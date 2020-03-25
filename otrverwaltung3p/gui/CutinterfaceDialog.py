# -*- coding: utf-8 -*-
# BEGIN LICENSE
# This file is in the public domain
# END LICENSE

from pathlib import Path
import logging
import os
import re
import time

import cairo  # gcurse: DO NOT DELETE

from gi import require_version
require_version('Gdk', '3.0')
require_version('Gst', '1.0')
require_version('GstPbutils', '1.0')
require_version('Gtk', '3.0')
from gi.repository import GLib, Gdk, Gst, GstPbutils, Gtk

Gst.init(None)

# from otrverwaltung3p.elements import KeySeekElement
# from otrverwaltung3p.elements import DecoderWrapper
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p import cutlists
from otrverwaltung3p.gui import LoadCutDialog
from otrverwaltung3p.actions.cut import Cut
from otrverwaltung3p.gui.widgets.movieBox import MovieBox  # gcurse: DO NOT DELETE


class CutinterfaceDialog(Gtk.Dialog, Gtk.Buildable, Cut):
    __gtype_name__ = "CutinterfaceDialog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(self.__class__.__name__)

        self.atfc = True
        self.builder = None
        self.bus = None
        self.buttonClose = False
        self.buttonOk = False
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.current_frame_position = 0
        self.cut_selected = -1
        self.cut_selected_last = -1
        self.cutlist = None
        self.cutslistmodel = None
        self.filename = ''
        self.fileuri = None
        self.frames = 0
        self.frame_timecode = self.timecode_frame = {}
        self.getVideoLength = True
        self.hide_cuts = False
        self.img_pause = self.img_play = None
        self.initial_cutlist = []
        self.initial_cutlist_in_frames = False
        self.is_playing = False
        self.keyframes = None
        self.last_direction = "none"
        self.marker_a, self.marker_b = 0, -1
        self.movie_box = None
        self.player = None
        self.seek_distance = 0
        self.seek_distance_default = 0
        self.slider = None
        self.state = Gst.State.NULL
        self.timelines = [[]]
        self.timeoutcontrol = True
        self.timer = None
        self.videolength = 0
        self.widgets_tt_names = ['button_play', 'button_a', 'button_b', 'button_remove', 'button_keyfast_back',
                                 'button_seek2_back', 'button_seek1_back', 'button_fast_back', 'button_back',
                                 'button_forward', 'button_fast_forward', 'button_seek1_forward', 'button_seek2_forward',
                                 'button_keyfast_forward', 'button_jump_to_marker_a', 'button_jump_to_marker_b',
                                 'load_button']
        self.widgets_tt_obj = []

    def do_parser_finished(self, builder):
        self.log.debug("funtion start")
        self.builder = builder
        self.builder.connect_signals(self)
        self.slider = self.builder.get_object('slider')
        self.slider.set_digits(0)
        self.slider.set_draw_value(False)

        self.movie_box = self.builder.get_object('movie_box').movie_widget
        self.player = self.builder.get_object('movie_box').player
        # Create bus to get events from GStreamer player
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect("message::state-changed", self.on_state_changed)
        self.bus.connect("message", self.on_message)

        self.hide_cuts = self.builder.get_object('checkbutton_hide_cuts').get_active()

        self.cutslistmodel = self.builder.get_object('cutslist')
        cutslistselection = self.builder.get_object('cutsview').get_selection()
        cutslistselection.connect('changed', self.on_cuts_selection_changed)

        button_delete_cut = self.builder.get_object('button_delete_cut')
        button_delete_cut.set_sensitive(False)
        button_deselect = self.builder.get_object('button_deselect')
        button_deselect.set_sensitive(False)

        for name in self.widgets_tt_names:
            self.widgets_tt_obj.append(self.builder.get_object(name))

    def get_cuts_in_frames(self, cuts, in_frames):
        if not cuts:
            res = [(0, self.frames)]
            self.log.debug(f"Framelist: {self.frames}")
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
        cutlist.intended_app = 'VirtualDub.exe'
        if filename is not None and os.path.exists(filename):
            cutlist.local_filename = filename
            cutlist.read_from_file()
            cutlist.read_cuts()
            if (cutlist.cuts_frames and cutlist.filename_original != os.path.basename(self.filename)) \
                    or (not cutlist.cuts_frames and cutlist.cuts_seconds):
                cutlist.fps = self.framerate_num / self.framerate_denom
                cutlist.cuts_frames = []
                self.log.info("Calculate frame values from seconds.")
                for start, duration in cutlist.cuts_seconds:
                    cutlist.cuts_frames.append((round(start * cutlist.fps), round(duration * cutlist.fps)))

            if cutlist.author != self.config.get('general', 'cutlist_username'):
                cutlist.usercomment = self.config.get('general', 'cutlist_comment') + '; Vorlage von ' + \
                                                      cutlist.author + '; ' + cutlist.usercomment
            if cutlist.cuts_frames:
                self.initial_cutlist = cutlist.cuts_frames
                self.initial_cutlist_in_frames = True
            else:
                self.initial_cutlist = cutlist.cuts_seconds
                self.initial_cutlist_in_frames = False

        else:
            cutlist.usercomment = self.config.get('general', 'cutlist_comment')
            self.initial_cutlist = []
            self.initial_cutlist_in_frames = True

        if self.timer is not None:  # Running
            self.timelines.append(self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames))

        if self.slider:
            self.slider.queue_draw()
        return cutlist

    def set_cuts(self, cutlist, cuts):
        self.log.debug("Function start")
        self.log.debug(f"var cutlist: {cutlist}")
        self.log.debug(f"var cuts: {cuts}")
        cutlist.fps = float(self.framerate_num) / float(self.framerate_denom)
        cutlist.cuts_frames = cuts
        cutlist.cuts_seconds = []
        cutlist.app = 'OTR-Verwaltung3p;Cutinterface'
        for start, duration in cuts:
            s = start * self.framerate_denom / float(self.framerate_num)
            d = duration * self.framerate_denom / float(self.framerate_num)
            cutlist.cuts_seconds.append((s, d))

    def run_(self, filename, cutlist, app):
        self.log.debug("function start")
        self.set_title("Cutinterface")
        self.app = app
        self.config = app.config
        self.fileuri = Path(filename).as_uri()
        self.filename = str(Path(filename))
        self.seek_distance_default = self.config.get('cutinterface', 'seek_distance_default') * Gst.SECOND
        self.seek_distance = self.seek_distance_default
        self.atfc = self.config.get('general', 'alt_time_frame_conv')
        # Setup buttons
        seek1 = str(self.config.get('cutinterface', 'seek1'))
        seek2 = str(self.config.get('cutinterface', 'seek2'))
        show_tooltips = self.config.get('cutinterface', 'show_tooltips')
        self.builder.get_object('button_seek2_back').set_label(f"<< {seek2} s")
        self.builder.get_object('button_seek2_forward').set_label(f"{seek2} s >>")
        self.builder.get_object('button_seek1_back').set_label(f"<< {seek1} s")
        self.builder.get_object('button_seek1_forward').set_label(f"{seek1} s >>")
        self.builder.get_object('switch_tooltip').set_active(show_tooltips)
        if not show_tooltips:
            self.on_switch_tooltip_state_set(None)

        if self.atfc:
            self.frame_timecode, self.timecode_frame, error = self.get_timecodes_from_file(self.filename)
            if self.frame_timecode is None:
                self.log.warning("Error: Timecodes konnten nicht ausgelesen werden.")

        self.keyframes, error = self.get_keyframes_from_file(self.filename)
        if self.keyframes is None:
            self.log.warning("Error: Keyframes konnten nicht ausgelesen werden.")

        self.movie_box.set_size_request(self.config.get('general', 'cutinterface_resolution_x'),
                                        self.config.get('general', 'cutinterface_resolution_y'))
        # Make window a bit bigger than natural size to avoid size changes
        ci_window = self.builder.get_object('cutinterface_dialog')
        ci_window.set_size_request(int(ci_window.size_request().width * 1.05),
                                   int(ci_window.size_request().height * 1.05))

        self.hide_cuts = self.config.get('general', 'cutinterface_hide_cuts')

        # get video info
        self.log.debug("Discoverer start")
        # Discoverer timeout set to 5 * Gst.SECOND
        self.discoverer = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        self.d = self.discoverer.discover_uri(self.fileuri)
        for vinfo in self.d.get_video_streams():
            self.framerate_num = vinfo.get_framerate_num()
            self.framerate_denom = vinfo.get_framerate_denom()
            self.videowidth = vinfo.get_width()
            self.videoheight = vinfo.get_height()

        self.log.debug(f"framerate_num: {self.framerate_num}")
        self.log.debug(f"framerate_denom: {self.framerate_denom}")
        self.videolength = self.d.get_duration()
        self.frames = round(self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND)
        self.cutlist = self.load_cutlist(cutlist)
        self.timelines = [self.get_cuts_in_frames(self.initial_cutlist,
                                                  self.initial_cutlist_in_frames)]

        # MENORYLEAK
        del self.d
        del self.discoverer

        # Set player uri only after discoverer is done
        self.player.set_property('uri', self.fileuri)
        try:
            if self.config.get('general', 'vol_adjust_on'):
                vol_adjust = re.findall("[a-z.0-9,]+", self.config.get('general', 'vol_adjust'))
                if vol_adjust:
                    # get station name from video filename
                    parts = self.filename.split('_'); parts.reverse(); station = parts[3]
                    for adj in vol_adjust:
                        if adj.split(",")[0].lower() in station:
                            self.player.set_property('volume', float(adj.split(",")[1]))
                            self.log.info(f"Cutinterface volume: {self.player.get_property('volume')}")
                            break
        except IndexError:
            pass

        self.ready_callback()

        self.timer2 = GLib.timeout_add(600, self.update_listview)
        # Reset cursor MainWindow
        self.app.gui.main_window.get_window().set_cursor(None)

        if Gtk.ResponseType.OK == self.run():
            self.set_cuts(self.cutlist, self.timelines[-1])
        else:
            self.set_cuts(self.cutlist, [])

        # Set return value of self.tick to false, so self.timer
        # is stopped if it still exists
        self.timeoutcontrol = False

        return self.cutlist

    def ready_callback(self):
        self.log.debug("Function start")
        self.builder.get_object('label_filename').set_markup(f"{os.path.basename(self.filename)}")

        self.update_timeline()
        self.update_listview()

        self.timer = GLib.timeout_add(200, self.tick)

    def tick(self):
        self.update_frames_and_time()
        self.update_slider()
        self.builder.get_object('checkbutton_hide_cuts').set_active(self.hide_cuts)
        return self.timeoutcontrol

    def set_marker(self, a=None, b=None):
        """ Set markers a and/or b to a specific frame position and update the buttons """

        if a is not None:
            self.marker_a = a

            if a != -1 and self.marker_b < 0:
                    self.marker_b = self.get_frames()-1

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
            self.builder.get_object('button_jump_to_marker_a').set_label('-')
        else:
            self.builder.get_object('button_jump_to_marker_a').set_label(str(int(self.marker_a)))

        if self.marker_b == -1:
            self.builder.get_object('button_jump_to_marker_b').set_label('-')
        else:
            self.builder.get_object('button_jump_to_marker_b').set_label(str(int(self.marker_b)))

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

        return self.frames-1

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

        return durations-1

    def invert_simple(self, cuts):
        # inverts the cuts (between timeline and cut-out list) assuming the list is flawless
        # and should be faster than the full version below
        inverted = []
        try:
            if cuts[0][0] > 0:
                inverted.append( (0, cuts[0][0]) )

            next_start = cuts[0][0] + cuts[0][1]
            for start, duration in cuts[1:]:
                inverted.append( (next_start, start - next_start) )
                next_start = start + duration

            if next_start < self.frames:
                inverted.append( (next_start, self.frames - next_start) )
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
                if duration < 0:                    # correct invalid values
                    duration = - duration
                    start = start - duration + 1

                if start < 0:
                    start = 0

                if start + duration > self.frames:
                    duration = self.frames - start

                if start < next_start:              # handle overlapping cuts
                    next_start = max(next_start, start + duration)
                else:
                    if start - next_start > 0:      # don't add cuts with zero length
                        inverted.append( (next_start, start - next_start) )

                    next_start = start + duration

            if next_start < self.frames:
                inverted.append( (next_start, self.frames - next_start) )
        except IndexError:
            pass
        return inverted

    def remove_segment(self, rel_s, rel_d):
        self.log.debug("\033[1;31m-- Entering remove_segment\033[1;m")
        self.log.debug(f"Current timeline is: {self.timelines[-1]}")

        abs_start = self.get_absolute_position(rel_s)
        abs_end = self.get_absolute_position(rel_s + rel_d - 1)

        inverted_timeline = self.invert_simple(self.timelines[-1])
        inverted_timeline.append((abs_start, abs_end - abs_start + 1))
        self.timelines.append(self.invert_full(inverted_timeline))

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
            self.jump_to(frames=abs_end+1)

    def get_frames(self):
        """ Returns the current number of frames to be shown. """
        if self.hide_cuts:
            frames = sum([duration for start, duration in self.timelines[-1]])
        else:
            frames = self.frames

        return frames

    def query_position(self, gst_format):
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
            try:
                success, current_position = self.query_position(Gst.Format.TIME)
                duration = self.player.query_duration(Gst.Format.TIME)[1]
                if not success:
                    return
            except Exception as e:  # manchmal geht es nicht, bspw. wenn gerade erst geseekt wurde
                self.log.warning(f"Exception: {e}")
                return

            if self.atfc:
                self.current_frame_position = self.time_to_frame(current_position)
            else:
                self.current_frame_position = current_position * self.framerate_num / self.framerate_denom / Gst.SECOND

            if self.keyframes is not None and round(self.current_frame_position) in self.keyframes:
                string = 'Frame(K): '
            else:
                string = 'Frame: '
            self.builder.get_object('label_time')\
                .set_text(string + f'{self.current_frame_position} / {self.get_frames() - 1}, '
                                   f'Zeit: {self.convert_sec(current_position)} / {self.convert_sec(duration)}')

    def update_slider(self):
        try:
            nanosecs = self.player.query_position(Gst.Format.TIME)[1]
            # block seek handler so we don't seek when we set_value()
            self.builder.get_object('slider').handler_block_by_func(self.on_slider_value_changed)
            if self.atfc:
                frame = self.time_to_frame(nanosecs)
            else:
                frame = nanosecs * self.framerate_num / self.framerate_denom / Gst.SECOND
            self.builder.get_object('slider').set_value(frame)
            self.builder.get_object('slider').handler_unblock_by_func(self.on_slider_value_changed)
        # catch Gst.QueryError
        except TypeError as typeError:
            self.log.debug(f"Exeption: {typeError}")

    def seeker(self, direction):
        """ Jump forward or backward by self.seek_distance.
            Value is divided by 2 on each direction change.
        """
        if not direction == 'reset' and not self.last_direction == 'none':
            # if direction has changed, bisect the seek_distance
            if not direction == self.last_direction:
                self.seek_distance = int(self.seek_distance / 2)
                self.log.debug(f"BISECT: direction: {direction}, last_direction: {self.last_direction}, "
                               f"seek_distance: {self.seek_distance / Gst.SECOND}s")
        if direction == 'left':
            self.jump_relative_time(self.seek_distance * -1)
            self.last_direction = direction
        elif direction == 'right':
            self.jump_relative_time(self.seek_distance)
            self.last_direction = direction
        elif direction == 'reset':
            self.seek_distance = self.seek_distance_default
            self.last_direction = 'none'
            self.log.debug(f"RESET: direction: {direction}, last_direction: {self.last_direction}, "
                           f"seek_distance: {self.seek_distance / Gst.SECOND}s")

    def update_listview(self):
        self.log.debug("Function start")
        listview = self.builder.get_object('cutsview')
        listselection = listview.get_selection()
        listmodel, listiter = listselection.get_selected()
        if listiter:
            tree_path = listmodel.get_path(listiter)
        listview.set_model(None)  # for speeding up the update of the view
        listmodel.clear()

        if not self.getVideoLength:
            inverted = self.invert_simple(self.timelines[-1])
            for start, duration in inverted:
                listmodel.append((start, start + duration - 1))

        listview.set_model(listmodel)
        if listiter:
            listselection.select_path(tree_path)

    def select_cut(self, direction):
        listview = self.builder.get_object('cutsview')
        listselection = listview.get_selection()
        listmodel, listiter = listselection.get_selected()
        rows = listmodel.iter_n_children(None)
        if listiter:  # A cut is selected
            if direction =="next":
                listiter = listmodel.iter_next(listiter)
                if listiter is None:
                    listiter = listmodel.get_iter_first()
            elif direction =="prev":
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
            self.builder.get_object('button_remove').set_label('Entfernen')
        else:
            self.builder.get_object('button_remove').set_label('Übernehmen')

    def convert_sec(self, time):
        s, rest = divmod(time, Gst.SECOND)

        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)

        time_str = "%02i:%02i:%02i.%03i" % (h, m, s, rest*1000/Gst.SECOND)

        return time_str

    def contextmenu_label_filename(self, *args):
        menu = Gtk.Menu()
        menuitem1 = Gtk.MenuItem("Dateinamen kopieren")
        menu.append(menuitem1)
        menuitem1.connect("activate", self.contextmenu_label_filename_copy)
        menuitem2 = Gtk.MenuItem("Dateinamen mit Pfad kopieren")
        menu.append(menuitem2)
        menuitem2.connect("activate", self.contextmenu_label_filename_copypath)
        menu.show_all()
        menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def contextmenu_label_filename_copy(self, *args):
        self.clipboard.set_text(os.path.basename(self.filename), -1)

    def contextmenu_label_filename_copypath(self, *args):
        self.clipboard.set_text(self.filename, -1)

    # gstreamer bus signals #

    def on_error(self, bus, msg):
        err, debug = msg.parse_error()
        self.log.error(f"Error: {err}, {debug}")
        self.player.set_state(Gst.State.NULL)
        self.builder.get_object('label_time').set_text('Frame: 0/0, Zeit 0s/0s')

    def on_eos(self, bus, msg):
        self.player.set_state(Gst.State.NULL)
        self.state = Gst.State.NULL
        self.builder.get_object('label_time').set_text('Frame: 0/0, Zeit 0s/0s')

    def on_state_changed(self, bus, msg):
        old, new, pending = msg.parse_state_changed()
        if not msg.src == self.player:
            # not from the player, ignore
            return
        self.state = new

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ASYNC_DONE:
            if self.getVideoLength:
                self.getVideoLength = not self.getVideoLength
                self.log.debug("Async done")
                self.videolength = self.player.query_duration(Gst.Format.TIME)[1]
                self.frames = round(self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND)  # ROUND
                self.slider.set_range(0, self.get_frames())
                self.timelines = [self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames)]
                self.builder.get_object('slider').set_range(0, self.get_frames())
                self.slider.queue_draw()
                self.log.debug(f"Timelines: {self.timelines}")
                self.log.debug(f"framerate_num: {self.framerate_num}")
                self.log.debug(f"framerate_denom: {self.framerate_denom}")
                self.log.debug(f"videolength: {self.videolength}")
                self.log.debug(f"Number of frames: {self.frames}")

    # signals #

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
        mod_ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        mod_shift = (event.state & Gdk.ModifierType.SHIFT_MASK)
        mod_alt = (event.state & Gdk.ModifierType.MOD1_MASK)

        if event.type == Gdk.EventType.KEY_PRESS:
            # CTRL
            if not mod_shift and not mod_alt and mod_ctrl:
                if keyname == 'LEFT':
                    self.on_button_seek2_back_clicked(None)
                    return True
                if keyname == 'RIGHT':
                    self.on_button_seek2_forward_clicked(None)
                    return True
                if keyname == 'DELETE':
                    self.on_button_delete_cut_clicked(None)
                    return False
            # SHIFT
            if not mod_ctrl and not mod_alt and mod_shift:
                if keyname == 'LEFT':
                    # -10 frames
                    self.on_button_fast_back_clicked(None)
                    return True
                elif keyname == 'RIGHT':
                    # +10 frames
                    self.on_button_fast_forward_clicked(None)
                    return True
                elif keyname == 'UP':
                    # +100 frames
                    self.on_button_seek1_forward_clicked(None)
                    return True
                elif keyname == 'DOWN':
                    # -100 frames
                    self.on_button_seek1_back_clicked(None)
                    return True
                elif keyname == 'DEL':
                    self.on_button_delete_cut_clicked(None)
                    return True
            # ALT
            if not mod_ctrl and not mod_shift and mod_alt:
                if keyname == 'LEFT':
                    self.seeker("left")
                    return True
                if keyname == 'RIGHT':
                    self.seeker("right")
                    return True
                if keyname == 'DOWN':
                    self.seeker("reset")
                    return True
            # Not SHIFT, not CTRL, not ALT
            if not mod_ctrl and not mod_shift and not mod_alt:
                if keyname == 'LEFT':
                    return True
                elif keyname == 'RIGHT':
                    return True
                elif keyname == 'UP':
                    self.on_button_keyfast_forward_clicked(None)
                    return True
                elif keyname == 'DOWN':
                    self.on_button_keyfast_back_clicked(None)
                    return True
                elif keyname == 'HOME' or keyname == 'BRACKETLEFT':
                    self.on_button_a_clicked(None)
                    return True
                elif keyname == 'END' or keyname == 'BRACKETRIGHT':
                    self.on_button_b_clicked(None)
                    return True
                elif keyname == 'PAGE_UP':
                    self.on_button_jump_to_marker_a_clicked(None)
                    return True
                elif keyname == 'PAGE_DOWN':
                    self.on_button_jump_to_marker_b_clicked(None)
                    return True
                elif keyname == 'DELETE':
                    self.on_button_remove_clicked(None)
                    return True
                elif keyname == 'L':
                    self.on_load_button_clicked(None)
                    return True
                elif keyname == 'SPACE':
                    self.on_button_play_pause_clicked(self.builder.get_object('button_play'))
                    return True
                elif keyname == 'N':
                    self.select_cut('next')
                    return True
                elif keyname == 'B':
                    self.select_cut('prev')
                    return True
                elif keyname == 'ESCAPE':
                    self.on_button_deselect_clicked(None)
                    return True
                else:
                    self.log.debug(f"keyname: {keyname}")
        return False

    def on_window_key_release_event(self, widget, event, *args):
        """handle keyboard events"""
        keyname = Gdk.keyval_name(event.keyval).upper()
        mod_ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        mod_shift = (event.state & Gdk.ModifierType.SHIFT_MASK)
        if not mod_ctrl and not mod_shift:
            if event.type == Gdk.EventType.KEY_RELEASE:
                time.sleep(0.05)
                if keyname == 'LEFT':
                    self.on_button_back_clicked(None)
                    return True
                elif keyname == 'RIGHT':
                    self.on_button_forward_clicked(None)
                    return True
        return False

    @staticmethod
    def on_slider_key_press_event(widget, event):
        # override normal keybindings for slider (HOME and END are used for markers)
        keyname = Gdk.keyval_name(event.keyval).upper()
        if keyname == 'HOME' or keyname == 'END':
            return True

    def on_label_filename_button_press_event(self, widget, event):
        print(event.type)
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button is Gdk.BUTTON_SECONDARY:  # right-click
            self.contextmenu_label_filename()

    def on_slider_value_changed(self, slider):
        frames = slider.get_value()
        self.log.debug(f"Slider value = {frames}")
        if frames >= self.get_frames():
            self.log.debug("slider.get_value() >= self.get_frames(). Restricting.")
            frames = self.get_frames() - 1
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                frames * Gst.SECOND * self.framerate_denom / self.framerate_num)
        if not self.is_playing:
            self.log.debug("update_frames_and_time() by slider change")
            self.update_frames_and_time()

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
        self.frames = round(self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND)

        if self.atfc:
            nano_seconds = self.frame_to_time(self.time_to_frame(nano_seconds) + frames)
        else:
            nano_seconds += frames * (1 * Gst.SECOND * self.framerate_denom / self.framerate_num)

        self.jump_to(nanoseconds=nano_seconds, flags=flags)

    def jump_key(self, direction, playing=None):
        frame = self.current_frame_position
        success, current_position = self.query_position(Gst.Format.TIME)
        if self.config.get('general', 'new_keyframe_search'):  # gcurse new_keyframe_search
            if direction == "backward":
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT |
                                        Gst.SeekFlags.SNAP_BEFORE, current_position - 1)
            else:
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT |
                                        Gst.SeekFlags.SNAP_AFTER, current_position + 1)
        else:
            if direction == "backward":
                jumpto = self.get_keyframe_in_front_of_frame(self.keyframes, frame)
            else:
                jumpto = self.get_keyframe_after_frame(self.keyframes, frame)
            self.log.debug(f"jumpto = {jumpto}")
            self.jump_to(frames=jumpto)

        if playing:
            self.player.set_state(Gst.State.PLAYING)

    def jump_to(self, frames=None, seconds=None, nanoseconds=0, flags=Gst.SeekFlags.ACCURATE, playing=None):
        if frames:
            if frames >= self.get_frames():
                frames = self.get_frames()-1

            if self.atfc:
                nanoseconds = self.frame_to_time(frames)
            else:
                nanoseconds = frames * Gst.SECOND * self.framerate_denom / self.framerate_num
        elif seconds:
            nanoseconds = seconds * Gst.SECOND

        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | flags, int(nanoseconds))
        if playing:
            self.player.set_state(Gst.State.PLAYING)

    def on_button_keyfast_back_clicked(self, widget, data=None):
        if self.is_playing:
            was_playing = True
            self.player.set_state(Gst.State.PAUSED)
        else:
            was_playing = False

        self.jump_key('backward', was_playing)

    def on_button_seek2_back_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get('cutinterface', 'seek2')) * Gst.SECOND * -1)

    def on_button_seek1_back_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get('cutinterface', 'seek1')) * Gst.SECOND * -1)
        # ~ self.jump_relative(-100)

    def on_button_fast_back_clicked(self, widget, data=None):
        self.jump_relative(-10)

    def on_button_back_clicked(self, widget, data=None):
        self.jump_relative(-1)

    def on_button_forward_clicked(self, widget, data=None):
        self.jump_relative(1)

    def on_button_fast_forward_clicked(self, widget, data=None):
        self.jump_relative(10)

    def on_button_seek1_forward_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get('cutinterface', 'seek1')) * Gst.SECOND)
        # ~ self.jump_relative(100)

    def on_button_seek2_forward_clicked(self, widget, data=None):
        self.jump_relative_time(int(self.config.get('cutinterface', 'seek2')) * Gst.SECOND)

    def on_button_keyfast_forward_clicked(self, widget, data=None):
        if self.is_playing:
            was_playing = True
            self.player.set_state(Gst.State.PAUSED)
        else:
            was_playing = False
        self.jump_key('forward', was_playing)

    def on_button_a_clicked(self, *args):
        # TODO: warn if Marker A = B or distance between them to low
        self.log.debug(f'marker a = {self.current_frame_position}')
        self.set_marker(a=self.current_frame_position)
        self.slider.queue_draw()

    def on_button_b_clicked(self, *args):
        # TODO: warn if Marker A = B or distance between them to low
        self.log.debug(f'marker b = {self.current_frame_position}')
        self.set_marker(b=self.current_frame_position)
        self.slider.queue_draw()

    def on_button_remove_clicked(self, widget):
        self.log.debug("Function start")
        self.log.debug(f"marker a = {self.marker_a}")
        self.log.debug(f"marker b = {self.marker_b}")
        if self.is_remove_modus():
            if self.marker_a >= 0 and self.marker_b >= 0:
                self.remove_segment(self.marker_a, self.marker_b-self.marker_a+1)
                if self.cut_selected >= 0:
                    self.builder.get_object('cutsview').get_selection().unselect_all()

                self.set_marker(a=-1, b=-1)
                self.slider.queue_draw()

        else:
            if self.marker_a >= 0 and self.marker_b >= 0:
                inverted = self.invert_simple(self.timelines[-1])
                inverted[self.cut_selected] = (self.marker_a, self.marker_b-self.marker_a+1)
                self.timelines.append(self.invert_full(inverted))
                self.builder.get_object('cutsview').get_selection().unselect_all()
                self.slider.queue_draw()
                self.update_listview()

        self.slider.clear_marks()
        self.marker_a = -1
        self.marker_b = -1

    def on_button_undo_clicked(self, *args):
        if len(self.timelines) > 1:
            del self.timelines[-1]
            self.update_timeline()
            self.update_listview()
            self.slider.queue_draw()

    def on_button_jump_to_marker_a_clicked(self, widget):
        if self.marker_a >= 0:
            self.jump_to(frames=self.marker_a)

    def on_button_jump_to_marker_b_clicked(self, widget):
        if self.marker_b >= 0:
            self.jump_to(frames=self.marker_b)

    def on_checkbutton_hide_cuts_toggled(self, widget):
        self.log.debug("Function start")
        self.is_playing = False
        self.player.set_state(Gst.State.PAUSED)
        self.update_frames_and_time()
        marker_a = self.get_absolute_position(self.marker_a)
        marker_b = self.get_absolute_position(self.marker_b)
        pos = self.get_absolute_position(self.current_frame_position)

        self.hide_cuts = widget.get_active()
        self.config.set('general', 'cutinterface_hide_cuts', self.hide_cuts)
        self.update_timeline()
        if self.hide_cuts:
            self.set_marker(self.get_relative_position(marker_a), self.get_relative_position(marker_b))
        else:
            self.builder.get_object('cutsview').get_selection().unselect_all()
            self.set_marker(marker_a, marker_b)

        self.update_remove_button()
        self.slider.queue_draw()

        # print "Relative position: ", self.get_relative_position(pos)
        time.sleep(0.2)
        if self.hide_cuts:
            self.jump_to(frames=self.get_relative_position(pos))
        else:
            self.jump_to(frames=pos)

    def on_cuts_selection_changed(self, treeselection):
        self.log.debug("Function start")
        cutslist, cutsiter = treeselection.get_selected()
        button_delete_cut = self.builder.get_object('button_delete_cut')
        button_deselect = self.builder.get_object('button_deselect')

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
            self.set_marker(a,b)
            self.slider.queue_draw()
        else:
            self.cut_selected = -1
            self.update_remove_button()
            button_delete_cut.set_sensitive(False)
            button_deselect.set_sensitive(False)

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
            pos = self.get_absolute_position(self.current_frame_position)

        inverted = self.invert_simple(self.timelines[-1])
        del inverted[self.cut_selected]
        self.timelines.append(self.invert_full(inverted))

        self.builder.get_object('cutsview').get_selection().unselect_all()

        if self.hide_cuts:
            self.update_timeline()
            marker_a = self.get_relative_position(marker_a)
            marker_b = self.get_relative_position(marker_b)
            pos = self.get_relative_position(pos)
            self.set_marker(marker_a,marker_b)
            time.sleep(0.2)
            self.jump_to(frames=pos)
            if playing:
                self.is_playing = True
                self.player.set_state(Gst.State.PLAYING)

        self.slider.queue_draw()
        self.update_listview()

    def on_button_deselect_clicked(self, widget):
        self.log.debug("Function start")
        self.builder.get_object('cutsview').get_selection().unselect_all()
        self.slider.clear_marks()
        self.marker_a = -1
        self.marker_b = -1

    def on_slider_draw_event(self, widget, cairo_context):
        self.redraw(cairo_context)

    def redraw(self, cairo_context):
        slider = self.builder.get_object('slider')

        border = 11
        if self.get_frames() != 0:
            # draw line from marker a to marker b and for all cuts
            try:
                one_frame_in_pixels = (slider.get_allocation().width - 2*border) / float(self.get_frames())
                # draw only if ...
                if self.marker_a != self.marker_b and self.marker_a >= 0 and self.marker_b >= 0:
                    self.log.debug(f"Slider allocation size: {slider.get_allocation().width} x {slider.get_allocation().height}")
                    self.log.debug(f"one_frame_in_pixels: {one_frame_in_pixels}")
                    marker_a = border + int(round(self.marker_a * one_frame_in_pixels))
                    marker_b = border + int(round(self.marker_b * one_frame_in_pixels))

                    cairo_context.set_source_rgb(1.0, 0.0, 0.0)  # red
                    cairo_context.rectangle(marker_a, 0, marker_b - marker_a, 5)
                    cairo_context.fill()

                if not self.hide_cuts:
                    inverted = self.invert_simple(self.timelines[-1])
                    for start, duration in inverted:
                        pixel_start = border + int(round(start * one_frame_in_pixels))
                        pixel_duration = int(round(duration * one_frame_in_pixels))

                        # draw keyframe cuts that don't need reencoding in a different color

                        if round(start) in self.keyframes and (round(start + duration) in self.keyframes or round(start + duration) == self.frames):
                            cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                            cairo_context.rectangle(pixel_start, slider.get_allocation().height - 5, pixel_duration, 5)
                            cairo_context.fill()
                        else:
                            if round(start) in self.keyframes:
                                cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                            else:
                                cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                            cairo_context.rectangle(pixel_start, slider.get_allocation().height - 5, pixel_duration/10, 5)
                            cairo_context.fill()

                            if round(start + duration) in self.keyframes or round(start + duration) == self.frames:
                                cairo_context.set_source_rgb(0.0, 0.6, 0.0)  # green
                            else:
                                cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange

                            cairo_context.rectangle(pixel_start + pixel_duration/10*9, slider.get_allocation().height - 5, pixel_duration/10, 5)
                            cairo_context.fill()

                            cairo_context.set_source_rgb(1.0, 0.6, 0.0)  # orange
                            cairo_context.rectangle(pixel_start + pixel_duration/10, slider.get_allocation().height - 5, pixel_duration/10*8, 5)
                            cairo_context.fill()

            except AttributeError as ex:
                self.log.warning(f"Exeption: {ex}")
                pass

    def on_switch_tooltip_state_set(self, *args):
        active = self.builder.get_object('switch_tooltip').get_active()
        for widget_tt in self.widgets_tt_obj:
            widget_tt.props.has_tooltip = True if active else False

    def on_load_button_clicked(self, widget):
        self.log.debug("Function start")
        load_dialog = LoadCutDialog.new(self.app)
        load_dialog.set_transient_for(self)
        load_dialog.set_modal(True)
        load_dialog.setup(self.filename)
        response = load_dialog.run()
        load_dialog.destroy()
        if response == 1:
            self.cutlist = self.load_cutlist(load_dialog.result.local_filename)
            self.builder.get_object('cutsview').get_selection().unselect_all()
            if self.hide_cuts:
                self.update_timeline()

            self.slider.queue_draw()
            self.update_listview()


def new(gui):
    glade_filename = otrvpath.getdatapath('ui', 'CutinterfaceDialog.glade')
    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("cutinterface_dialog")
    dialog.gui = gui
    return dialog
