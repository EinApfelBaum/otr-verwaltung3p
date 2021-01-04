# -*- coding: utf-8 -*-
# BEGIN LICENSE
# This file is in the public domain
# END LICENSE
import bisect
import logging
import os
import re
import sys
import time
from decimal import Decimal
from pathlib import Path

import cairo  # noqa F401 gcurse: DO NOT DELETE

from gi import require_version

require_version("Gdk", "3.0")
require_version("Gst", "1.0")
require_version("GstPbutils", "1.0")
require_version("Gtk", "3.0")
from gi.repository import GLib, Gdk, Gst, GstPbutils, Gtk

from otrverwaltung3p import cutlists
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.actions.cut import Cut
from otrverwaltung3p.constants import Format
from otrverwaltung3p.gui import LoadCutDialog
from otrverwaltung3p.gui.widgets.movieBox import MovieBox  # noqa F401 gcurse: DO NOT DELETE

Gst.init(None)


class CutinterfaceDialog(Gtk.Dialog, Gtk.Buildable, Cut):
    __gtype_name__ = "CutinterfaceDialog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(self.__class__.__name__)
        self.atfc = None  # alternative time <-> frame conversion
        self.builder = None
        self.bus = None  # gstreamer bus
        self.buttonClose = False
        self.buttonOk = False
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.current_position_frame = 0
        self.current_position_time = 0
        self.cut_selected = -1
        self.cut_selected_last = -1
        self.cutlist, self.cutslistmodel = None, None
        self.filename = None
        self.fileuri = None
        self.format_dict = Cut.format_dict
        self.fps = 0
        self.frames = 0
        self.framerate_denom, self.framerate_num = 0, 0
        self.frame_timecode, self.timecode_frame = {}, {}
        self.getVideoLength = True
        self.gtksink = None
        self.hide_cuts = False
        self.hide_mouse_over_video = False
        self.img_pause, self.img_play = None, None
        self.initial_cutlist = []
        self.initial_cutlist_in_frames = False
        self.inverted_timeline = None
        self.is_playing = False
        self.keyframes = None
        self.last_direction = "none"
        self.marker_a, self.marker_b = 0, -1
        self.movie_box = None
        self.nkfs = None  # new keyframe search
        self.player = None
        self.seek_distance = 0
        self.seek_distance_default = 0
        self.slider = None
        self.state = Gst.State.NULL
        self.test_cut = False
        self.test_next_marker = False
        self.timelines = [[]]
        self.timeoutcontrol = True
        self.timer, self.timer2 = None, None
        self.timer_hide_cursor = None
        self.vformat = None
        self.videoheight = 0
        self.videolength = 0
        self.videowidth = 0
        self.widgets_tt_names = [
            "btn_test_cut",
            "btn_test_next_marker",
            "button_a",
            "button_b",
            "button_back",
            "button_delete_cut",
            "button_deselect",
            "button_fast_back",
            "button_fast_forward",
            "button_forward",
            "button_jump_to_marker_a",
            "button_jump_to_marker_b",
            "button_keyfast_back",
            "button_keyfast_forward",
            "button_play",
            "button_remove",
            "button_seek1_back",
            "button_seek1_forward",
            "button_seek2_back",
            "button_seek2_forward",
            "load_button",
            "slider",
        ]
        self.widgets_tt_obj = []

    def do_parser_finished(self, builder):
        self.log.debug("funtion start")
        self.builder = builder
        self.builder.connect_signals(self)
        self.slider = self.builder.get_object("slider")
        self.slider.set_digits(0)
        self.slider.set_draw_value(False)

        self.movie_box = self.builder.get_object("movie_box").movie_widget
        self.player = self.builder.get_object("movie_box").player
        self.gtksink = self.builder.get_object("movie_box").gtksink
        # Create bus to get events from GStreamer player
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::error", self.on_error)
        self.bus.connect("message::eos", self.on_eos)
        self.bus.connect("message::state-changed", self.on_state_changed)
        self.bus.connect("message", self.on_message)

        self.hide_cuts = self.builder.get_object("checkbutton_hide_cuts").get_active()

        self.cutslistmodel = self.builder.get_object("cutslist")
        # Now in glade:
        # cutslistselection = self.builder.get_object("cutsview").get_selection()
        # cutslistselection.connect("changed", self.on_cuts_selection_changed)

        button_delete_cut = self.builder.get_object("button_delete_cut")
        button_delete_cut.set_sensitive(False)
        button_deselect = self.builder.get_object("button_deselect")
        button_deselect.set_sensitive(False)

        btn_test_cut = self.builder.get_object("btn_test_cut")
        btn_test_cut.connect("button-release-event", self.on_btn_test_cut_release_event)

        for name in self.widgets_tt_names:
            self.widgets_tt_obj.append(self.builder.get_object(name))

    def get_cuts_in_frames(self, cuts, in_frames):
        if not cuts:
            res = [(0, self.frames)]
        elif in_frames:
            res = cuts
        else:
            res = []
            for start, duration in cuts:
                start_frame = int(start * self.framerate_num / self.framerate_denom)
                duration_frames = int(duration * self.framerate_num / self.framerate_denom)
                self.log.debug(f"Startframe = {start_frame}")
                self.log.debug(f"Duration = {duration_frames}")
                res.append((start_frame, duration_frames))
        return res

    def load_cutlist(self, filename):
        self.log.debug("Function start")
        cutlist = cutlists.Cutlist()
        cutlist.intended_app = "VirtualDub.exe"
        if filename is not None and os.path.exists(filename):
            cutlist.local_filename = filename
            cutlist.read_from_file()
            cutlist.read_cuts()
            if (cutlist.cuts_frames and cutlist.filename_original != os.path.basename(self.filename)) or (
                not cutlist.cuts_frames and cutlist.cuts_seconds
            ):
                cutlist.fps = self.fps
                cutlist.cuts_frames = []
                self.log.info("Calculate frame values from seconds.")
                for start, duration in cutlist.cuts_seconds:
                    cutlist.cuts_frames.append((round(start * cutlist.fps), round(duration * cutlist.fps)))

            if cutlist.author != self.config.get("general", "cutlist_username"):
                cutlist.usercomment = (
                    self.config.get("general", "cutlist_comment")
                    + "; Vorlage von "
                    + cutlist.author
                    + "; "
                    + cutlist.usercomment
                )
            if cutlist.cuts_frames:
                self.initial_cutlist = cutlist.cuts_frames
                self.initial_cutlist_in_frames = True
            else:
                self.initial_cutlist = cutlist.cuts_seconds
                self.initial_cutlist_in_frames = False

        else:
            cutlist.usercomment = self.config.get("general", "cutlist_comment")
            self.initial_cutlist = []
            self.initial_cutlist_in_frames = True

        if self.timer is not None:  # Running
            self.timelines.append(self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames))

        if self.slider:
            self.slider.queue_draw()

        return cutlist

    def set_cuts(self, cutlist, cuts):
        cutlist.fps = self.fps
        cutlist.cuts_frames = cuts
        cutlist.cuts_seconds = []
        cutlist.app = f"OTR-Verwaltung3p_{sys.platform[:1]}"
        for start, duration in cuts:
            s = start * self.framerate_denom / float(self.framerate_num)
            d = duration * self.framerate_denom / float(self.framerate_num)
            cutlist.cuts_seconds.append((s, d))

    def run_(self, filename, cutlist, app):
        self.set_title("Cutinterface")
        self.app = app
        self.config = app.config
        self.filename = Path(filename)
        self.fileuri = self.filename.as_uri()

        self.vformat, _, _, _ = self.get_format(str(self.filename))

        self.config_update()

        if self.atfc:
            self.frame_timecode, self.timecode_frame, error = self.get_timecodes_from_file(str(self.filename))
            if self.frame_timecode is None:
                self.log.error("Error: Timecodes konnten nicht ausgelesen werden.")

        self.keyframes, error = self.get_keyframes_from_file(str(self.filename), self.vformat)
        if self.keyframes is None:
            self.log.error("Error: Keyframes konnten nicht ausgelesen werden.")

        self.movie_box.set_size_request(
            self.config.get("cutinterface", "resolution_x"), self.config.get("cutinterface", "resolution_y"),
        )
        # Make window a bit bigger than natural size to avoid size changes
        ci_window = self.builder.get_object("cutinterface_dialog")
        ci_window.set_size_request(
            int(ci_window.size_request().width * 1.1), int(ci_window.size_request().height * 1.0),
        )
        self.hide_cuts = self.config.get("cutinterface", "hide_cuts")

        # get video info
        self.log.debug("Discoverer start")
        # Discoverer timeout set to 5 * Gst.SECOND
        discoverer = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        disco = discoverer.discover_uri(self.fileuri)
        for vinfo in disco.get_video_streams():
            self.framerate_num = vinfo.get_framerate_num()
            self.framerate_denom = vinfo.get_framerate_denom()
            self.videowidth = vinfo.get_width()
            self.videoheight = vinfo.get_height()

        self.log.debug(f"framerate_num: {self.framerate_num}")
        self.log.debug(f"framerate_denom: {self.framerate_denom}")
        self.videolength = disco.get_duration()
        self.frames = round(self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND)
        self.fps = float(self.framerate_num) / float(self.framerate_denom)
        self.cutlist = self.load_cutlist(cutlist)  # needs self.fps
        self.timelines = [self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames)]
        # MENORYLEAK
        del disco
        del discoverer

        # Set player uri only after discoverer is done
        self.player.set_property("uri", self.fileuri)
        self.adjust_volume()

        self.ready_callback()

        # Reset cursor MainWindow
        self.app.gui.main_window.get_window().set_cursor(None)

        self.timer2 = GLib.timeout_add(600, self.update_listview)

        if Gtk.ResponseType.OK == self.run():
            self.set_cuts(self.cutlist, self.timelines[-1])
        else:
            self.set_cuts(self.cutlist, [])

        # Set return value of self.tick to false, so self.timer is stopped if it still exists
        self.timeoutcontrol = False
        # Un-hide the PreferencesWindow notebook tabs
        self.preferences_window_pages_visible(True)

        return self.cutlist

    def adjust_volume(self):
        try:
            if self.config.get("general", "vol_adjust_on"):
                vol_adjust = re.findall("[a-z.0-9,]+", self.config.get("general", "vol_adjust"))
                if vol_adjust:
                    # get station name from video filename
                    parts = str(self.filename).split("_")
                    parts.reverse()
                    station = parts[3]
                    for adj in vol_adjust:
                        if adj.split(",")[0].lower() in station:
                            self.player.set_property("volume", float(adj.split(",")[1]))
                            self.log.info(f"Cutinterface volume: {self.player.get_property('volume')}")
                            break
        except IndexError:
            pass

    def config_update(self):
        self.hide_mouse_over_video = self.config.get("cutinterface", "mouse_hide_over_video")
        if self.vformat == Format.HD2:
            self.atfc = False
        else:
            self.atfc = self.config.get("cutinterface", "alt_time_frame_conv")
        self.nkfs = self.config.get("cutinterface", "new_keyframe_search")
        self.seek_distance_default = self.config.get("cutinterface", "seek_distance_default") * Gst.SECOND
        self.seek_distance = self.seek_distance_default
        # Setup buttons
        seek1 = str(self.config.get("cutinterface", "seek1"))
        seek2 = str(self.config.get("cutinterface", "seek2"))
        self.builder.get_object("button_seek2_back").set_label(f"<< {seek2} s")
        self.builder.get_object("button_seek2_forward").set_label(f"{seek2} s >>")
        self.builder.get_object("button_seek1_back").set_label(f"<< {seek1} s")
        self.builder.get_object("button_seek1_forward").set_label(f"{seek1} s >>")
        self.builder.get_object("switch_tooltip").set_active(self.config.get("cutinterface", "show_tooltips"))
        self.builder.get_object("switch_keyframesearch").set_active(not self.nkfs)
        if not self.config.get("cutinterface", "show_tooltips"):
            self.on_switch_tooltip_state_set(None)
        if self.nkfs:
            self.on_switch_keyframesearch_state_set(None)
        self.adjust_volume()

    def ready_callback(self):
        self.log.debug("Function start")
        self.builder.get_object("label_filename").set_markup(f"{self.filename.name}")

        self.update_timeline()
        self.update_listview()

        self.timer = GLib.timeout_add(200, self.tick)

    def tick(self):
        self.update_frames_and_time()
        self.update_slider()
        self.builder.get_object("checkbutton_hide_cuts").set_active(self.hide_cuts)
        return self.timeoutcontrol

    def set_marker(self, a=None, b=None):
        """ Set markers a and/or b to a specific frame position and update the buttons """

        if a is not None:
            self.marker_a = a

            if a != -1 and self.marker_b < 0:
                self.marker_b = self.get_frames() - 1

        if b is not None:
            self.marker_b = b

            if b != -1 and self.marker_a < 0:
                self.marker_a = 0

        if self.marker_a != -1 and self.marker_b != -1 and self.marker_a > self.marker_b:
            self.log.debug("Switch a and b")
            c = self.marker_b
            self.marker_b = self.marker_a
            self.marker_a = c

        if self.marker_a == -1:
            self.builder.get_object("button_jump_to_marker_a").set_label("-")
        else:
            self.builder.get_object("button_jump_to_marker_a").set_label(str(int(self.marker_a)))

        if self.marker_b == -1:
            self.builder.get_object("button_jump_to_marker_b").set_label("-")
        else:
            self.builder.get_object("button_jump_to_marker_b").set_label(str(int(self.marker_b)))

        self.slider.queue_draw()

    def update_timeline(self):
        self.log.debug("Function start")
        self.player.set_state(Gst.State.PLAYING)
        self.player.set_state(Gst.State.PAUSED)

    def get_absolute_position(self, rel_pos):
        # get absolute frame, assuming that the given frame corresponds to the current display modus
        if not self.hide_cuts:
            return rel_pos
        elif rel_pos == -1:
            return -1

        durations = 0
        for start, duration in self.timelines[-1]:
            if rel_pos - durations < duration:
                return start + rel_pos - durations
            else:
                durations = durations + duration

        return self.frames - 1

    def get_relative_position(self, abs_pos):
        # convert the absolute position into the corresponding relative position
        if abs_pos == -1:
            return -1

        durations = 0
        for start, duration in self.timelines[-1]:
            if abs_pos - start < 0:
                return durations
            elif abs_pos - start < duration:
                return durations + abs_pos - start
            else:
                durations = durations + duration

        return durations - 1

    def invert_simple(self, cuts):
        # inverts the cuts (between timeline and cut-out list) assuming the list is flawless
        # and should be faster than the full version below
        inverted = []
        try:
            if cuts[0][0] > 0:
                inverted.append((0, cuts[0][0]))

            next_start = cuts[0][0] + cuts[0][1]
            for start, duration in cuts[1:]:
                inverted.append((next_start, start - next_start))
                next_start = start + duration

            if next_start < self.frames:
                inverted.append((next_start, self.frames - next_start))
        except IndexError:
            pass
        return inverted

    def invert_full(self, cuts):
        # inverts the cuts (between timeline and cut-out list) removing all kinds of overlaps etc.
        inverted = []
        sorted_cuts = sorted(cuts, key=lambda c: c[0])  # sort cuts after start frame
        try:
            if sorted_cuts[0][0] > 0:
                inverted.append((0, sorted_cuts[0][0]))

            next_start = sorted_cuts[0][0] + sorted_cuts[0][1]
            for start, duration in sorted_cuts[1:]:
                if duration < 0:  # correct invalid values
                    duration = -duration
                    start = start - duration + 1

                if start < 0:
                    start = 0

                if start + duration > self.frames:
                    duration = self.frames - start

                if start < next_start:  # handle overlapping cuts
                    next_start = max(next_start, start + duration)
                else:
                    if start - next_start > 0:  # don't add cuts with zero length
                        inverted.append((next_start, start - next_start))

                    next_start = start + duration

            if next_start < self.frames:
                inverted.append((next_start, self.frames - next_start))
        except IndexError:
            pass
        return inverted

    def remove_segment(self, rel_s, rel_d):
        self.log.debug("\033[1;31m-- Entering remove_segment\033[1;m")
        self.log.debug(f"Current timeline is: {self.timelines[-1]}")

        abs_start = self.get_absolute_position(rel_s)
        abs_end = self.get_absolute_position(rel_s + rel_d - 1)

        self.inverted_timeline = self.invert_simple(self.timelines[-1])
        self.inverted_timeline.append((abs_start, abs_end - abs_start + 1))
        self.timelines.append(self.invert_full(self.inverted_timeline))

        self.log.debug(f"Current timeline is: {self.timelines[-1]}")
        self.log.debug("\033[1;31m-- Leaving remove_segment\033[1;m")

        self.update_timeline()
        self.update_listview()

        time.sleep(0.2)
        if self.hide_cuts:
            self.log.debug(f"Seek To: {rel_s}")
            self.jump_to(frames=rel_s)
        else:
            self.log.debug(f"Seek To: {abs_end + 1}")
            self.jump_to(frames=abs_end + 1)

    def get_frames(self):
        """ Returns the current number of frames to be shown. """
        if self.hide_cuts:
            frames = sum([duration for start, duration in self.timelines[-1]])
        else:
            frames = self.frames

        return frames

    def query_position(self, gst_format):
        success, cur_pos = None, None
        for count in range(2):
            success, cur_pos = self.player.query_position(gst_format)
            if success:
                break
            else:
                time.sleep(0.05)
        return success, cur_pos

    def update_frames_and_time(self):
        if self.state == Gst.State.NULL:
            return
        else:
            self.builder.get_object("btn_test_cut").set_sensitive(self.cut_selected != -1)
            try:
                success, self.current_position_time = self.query_position(Gst.Format.TIME)
                duration = self.player.query_duration(Gst.Format.TIME)[1]
                if not success:
                    return
            except Exception as e:  # manchmal geht es nicht, bspw. wenn gerade erst geseekt wurde
                self.log.warning(f"Exception: {e}")
                return

            self.current_position_frame = self.time_to_frame(self.current_position_time)

            label_time_colors = self.config.get("cutinterface", "label_time_colors")
            frame_color = label_time_colors[1]
            if (
                self.keyframes is not None
                and self.current_position_frame in self.keyframes
                and self.vformat != Format.HD2
            ):
                if self.config.get("cutinterface", "label_time_colors")[0]:
                    frame_color = label_time_colors[1]
                string = '<span font_family="monospace">(K) </span>'
            else:
                if self.config.get("cutinterface", "label_time_colors")[0]:
                    frame_color = label_time_colors[2]
                string = '<span font_family="monospace">    </span>'

            disp_frame = f"{self.current_position_frame} / {self.get_frames() - 1}"
            disp_hms = f"{self.nanoseconds_to_hms(self.current_position_time)} / {self.nanoseconds_to_hms(duration)}"
            disp_sec = (
                f"{round(Decimal(self.current_position_time / Gst.SECOND), 3):.3f} / "
                f"{round(Decimal(duration / Gst.SECOND), 3):.3f}"
            )
            # if self.config.get("cutinterface", "label_time_colors")[0] and self.vformat != Format.HD2:
            #     self.builder.get_object("lbl_time").set_markup(
            #         f"<span color='{frame_color}'>Frame: {string}{disp_frame}, </span>"
            #         f"<span color='{label_time_colors[3]}'>Zeit: {disp_hms}, </span>"
            #         f"<span color='{label_time_colors[4]}'> Sek: {disp_sec}  </span>"
            #         f"<span color='{label_time_colors[5]}'>{Format.to_string(self.vformat)}</span>"
            #     )
            # else:
            #     self.builder.get_object("label_time").set_markup(
            #         f"Frame: {string}{disp_frame}, "
            #         f"Zeit: {disp_hms}, "
            #         f"Sek: {disp_sec}  {Format.to_string(self.vformat)}"
            #     )
            if self.config.get("cutinterface", "label_time_colors")[0] and self.vformat != Format.HD2:
                self.builder.get_object("lbl_frame").set_markup(
                    f"<span color='{frame_color}'>Frame: {string}{disp_frame}</span>"
                )
                self.builder.get_object("lbl_time").set_markup(
                    f"<span color='{label_time_colors[3]}'>Zeit: {disp_hms}</span>"
                )
                self.builder.get_object("lbl_seconds").set_markup(
                    f"<span color='{label_time_colors[4]}'> Sek: {disp_sec}</span>"
                )
                self.builder.get_object("lbl_format").set_markup(
                    f"<span color='{label_time_colors[5]}'>{Format.to_string(self.vformat)}</span>"
                )
            else:
                self.builder.get_object("lbl_frame").set_markup(f"Frame: {string}{disp_frame}")
                self.builder.get_object("lbl_time").set_markup(f"Zeit: {disp_hms}")
                self.builder.get_object("lbl_seconds").set_markup(f"Sek: {disp_sec}")
                self.builder.get_object("lbl_format").set_markup(f"{Format.to_string(self.vformat)}")

    def update_slider(self):
        try:
            nanosecs = self.player.query_position(Gst.Format.TIME)[1]
            # block seek handler so we don't seek when we set_value()
            self.builder.get_object("slider").handler_block_by_func(self.on_slider_value_changed)

            frame = self.time_to_frame(nanosecs)

            self.builder.get_object("slider").set_value(frame)
            self.builder.get_object("slider").handler_unblock_by_func(self.on_slider_value_changed)
        # catch Gst.QueryError
        except TypeError:
            pass

    def seeker(self, direction):
        """ Jump forward or backward by self.seek_distance.
            Value is divided by 2 on each direction change.
        """
        if not direction == "reset" and not self.last_direction == "none":
            # if direction has changed, bisect the seek_distance
            if not direction == self.last_direction:
                self.seek_distance = int(self.seek_distance / 2)
                self.log.debug(
                    f"BISECT: direction: {direction}, last_direction: {self.last_direction}, "
                    f"seek_distance: {self.seek_distance / Gst.SECOND}s"
                )
        if direction == "left":
            self.jump_relative_time(self.seek_distance * -1)
            self.last_direction = direction
        elif direction == "right":
            self.jump_relative_time(self.seek_distance)
            self.last_direction = direction
        elif direction == "reset":
            self.seek_distance = self.seek_distance_default
            self.last_direction = "none"
            self.log.debug(
                f"RESET: direction: {direction}, last_direction: {self.last_direction}, "
                f"seek_distance: {self.seek_distance / Gst.SECOND}s"
            )

    def update_listview(self):
        self.log.debug("Function start")
        listview = self.builder.get_object("cutsview")
        listselection = listview.get_selection()
        if listselection.get_selected():
            listmodel, listiter = listselection.get_selected()
            listview.set_model(None)  # for speeding up the update of the view
            listmodel.clear()

            if not self.getVideoLength:
                self.inverted_timeline = self.invert_simple(self.timelines[-1])
                for start, duration in self.inverted_timeline:
                    listmodel.append((start, start + duration - 1))

            cut_duration_secs = sum([duration for start, duration in self.timelines[-1]]) / self.fps
            cut_duration = self.seconds_to_hms(cut_duration_secs).split(".")[0]
            self.builder.get_object("lbl_cut_duration").set_text(f"{str(cut_duration)}")

            listview.set_model(listmodel)
            if listiter:
                listselection.select_path(listmodel.get_path(listiter))

            if self.timer2 is not None:
                return False

    def select_cut(self, direction):
        listview = self.builder.get_object("cutsview")
        listselection = listview.get_selection()
        listmodel, listiter = listselection.get_selected()
        rows = listmodel.iter_n_children(None)
        if listiter:  # A cut is selected
            if direction == "next":
                listiter = listmodel.iter_next(listiter)
                if listiter is None:
                    listiter = listmodel.get_iter_first()
            elif direction == "prev":
                listiter = listmodel.iter_previous(listiter)
                if listiter is None:
                    # ~ rows = listmodel.iter_n_children(None)
                    listiter = listmodel.iter_nth_child(None, rows - 1)

            tree_path = listmodel.get_path(listiter)
            listselection.select_path(tree_path)
        else:  # No cut selected
            if direction == "next":
                if self.cut_selected_last + 1:  # same as "if not self.cut_selected_last == -1"
                    listiter = listmodel.iter_nth_child(None, self.cut_selected_last + 1)
                    if listiter is None:
                        listiter = listmodel.get_iter_first()
                else:
                    listiter = listmodel.get_iter_first()
            elif direction == "prev":
                if self.cut_selected_last + 1:  # same as "if not self.cut_selected_last == -1"
                    listiter = listmodel.iter_nth_child(None, self.cut_selected_last)
                    # Is the following necessary? Can listiter be None here?
                    if listiter is None:
                        listiter = listmodel.iter_nth_child(None, rows - 1)
                else:
                    listiter = listmodel.iter_nth_child(None, rows - 1)

            tree_path = listmodel.get_path(listiter)
            listselection.select_path(tree_path)

    def is_remove_modus(self):
        return self.cut_selected < 0 or self.hide_cuts

    def update_remove_button(self):
        if self.is_remove_modus():
            self.builder.get_object("button_remove").set_label("Entfernen")
        else:
            self.builder.get_object("button_remove").set_label("Übernehmen")

    def cmenu_lbl_filename(self):
        menu = Gtk.Menu()
        items = [("Dateiname kopieren", "name"), ("Dateiname mit Pfad kopieren", "path")]
        for label, action in items:
            item = Gtk.MenuItem(label)
            item.connect("activate", self.cmenu_lbl_filename_callback, action)
            menu.add(item)
        menu.show_all()
        menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def cmenu_lbl_filename_callback(self, _, action):
        if action == "name":
            self.clipboard.set_text(self.filename.name, -1)
        elif action == "path":
            self.clipboard.set_text(str(self.filename), -1)

    def time_to_frame(self, nanoseconds: int) -> int:
        """Return the frame number for time"""
        if self.atfc:
            if nanoseconds in self.timecode_frame:
                return self.timecode_frame[nanoseconds]
            else:
                nearest_position = self.find_closest(self.timecode_frame, nanoseconds)
                # ~ self.log.debug("nearest_position: {}".format(nearest_position))
                return self.timecode_frame[nearest_position]
        else:
            return round(nanoseconds / Gst.SECOND * self.fps)

    def frame_to_time(self, frame_number: int):
        """Returns the time (nanoseconds) for frame_number."""
        if frame_number < 0:
            return 0
        elif frame_number > self.frames:
            return self.videolength

        if self.atfc:
            if frame_number in self.frame_timecode:
                return self.frame_timecode[frame_number]
            else:
                return self.current_position_time
        else:
            return frame_number / self.fps * Gst.SECOND

    @staticmethod
    def find_closest(find_in: dict, position: int) -> int:
        """ Assumes find_in (key_list) is sorted. Returns closest value to position.
        If two numbers are equally close, return the smaller one.
        """
        key_list = list(find_in.keys())
        pos = bisect.bisect_left(key_list, position)
        if pos == 0:
            return key_list[0]
        if pos == len(key_list):
            return key_list[-1]
        before = key_list[pos - 1]
        after = key_list[pos]
        if after - position < position - before:
            return after
        else:
            return before

    @staticmethod
    def nanoseconds_to_hms(nanoseconds: int) -> str:
        # Used for display
        second, remainder = divmod(nanoseconds, Gst.SECOND)
        hour, second = divmod(second, 3600)
        minute, second = divmod(second, 60)

        decimals = str(int(remainder))[:3].ljust(3, "0")
        return f"{hour:02}:{minute:02}:{second:02}.{decimals}"

    # #### gstreamer bus signals ####
    def on_error(self, bus, msg):
        err, debug = msg.parse_error()
        self.log.error(f"Error: {err}, {debug}")
        self.player.set_state(Gst.State.NULL)
        self.builder.get_object("lbl_time").set_text("Frame: 0/0, Zeit 0s/0s")

    def on_eos(self, bus, msg):
        self.player.set_state(Gst.State.PAUSED)
        self.on_button_back_clicked(None)
        self.on_button_forward_clicked(None)
        if self.test_next_marker or self.test_cut:
            self.test_next_marker = False
            self.test_cut = False

    def on_state_changed(self, bus, msg):
        old, new, pending = msg.parse_state_changed()
        if not msg.src == self.player:
            # not from the player, ignore
            return
        self.state = new

    def on_message(self, bus, message):
        message_type = message.type
        if message_type == Gst.MessageType.ASYNC_DONE:
            if self.getVideoLength:
                self.getVideoLength = not self.getVideoLength
                self.log.debug("Async done")
                self.log.debug(f"getVideoLength = {self.getVideoLength}")
                self.videolength = self.player.query_duration(Gst.Format.TIME)[1]
                self.frames = round(self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND)  # ROUND
                self.slider.set_range(0, self.get_frames())
                self.timelines = [self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames)]
                self.builder.get_object("slider").set_range(0, self.get_frames())
                self.slider.queue_draw()
                self.log.debug(f"Timelines: {self.timelines}")
                self.log.debug(f"framerate_num: {self.framerate_num}")
                self.log.debug(f"framerate_denom: {self.framerate_denom}")
                self.log.debug(f"videolength: {self.videolength}")
                self.log.debug(f"Number of frames: {self.frames}")
        elif message_type == Gst.MessageType.SEGMENT_DONE:
            if self.test_cut:
                self.test_cut_part2()

    # #### signals ####
    def on_movie_event_box_enter_leave_notify_event(self, widget, event, *args):
        if self.hide_mouse_over_video:
            if event.type == Gdk.EventType.MOTION_NOTIFY:
                GLib.source_remove(self.timer_hide_cursor)
                widget.get_window().set_cursor(None)
                self.timer_hide_cursor = GLib.timeout_add(
                    2000, widget.get_window().set_cursor, self.app.gui.cursor_blank
                )
            if event.type == Gdk.EventType.ENTER_NOTIFY and self.hide_mouse_over_video:
                self.timer_hide_cursor = GLib.timeout_add(
                    2000, widget.get_window().set_cursor, self.app.gui.cursor_blank
                )
            elif event.type == Gdk.EventType.LEAVE_NOTIFY:
                GLib.source_remove(self.timer_hide_cursor)
                widget.get_window().set_cursor(None)

    def on_movie_box_unrealize(self, widget):
        self.player.set_state(Gst.State.NULL)
        # MEMORYLEAK:
        self.bus.remove_signal_watch()
        del self.bus
        del self.frame_timecode
        del self.timecode_frame
        del self.keyframes

    def on_window_key_press_event(self, widget, event, *args):
        """handle keyboard events"""
        keyname = Gdk.keyval_name(event.keyval).upper()
        mod_ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        mod_shift = event.state & Gdk.ModifierType.SHIFT_MASK
        mod_alt = event.state & Gdk.ModifierType.MOD1_MASK

        if event.type == Gdk.EventType.KEY_PRESS:
            # CTRL
            if not mod_shift and not mod_alt and mod_ctrl:
                if keyname == "LEFT":
                    self.on_button_seek2_back_clicked(None)
                    return True
                if keyname == "RIGHT":
                    self.on_button_seek2_forward_clicked(None)
                    return True
                if keyname == "DELETE":
                    self.on_button_delete_cut_clicked(None)
                    return True
                if keyname == "HOME":
                    self.jump_to(nanoseconds=0)
                    return True
                if keyname == "END":
                    self.jump_to(nanoseconds=self.videolength)
                    return True
            # SHIFT
            if not mod_ctrl and not mod_alt and mod_shift:
                if keyname == "LEFT":
                    # -10 frames
                    self.on_button_fast_back_clicked(None)
                    return True
                elif keyname == "RIGHT":
                    # +10 frames
                    self.on_button_fast_forward_clicked(None)
                    return True
                elif keyname == "UP":
                    # +100 frames
                    self.on_button_seek1_forward_clicked(None)
                    return True
                elif keyname == "DOWN":
                    # -100 frames
                    self.on_button_seek1_back_clicked(None)
                    return True
                elif keyname == "T":
                    self.test_cut_part1(False)
                elif keyname == "A":
                    self.on_btn_test_next_marker_clicked(None)
            # ALT
            if not mod_ctrl and not mod_shift and mod_alt:
                if keyname == "LEFT":
                    self.seeker("left")
                    return True
                if keyname == "RIGHT":
                    self.seeker("right")
                    return True
                if keyname == "DOWN":
                    self.seeker("reset")
                    return True
            # Not SHIFT, not CTRL, not ALT
            if not mod_ctrl and not mod_shift and not mod_alt:
                if keyname == "LEFT":
                    self.on_button_back_clicked(None)
                    return True
                elif keyname == "RIGHT":
                    self.on_button_forward_clicked(None)
                    return True
                elif keyname == "UP":
                    self.on_button_keyfast_forward_clicked(None)
                    return True
                elif keyname == "DOWN":
                    self.on_button_keyfast_back_clicked(None)
                    return True
                elif keyname == "HOME" or keyname == "BRACKETLEFT":
                    self.on_button_a_clicked(None)
                    return True
                elif keyname == "END" or keyname == "BRACKETRIGHT":
                    self.on_button_b_clicked(None)
                    return True
                elif keyname == "PAGE_UP":
                    self.on_button_jump_to_marker_a_clicked(None)
                    return True
                elif keyname == "PAGE_DOWN":
                    self.on_button_jump_to_marker_b_clicked(None)
                    return True
                elif keyname == "DELETE":
                    self.on_button_remove_clicked(None)
                    return True
                elif keyname == "L":
                    self.on_load_button_clicked(None)
                    return True
                elif keyname == "SPACE":
                    self.on_button_play_pause_clicked(self.builder.get_object("button_play"))
                    return True
                elif keyname == "N":
                    self.select_cut("next")
                    return True
                elif keyname == "B":
                    self.select_cut("prev")
                    return True
                elif keyname == "ESCAPE":
                    self.on_button_deselect_clicked(None)
                    return True
                elif keyname == "T":
                    self.test_cut_part1(False)
                else:
                    self.log.debug(f"keyname: {keyname}")
        return False

    def on_window_key_release_event(self, widget, event, *args):
        """handle keyboard events"""
        return False
        # keyname = Gdk.keyval_name(event.keyval).upper()
        # mod_ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        # mod_shift = event.state & Gdk.ModifierType.SHIFT_MASK
        # if not mod_ctrl and not mod_shift:
        #     if event.type == Gdk.EventType.KEY_RELEASE:
        #         time.sleep(0.05)
        #         if keyname == "LEFT":
        #             self.on_button_back_clicked(None)
        #             return True
        #         elif keyname == "RIGHT":
        #             self.on_button_forward_clicked(None)
        #             return True
        # return False

    @staticmethod
    def on_slider_key_press_event(widget, event):
        # override normal keybindings for slider (HOME and END are used for markers)
        keyname = Gdk.keyval_name(event.keyval).upper()
        if keyname == "HOME" or keyname == "END":
            return True

    def on_slider_scroll_event(self, widget, event):
        # Handles navigating with mousewheel
        if self.app.config.get("cutinterface", "scrolling_inverted"):
            direction = "up" if event.get_scroll_deltas()[2] > 0 else "down"
        else:
            direction = "down" if event.get_scroll_deltas()[2] > 0 else "up"
        # accel_mask = Gtk.accelerator_get_default_mod_mask()
        mod_ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        mod_shift = event.state & Gdk.ModifierType.SHIFT_MASK
        mod_alt = event.state & Gdk.ModifierType.MOD1_MASK
        # SHIFT
        if mod_shift and not mod_ctrl and not mod_alt:
            if direction == "down":
                self.on_button_seek1_back_clicked(None)
                return True
            else:
                self.on_button_seek1_forward_clicked(None)
                return True
        # CTRL
        elif mod_ctrl and not mod_shift and not mod_alt:
            if direction == "down":
                self.on_button_seek2_back_clicked(None)
                return True
            else:
                self.on_button_seek2_forward_clicked(None)
                return True
        # ALT
        elif not mod_ctrl and not mod_shift and mod_alt:
            if direction == "down":
                self.seeker("left")
                return True
            else:
                self.seeker("right")
                return True
        # CTRL-SHIFT
        elif mod_ctrl and mod_shift and not mod_alt:
            if direction == "down":
                self.on_button_keyfast_back_clicked(None)
                return True
            else:
                self.on_button_keyfast_forward_clicked(None)
                return True
        # Not SHIFT, not CTRL, not ALT
        else:
            if direction == "down":
                self.on_button_back_clicked(None)
                return True
            else:
                self.on_button_forward_clicked(None)
                return True

    def on_slider_value_changed(self, slider):
        frames = slider.get_value()
        self.log.debug(f"Slider value = {frames}")
        if frames >= self.get_frames():
            self.log.debug("slider.get_value() >= self.get_frames(). Restricting.")
            frames = self.get_frames() - 1
        self.player.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            frames * Gst.SECOND * self.framerate_denom / self.framerate_num,
        )
        if not self.is_playing:
            self.log.debug("update_frames_and_time() by slider change")
            self.update_frames_and_time()

    def on_slider_draw_event(self, slider, cairo_context):
        border = 11
        if self.get_frames() != 0:
            # draw line from marker a to marker b and for all cuts
            try:
                one_frame_in_pixels = (slider.get_allocation().width - 2 * border) / float(self.get_frames())
                # draw only if ...
                if self.marker_a != self.marker_b and self.marker_a >= 0 and self.marker_b >= 0:
                    # self.log.debug(f"Slider allocation size: {slider.get_allocation().width} x "
                    #                f"{slider.get_allocation().height}")
                    # self.log.debug(f"one_frame_in_pixels: {one_frame_in_pixels}")
                    marker_a = border + int(round(self.marker_a * one_frame_in_pixels))
                    marker_b = border + int(round(self.marker_b * one_frame_in_pixels))

                    cairo_context.set_source_rgb(1.0, 0.0, 0.0)  # red
                    cairo_context.rectangle(marker_a, 0, marker_b - marker_a, 5)
                    cairo_context.fill()

                if not self.hide_cuts:
                    inverted = self.invert_simple(self.timelines[-1])
                    for start, duration in inverted:
                        pixel_start = border + int(start * one_frame_in_pixels)
                        pixel_duration = int(duration * one_frame_in_pixels)

                        # draw keyframe cuts that don't need reencoding in a different color

                        if start in self.keyframes and (
                            (start + duration in self.keyframes or start + duration == self.frames)
                            and self.vformat != Format.HD2
                        ):
                            cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                            cairo_context.rectangle(
                                pixel_start, slider.get_allocation().height - 5, pixel_duration, 5,
                            )
                            cairo_context.fill()
                        else:
                            if start in self.keyframes and self.vformat != Format.HD2:
                                cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                            else:
                                cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                            cairo_context.rectangle(
                                pixel_start, slider.get_allocation().height - 5, pixel_duration / 10, 5,
                            )
                            cairo_context.fill()

                            if (
                                start + duration in self.keyframes
                                or start + duration == self.frames
                                and self.vformat != Format.HD2
                            ):
                                cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                            else:
                                cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange

                            cairo_context.rectangle(
                                pixel_start + pixel_duration / 10 * 9,
                                slider.get_allocation().height - 5,
                                pixel_duration / 10,
                                5,
                            )
                            cairo_context.fill()

                            cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                            cairo_context.rectangle(
                                pixel_start + pixel_duration / 10,
                                slider.get_allocation().height - 5,
                                pixel_duration / 10 * 8,
                                5,
                            )
                            cairo_context.fill()

                # if not self.hide_cuts:
                #     inverted = self.invert_simple(self.timelines[-1])
                #     for start, duration in inverted:
                #         pixel_start = border + int(round(start * one_frame_in_pixels))
                #         pixel_duration = int(round(duration * one_frame_in_pixels))
                #
                #         # draw keyframe cuts that don't need reencoding in a different color
                #
                #         if round(start) in self.keyframes and (
                #                 (round(start + duration) in self.keyframes
                #                  or round(start + duration) == self.frames)
                #                 and self.vformat != Format.HD2
                #         ):
                #             cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                #             cairo_context.rectangle(
                #                 pixel_start, slider.get_allocation().height - 5, pixel_duration, 5,
                #             )
                #             cairo_context.fill()
                #         else:
                #             if round(start) in self.keyframes and self.vformat != Format.HD2:
                #                 cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                #             else:
                #                 cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                #             cairo_context.rectangle(
                #                 pixel_start, slider.get_allocation().height - 5, pixel_duration / 10, 5,
                #             )
                #             cairo_context.fill()
                #
                #             if round(start + duration) in self.keyframes \
                #                     or round(start + duration) == self.frames and self.vformat != Format.HD2:
                #                 cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                #             else:
                #                 cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                #
                #             cairo_context.rectangle(
                #                 pixel_start + pixel_duration / 10 * 9,
                #                 slider.get_allocation().height - 5,
                #                 pixel_duration / 10,
                #                 5,
                #             )
                #             cairo_context.fill()
                #
                #             cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                #             cairo_context.rectangle(
                #                 pixel_start + pixel_duration / 10,
                #                 slider.get_allocation().height - 5,
                #                 pixel_duration / 10 * 8,
                #                 5,
                #             )
                #             cairo_context.fill()

            except AttributeError as ex:
                self.log.warning(f"Exeption: {ex}")
                pass

    def on_cuts_selection_changed(self, treeselection):
        self.log.debug("Function start")
        cutslist, cutsiter = treeselection.get_selected()
        button_delete_cut = self.builder.get_object("button_delete_cut")
        button_deselect = self.builder.get_object("button_deselect")

        if cutsiter:
            self.cut_selected = cutslist.get_path(cutsiter)[0]
            self.cut_selected_last = self.cut_selected
            self.log.debug(f"Selected cut = {self.cut_selected}")
            a = cutslist.get_value(cutsiter, 0)
            b = cutslist.get_value(cutsiter, 1)
            if self.hide_cuts:
                a = self.get_relative_position(a)
                b = self.get_relative_position(b)

            self.update_remove_button()
            button_delete_cut.set_sensitive(True)
            button_deselect.set_sensitive(True)
            self.set_marker(a, b)
            self.slider.queue_draw()
        else:
            self.cut_selected = -1
            self.update_remove_button()
            button_delete_cut.set_sensitive(False)
            button_deselect.set_sensitive(False)

    # ##### interaction events #####
    def on_label_filename_button_press_event(self, widget, event):
        # print(event.type)
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button is Gdk.BUTTON_SECONDARY:  # right-click
            self.cmenu_lbl_filename()

    def on_btn_config_clicked(self, widget, data=None):
        self.app.gui.preferences_window.builder.get_object("notebook").set_current_page(6)
        self.preferences_window_pages_visible(False)
        self.app.gui.preferences_window.show()

    def on_button_undo_clicked(self, *args):
        if len(self.timelines) > 1:
            del self.timelines[-1]
            self.update_timeline()
            self.update_listview()
            self.slider.queue_draw()

    # ##### button row 1 #####
    def on_button_play_pause_clicked(self, button, data=None):
        if self.is_playing:
            self.is_playing = False
            self.player.set_state(Gst.State.PAUSED)
            button.set_label("  Play  ")
            self.update_frames_and_time()
        else:
            self.is_playing = True
            self.player.set_state(Gst.State.PLAYING)
            button.set_label("Pause")

    def on_btn_test_next_marker_clicked(self, button, data=None):
        test_cut_offset_secs = self.config.get("cutinterface", "test_cut_offset_secs")
        self.test_next_marker = True
        self.player.set_state(Gst.State.PAUSED)
        next_marker = self.frame_to_time(self.marker_a - 1)

        if next_marker > 0 and self.frame_to_time(self.marker_a - 1) - test_cut_offset_secs * Gst.SECOND >= 0:
            # new_seek(rate, format, flags, start_type, start, stop_type, stop)
            segment = Gst.Event.new_seek(
                1.0,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,  # | Gst.SeekFlags.SEGMENT,
                Gst.SeekType.SET,
                self.frame_to_time(self.marker_a - 1) - test_cut_offset_secs * Gst.SECOND,
                Gst.SeekType.SET,
                next_marker,
            )
            _ = self.gtksink.send_event(segment)
            self.player.set_state(Gst.State.PLAYING)

    def on_btn_test_cut_release_event(self, button, event, data=None):
        # test_all = event.state & Gdk.ModifierType.SHIFT_MASK
        test_all = False
        self.test_cut_part1(test_all)

    def on_button_a_clicked(self, *args):
        # TODO: warn if Marker A = B or distance between them to low
        self.log.debug(f"marker a = {self.current_position_frame}")
        self.set_marker(a=self.current_position_frame)
        self.slider.queue_draw()

    def on_button_b_clicked(self, *args):
        # TODO: warn if Marker A = B or distance between them to low
        self.log.debug(f"marker b = {self.current_position_frame}")
        self.set_marker(b=self.current_position_frame)
        self.slider.queue_draw()

    def on_button_remove_clicked(self, widget):
        self.log.debug("Function start")
        self.log.debug(f"marker a = {self.marker_a}")
        self.log.debug(f"marker b = {self.marker_b}")
        if self.is_remove_modus():
            if self.marker_a >= 0 and self.marker_b >= 0:
                self.remove_segment(self.marker_a, self.marker_b - self.marker_a + 1)
                if self.cut_selected >= 0:
                    self.builder.get_object("cutsview").get_selection().unselect_all()

                self.set_marker(a=-1, b=-1)
                self.slider.queue_draw()

        else:
            if self.marker_a >= 0 and self.marker_b >= 0:
                inverted = self.invert_simple(self.timelines[-1])
                inverted[self.cut_selected] = (
                    self.marker_a,
                    self.marker_b - self.marker_a + 1,
                )
                self.timelines.append(self.invert_full(inverted))
                self.builder.get_object("cutsview").get_selection().unselect_all()
                self.slider.queue_draw()
                self.update_listview()

        self.slider.clear_marks()
        self.marker_a = -1
        self.marker_b = -1
        self.seek_distance = self.seek_distance_default

    def on_checkbutton_hide_cuts_toggled(self, widget):
        self.log.debug("Function start")
        self.is_playing = False
        self.player.set_state(Gst.State.PAUSED)
        self.update_frames_and_time()
        marker_a = self.get_absolute_position(self.marker_a)
        marker_b = self.get_absolute_position(self.marker_b)
        pos = self.get_absolute_position(self.current_position_frame)

        self.hide_cuts = widget.get_active()
        self.config.set("cutinterface", "hide_cuts", self.hide_cuts)
        self.update_timeline()
        if self.hide_cuts:
            self.set_marker(
                self.get_relative_position(marker_a), self.get_relative_position(marker_b),
            )
        else:
            self.builder.get_object("cutsview").get_selection().unselect_all()
            self.set_marker(marker_a, marker_b)

        self.update_remove_button()
        self.slider.queue_draw()

        # print "Relative position: ", self.get_relative_position(pos)
        time.sleep(0.2)
        if self.hide_cuts:
            self.jump_to(frames=self.get_relative_position(pos))
        else:
            self.jump_to(frames=pos)

    # ##### button row 2 navigation #####
    def on_button_keyfast_back_clicked(self, widget, data=None):
        if self.is_playing:
            was_playing = True
            self.player.set_state(Gst.State.PAUSED)
        else:
            was_playing = False

        self.jump_key("backward", was_playing)

    def on_button_seek2_back_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get("cutinterface", "seek2")) * Gst.SECOND * -1)

    def on_button_seek1_back_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get("cutinterface", "seek1")) * Gst.SECOND * -1)
        # ~ self.jump_relative(-100)

    def on_button_fast_back_clicked(self, widget, data=None):
        self.jump_relative(-10)

    def on_button_back_clicked(self, widget, data=None):
        if self.current_position_frame != 0:
            self.jump_relative(-1)

    def on_button_forward_clicked(self, widget, data=None):
        # self.jump_relative(1)
        self.frame_step(1.0, 1)

    def on_button_fast_forward_clicked(self, widget, data=None):
        self.jump_relative(10)

    def on_button_seek1_forward_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get("cutinterface", "seek1")) * Gst.SECOND)
        # ~ self.jump_relative(100)

    def on_button_seek2_forward_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get("cutinterface", "seek2")) * Gst.SECOND)

    def on_button_keyfast_forward_clicked(self, widget, data=None):
        if self.is_playing:
            was_playing = True
            self.player.set_state(Gst.State.PAUSED)
        else:
            was_playing = False
        self.jump_key("forward", was_playing)

    # ##### buttons below cutsview (right side) #####
    def on_button_delete_cut_clicked(self, widget):
        self.log.debug("Function start")
        # global marker_a, marker_b, pos, playing  gcurse: delete this if no bugs appear
        if self.hide_cuts:
            playing = self.is_playing
            self.is_playing = False
            self.player.set_state(Gst.State.PAUSED)
            self.update_frames_and_time()
            marker_a = self.get_absolute_position(self.marker_a)
            marker_b = self.get_absolute_position(self.marker_b)
            pos = self.get_absolute_position(self.current_position_frame)

        inverted = self.invert_simple(self.timelines[-1])
        del inverted[self.cut_selected]
        self.timelines.append(self.invert_full(inverted))

        self.on_button_deselect_clicked(None)

        if self.hide_cuts:
            self.update_timeline()
            marker_a = self.get_relative_position(marker_a)
            marker_b = self.get_relative_position(marker_b)
            pos = self.get_relative_position(pos)
            self.set_marker(marker_a, marker_b)
            time.sleep(0.2)
            self.jump_to(frames=pos)
            if playing:
                self.is_playing = True
                self.player.set_state(Gst.State.PLAYING)

        self.slider.queue_draw()
        self.update_listview()

    def on_button_deselect_clicked(self, widget):
        self.log.debug("Function start")
        self.builder.get_object("cutsview").get_selection().unselect_all()
        self.slider.clear_marks()
        self.marker_a = -1
        self.marker_b = -1

    def on_load_button_clicked(self, widget):
        self.log.debug("Function start")
        load_dialog = LoadCutDialog.new(self.app)
        load_dialog.set_transient_for(self)
        load_dialog.set_modal(True)
        load_dialog.setup(str(self.filename))
        response = load_dialog.run()
        load_dialog.destroy()
        if response == 1:
            self.cutlist = self.load_cutlist(load_dialog.result.local_filename)
            self.builder.get_object("cutsview").get_selection().unselect_all()
            if self.hide_cuts:
                self.update_timeline()

            self.slider.queue_draw()
            self.update_listview()

    # ##### button row 3 #####
    def on_button_jump_to_marker_a_clicked(self, widget):
        if self.marker_a >= 0:
            self.jump_to(frames=self.marker_a)

    def on_button_jump_to_marker_b_clicked(self, widget):
        if self.marker_b >= 0:
            self.jump_to(frames=self.marker_b)

    # ##### vbutton row bottom #####
    def on_switch_tooltip_state_set(self, *args):
        active = self.builder.get_object("switch_tooltip").get_active()
        for widget_tt in self.widgets_tt_obj:
            widget_tt.props.has_tooltip = True if active else False

    def on_switch_keyframesearch_state_set(self, *args):
        active = self.builder.get_object("switch_keyframesearch").get_active()
        if active:
            self.nkfs = False
        else:
            self.nkfs = True

    # ##### seeking #####
    def jump_relative_time(self, jump_nanoseconds, flags=Gst.SeekFlags.ACCURATE):
        try:
            success, nano_seconds = self.query_position(Gst.Format.TIME)
            if not success:
                # self.log.debug('query_position() was not successful')
                return
        except Exception as e:
            self.log.debug(f"Exception: {e}")
            return
        # self.videolength = self.player.query_duration(Gst.Format.TIME)[1]
        nano_seconds += jump_nanoseconds

        if nano_seconds < 0:
            self.log.debug("restrict start")
            nano_seconds = 0
        elif nano_seconds > self.videolength:
            self.log.debug("restrict end")
            nano_seconds = self.videolength
        self.jump_to(nanoseconds=nano_seconds, flags=flags)

    def jump_relative(self, frames, flags=Gst.SeekFlags.ACCURATE):
        try:
            success, nano_seconds = self.query_position(Gst.Format.TIME)
            if not success:
                # self.log.debug('query_position() was not successful')
                return
        except Exception as e:
            self.log.debug(f"Exception: {e}")
            return

        self.videolength = self.player.query_duration(Gst.Format.TIME)[1]
        # self.frames = round(self.videolength * self.fps / Gst.SECOND)

        if self.atfc:
            nano_seconds = self.frame_to_time(self.time_to_frame(nano_seconds) + frames)
        else:
            nano_seconds += frames * (Gst.SECOND * self.framerate_denom / self.framerate_num)

        self.jump_to(nanoseconds=nano_seconds, flags=flags)

    def jump_key(self, direction, playing=None):
        self.update_frames_and_time()
        # success, current_position = self.query_position(Gst.Format.TIME)
        if self.nkfs:  # gcurse new_keyframe_search
            if direction == "backward":
                self.player.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT | Gst.SeekFlags.SNAP_BEFORE,
                    self.frame_to_time(self.current_position_frame - 1),
                )
            else:
                self.player.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT | Gst.SeekFlags.SNAP_AFTER,
                    self.frame_to_time(self.current_position_frame + 1),
                )
        else:
            frame = self.current_position_frame
            if direction == "backward":
                jumpto = self.get_keyframe_in_front_of_frame(self.keyframes, frame)
            else:
                jumpto = self.get_keyframe_after_frame(self.keyframes, frame)
            self.log.debug(f"jumpto = {jumpto}")
            self.jump_to(frames=jumpto)

        if playing:
            self.player.set_state(Gst.State.PLAYING)

    def jump_to(
        self, frames=None, seconds=None, nanoseconds=0, flags=Gst.SeekFlags.ACCURATE, playing=None,
    ):
        if frames:
            if frames >= self.get_frames():
                frames = self.get_frames() - 1

            nanoseconds = self.frame_to_time(frames)

        elif seconds:
            nanoseconds = seconds * Gst.SECOND

        if nanoseconds < 0:
            self.log.debug("restrict start")
            nanoseconds = 0
        elif nanoseconds > self.videolength:
            self.log.debug("restrict end")
            nanoseconds = self.videolength
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | flags, int(nanoseconds))
        if playing:
            self.player.set_state(Gst.State.PLAYING)

    def set_playback_direction(self, direction: float):
        if direction > 0:
            set_direction = Gst.Event.new_seek(
                # rate (float) – The new playback rate
                direction,
                # format (Gst.Format) – The format of the seek values
                Gst.Format.TIME,
                # flags (Gst.SeekFlags) – The optional seek flags
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                # start_type (Gst.SeekType) – The type and flags for the new start position
                Gst.SeekType.SET,
                # start (int) – The value of the new start position
                self.current_position_time,
                # stop_type (Gst.SeekType) – The type and flags for the new stop position
                Gst.SeekType.NONE,
                # stop (int) – The value of the new stop position
                0,
            )
        else:
            set_direction = Gst.Event.new_seek(
                direction,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                Gst.SeekType.SET,
                0,
                Gst.SeekType.SET,
                self.current_position_time,
            )
        _ = self.gtksink.send_event(set_direction)

    def frame_step(self, direction: float, amount: int):
        """ Create a new step event. The purpose of the step event is to instruct a sink to skip amount (expressed in
            format) of media. It can be used to implement stepping through the video frame by frame or for doing fast
            trick modes.
            A rate of <= 0.0 is not allowed. Pause the pipeline, for the effect of rate = 0.0 or first reverse the
            direction of playback using a seek event to get the same effect as rate < 0.0.
            The flush flag will clear any pending data in the pipeline before starting the step operation.
            The intermediate flag instructs the pipeline that this step operation is part of a larger step operation.
        """
        # This does not work if the direction of playback is backwards (Audio: cannot flush buffer, or the like).
        if direction < 0:
            self.set_playback_direction(direction)
        frame_step = Gst.Event.new_step(
            Gst.Format.BUFFERS,  # format (Gst.Format) – the format of amount
            amount,  # amount (int) – the amount of data to step
            abs(direction),  # rate (float) – the step rate
            True,  # flush (bool) – flushing steps
            False,  # intermediate (bool) – intermediate steps
        )
        _ = self.player.send_event(frame_step)
        if direction < 0:
            self.set_playback_direction(-direction)

    def test_cut_part1(self, test_all):
        test_cut_offset_secs = self.config.get("cutinterface", "test_cut_offset_secs")
        if not test_all:
            if self.cut_selected != -1:
                if self.marker_a > 0 and 0 < self.marker_b < self.frames - 1:
                    # A cut is selected and it is neither the first nor the last
                    self.test_cut = True
                    segment1 = Gst.Event.new_seek(
                        # rate (float) – The new playback rate
                        1.0,
                        # format (Gst.Format) – The format of the seek values
                        Gst.Format.TIME,
                        # flags (Gst.SeekFlags) – The optional seek flags
                        Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE | Gst.SeekFlags.SEGMENT,
                        # start_type (Gst.SeekType) – The type and flags for the new start position
                        Gst.SeekType.SET,
                        # start (int) – The value of the new start position
                        self.frame_to_time(self.marker_a - 1) - test_cut_offset_secs * Gst.SECOND,
                        # stop_type (Gst.SeekType) – The type and flags for the new stop position
                        Gst.SeekType.SET,
                        # stop (int) – The value of the new stop position
                        self.frame_to_time(self.marker_a - 1),
                    )
                    _ = self.gtksink.send_event(segment1)
                    self.player.set_state(Gst.State.PLAYING)
                else:
                    if self.marker_a == 0:
                        start_play = self.frame_to_time(self.marker_b + 1)
                        end_play = self.frame_to_time(self.marker_b + 1) + test_cut_offset_secs * Gst.SECOND
                    else:
                        start_play = self.frame_to_time(self.marker_a - 1) - test_cut_offset_secs * Gst.SECOND
                        end_play = self.frame_to_time(self.marker_a - 1)
                    self.test_cut = True
                    segment1 = Gst.Event.new_seek(
                        1.0,
                        Gst.Format.TIME,
                        Gst.SeekFlags.ACCURATE | Gst.SeekFlags.FLUSH,  # | Gst.SeekFlags.SEGMENT,
                        Gst.SeekType.SET,
                        start_play,
                        Gst.SeekType.SET,
                        end_play,
                    )
                    _ = self.gtksink.send_event(segment1)
                    self.player.set_state(Gst.State.PLAYING)
        else:
            print("Funktion 'Alle Schnitte testen' ist noch nicht implementiert.")
            raise NotImplementedError

    def test_cut_part2(self):
        test_cut_offset_secs = self.config.get("cutinterface", "test_cut_offset_secs")
        segment2 = Gst.Event.new_seek(
            1.0,
            Gst.Format.TIME,
            Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET,
            self.frame_to_time(self.marker_b + 1),
            Gst.SeekType.SET,
            self.frame_to_time(self.marker_b + 1) + test_cut_offset_secs * Gst.SECOND,
        )
        _ = self.gtksink.send_event(segment2)
        self.player.set_state(Gst.State.PLAYING)

    def preferences_window_pages_visible(self, visible: bool):
        page_count = self.app.gui.preferences_window.builder.get_object("notebook").get_n_pages()
        for page_num in range(page_count):
            # if page_num not in [6]:
            #     self.app.gui.preferences_window.builder.get_object("notebook").get_nth_page(page_num).set_visible(
            #         visible
            #     )
            if page_num == 6:  # Page Cutinterface
                widgets = [
                    "lbl_moviewindow_x",
                    "lbl_moviewindow_y",
                    "spinbutton_x",
                    "spinbutton_y",
                    "button_reset_size_moviewindow",
                ]
                if self.timecode_frame is None or len(self.timecode_frame) == 0:
                    widgets.append("check_alt_time_frame_conv")
                for widget in widgets:
                    self.app.gui.preferences_window.builder.get_object(widget).set_sensitive(visible)


def new():
    glade_filename = otrvpath.getdatapath("ui", "CutinterfaceDialog.glade")
    builder = Gtk.Builder.new_from_file(glade_filename)
    # builder.add_from_file(glade_filename)
    dialog = builder.get_object("cutinterface_dialog")
    # dialog.gui = gui
    return dialog
