# -*- coding: utf-8 -*-
# BEGIN LICENSE
# This file is in the public domain
# END LICENSE

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
gi.require_version('GdkX11', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gtk, Gdk, GObject, Gst, GstPbutils, GdkX11, GstVideo
import pathlib
import logging

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

Gdk.threads_init()
Gst.init(None)

import os
import time
#from otrverwaltung.elements import KeySeekElement
#from otrverwaltung.elements import DecoderWrapper
from otrverwaltung import path
from otrverwaltung import cutlists
from otrverwaltung.gui import LoadCutDialog
from otrverwaltung.actions.cut import Cut


class CutinterfaceDialog(Gtk.Dialog, Gtk.Buildable, Cut):
    __gtype_name__ = "CutinterfaceDialog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(self.__class__.__name__)
        self.marker_a, self.marker_b = 0, -1
        self.timelines = [ [] ]
        self.cut_selected = -1
        self.timer = None
        self.hide_cuts = False
        self.frames = 0
        self.slider = None
        self.keyframes = None
        self.getVideoLength = True
        self.xid = 0
        self.buttonClose = False
        self.buttonOk = False

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)
        self.slider = self.builder.get_object('slider')
        self.slider.set_digits(0)
        # TODO: make it an option
        #self.slider.set_draw_value(True)

        self.movie_window = self.builder.get_object('movie_window')
        self.movie_window.connect('realize', self.on_realize)
        self.movie_window.connect('unrealize', self.on_unrealize)


        self.hide_cuts = self.builder.get_object('checkbutton_hide_cuts').get_active()

        cutslistmodel = self.builder.get_object('cutslist')
        #cutslistmodel.set_default_sort_func(None)
        cutslistselection = self.builder.get_object('cutsview').get_selection()
        cutslistselection.connect('changed', self.on_cuts_selection_changed)

        button_delete_cut = self.builder.get_object('button_delete_cut')
        button_delete_cut.set_sensitive(False)
        button_deselect = self.builder.get_object('button_deselect')
        button_deselect.set_sensitive(False)

        #player state
        self.is_playing = False

    def on_realize(self, widget, data=None):
        self.log.info("function start")

        window = widget.get_window()
        self.xid = window.get_xid()
        #window = widget.get_window()
        #window_handle = widget.get_xid()

        # xid must be retrieved first in GUI-thread and before creating player to prevent racing conditions
        # You need to get the XID after window.show_all().  You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.
        #self.xid = self.movie_window.get_property('window').get_xid()

        # pass it to playbin, which implements XOverlay and will forward
        # it to the video sink
        #self.playbin.set_window_handle(self.xid)
        #self.playbin.set_xwindow_id(window_handle)

        #self.player.set_state(Gst.State.PLAYING)
        #self.player.set_state(Gst.State.PAUSED)

        self.ready_callback()

    def on_unrealize(self,widget,data=None):
        # to prevent racing conditions when closing the window while playing
        self.player.set_state(Gst.State.NULL)

    def get_cuts_in_frames(self, cuts, in_frames):
        if cuts == []:
            res = [(0, self.frames)]
            self.log.info("Framelist: {0}".format(self.frames))
        elif in_frames:
            res = cuts
        else:
            res = []
            for start, duration in cuts:
                start_frame = int(start * self.framerate_num / self.framerate_denom)
                duration_frames = int(duration * self.framerate_num / self.framerate_denom)
                self.log.info("Startframe = {0}".format(start_frame))
                self.log.info("Duration = {0}".format(duration_frames))
                res.append((start_frame,duration_frames))
        return res

    def load_cutlist(self, filename):
        cutlist = cutlists.Cutlist()
        cutlist.intended_app = 'VirtualDub.exe'
        if filename != None and os.path.exists(filename):
            cutlist.local_filename = filename
            cutlist.read_from_file()
            cutlist.read_cuts()
            if cutlist.author != self.app.config.get('general', 'cutlist_username'):
                cutlist.usercomment = 'OTRV3p; Vorlage von ' + cutlist.author + '; ' + cutlist.usercomment
            if cutlist.cuts_frames:
                self.initial_cutlist = cutlist.cuts_frames
                self.initial_cutlist_in_frames = True
            else:
                self.initial_cutlist = cutlist.cuts_seconds
                self.initial_cutlist_in_frames = False

        else:
            cutlist.usercomment = 'OTRV3p'
            self.initial_cutlist = []
            self.initial_cutlist_in_frames = True

        if self.timer != None:      # Running
            self.timelines.append(self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames))

        if self.slider:
            self.slider.queue_draw()
        return cutlist

    def set_cuts(self, cutlist, cuts):
        cutlist.fps = float(self.framerate_num) / float(self.framerate_denom)
        cutlist.cuts_frames = cuts
        cutlist.cuts_seconds = []
        cutlist.app = 'OTR-Verwaltung3p;Cutinterface'
        for start, duration in cuts:
            s = start * self.framerate_denom / float(self.framerate_num)
            d = duration * self.framerate_denom / float(self.framerate_num)
            cutlist.cuts_seconds.append((s,d))

    def _run(self, filename, cutlist, app):
        self.app = app
        self.config = app.config
        self.filename = filename
        self.cutlist = self.load_cutlist(cutlist)

        self.keyframes, error = self.get_keyframes_from_file(filename)
        if self.keyframes == None:
            self.log.warning("Error: Keyframes konnten nicht ausgelesen werden.")

        self.movie_window.set_size_request(self.config.get('general', 'cutinterface_resolution_x'), self.config.get('general', 'cutinterface_resolution_y'))
        self.hide_cuts = self.config.get('general', 'cutinterface_hide_cuts')

        # before we get info, we need to create the player
        self.create_Player()

        # get video info
        self.discover = GstPbutils.Discoverer.new(Gst.SECOND)
        #tempfilename = pathlib.Path(filename).as_uri()
        self.d = self.discover.discover_uri('file://{}'.format(pathlib.Path(filename)))
        for vinfo in self.d.get_video_streams():
            self.framerate_num = vinfo.get_framerate_num()
            self.framerate_denom = vinfo.get_framerate_denom()
            self.videowidth = vinfo.get_width()
            self.videoheight = vinfo.get_height()

        self.videolength = self.d.get_duration()
        self.frames = self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND
        self.timelines = [self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames)]
        self.ready_callback()

        if Gtk.ResponseType.OK == self.run():
            self.set_cuts(self.cutlist, self.timelines[-1])
        else:
            self.set_cuts(self.cutlist, [])

        if self.timer != None:
            GObject.source_remove(self.timer)

        return self.cutlist

    def create_Player(self):
        # The player
        self.player = Gst.Pipeline.new()

        # Create bus and connect several handlers
        # Create bus to get events from GStreamer player
        bus = self.player.get_bus()
        bus.add_signal_watch()

        bus.connect('message::eos', self.on_eos)
        bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)
        bus.connect("message", self.on_message)

        # Create GStreamer elements
        self.playbin = Gst.ElementFactory.make('playbin', None)

        # Add playbin to the player
        self.player.add(self.playbin)

        # Set properties
        fileUri = 'file://' + self.filename
        self.playbin.set_property('uri', fileUri)

        self.player.set_state(Gst.State.PLAYING)
        self.player.set_state(Gst.State.PAUSED)

    def ready_callback(self):
        self.builder.get_object('label_filename').set_markup("Aktuelle Datei: <b>%s</b>" % os.path.basename(self.filename))

        self.update_timeline()
        self.update_listview()

        self.timer = GObject.timeout_add(200, self.tick)

    def tick(self):
        self.update_frames_and_time()
        self.update_slider()
        self.builder.get_object('checkbutton_hide_cuts').set_active(self.hide_cuts)
        return True

    def jump_to(self, frames=None, seconds=None, nanoseconds=0, flags=Gst.SeekFlags.ACCURATE):
        if frames:
            if frames >= self.get_frames():
                frames = self.get_frames()-1

            nanoseconds = frames * Gst.SECOND * self.framerate_denom / self.framerate_num
        elif seconds:
            nanoseconds = seconds * Gst.SECOND

        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | flags, int(nanoseconds))

    def set_marker(self, a=None, b=None):
        """ Set markers a and/or b to a specific frame posititon and update the buttons """

        if a is not None:
            self.marker_a = a
            
            if a != -1 and self.marker_b < 0:
                    self.marker_b = self.get_frames()-1
    
        if b is not None:
            self.marker_b = b
            
            if b != -1 and self.marker_a < 0:
                    self.marker_a = 0
        
        if self.marker_a != -1 and self.marker_b != -1 and self.marker_a > self.marker_b:
            self.log.info("Switch a and b")
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

        self.player.set_state(Gst.State.PLAYING)
        self.player.set_state(Gst.State.PAUSED)

    # get absolute frame, assuming that the given frame corresponds to the current display modus
    def get_absolute_position(self, rel_pos):
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

    # convert the absolute position into the corresponding relative position
    def get_relative_position(self, abs_pos):
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

    # inverts the cuts (between timeline and cut-out list) assuming the list is flawless
    # and should be faster than the full version below
    def invert_simple(self, cuts):
        inverted = []
        if cuts[0][0] > 0:
            inverted.append( (0, cuts[0][0]) )

        next_start = cuts[0][0] + cuts[0][1]
        for start, duration in cuts[1:]:
            inverted.append( (next_start, start - next_start) )
            next_start = start + duration

        if next_start < self.frames:
            inverted.append( (next_start, self.frames - next_start) )

        return inverted

    # inverts the cuts (between timeline and cut-out list) removing all kinds of overlaps etc.
    def invert_full(self, cuts):
        inverted = []

        sorted_cuts = sorted(cuts, key=lambda c:c[0]) # sort cuts after start frame
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

        return inverted

    def remove_segment(self, rel_s, rel_d):
        self.log.info("\n\033[1;31m-- Entering remove_segment\033[1;m")
        self.log.info("Current timeline is: {0}".format(self.timelines[-1]))

        abs_start = self.get_absolute_position(rel_s)
        abs_end = self.get_absolute_position(rel_s + rel_d - 1)

        inverted_timeline = self.invert_simple(self.timelines[-1])
        inverted_timeline.append((abs_start, abs_end - abs_start + 1))
        self.timelines.append(self.invert_full(inverted_timeline))

        self.log.info("Current timeline is: {0}".format(self.timelines[-1]))
        self.log.info("\033[1;31m-- Leaving remove_segment\033[1;m\n")

        self.update_timeline()
        self.update_listview()

        time.sleep(0.2)
        if self.hide_cuts:
            self.log.info("Seek To: {0}".format(rel_s))
            self.jump_to(frames=rel_s)
        else:
            self.log.info("Seek To: {0}".format(abs_end + 1))
            self.jump_to(frames=abs_end+1)

    def get_frames(self):
        """ Returns the current number of frames to be shown. """
        if self.hide_cuts:
            frames = sum([duration for start, duration in self.timelines[-1]])
        else:
            frames = self.frames

        return frames

    def update_frames_and_time(self):
        #Versuch, Informationen zu erhalten und zu updaten
        try:
            current_position = self.player.query_position(Gst.Format.TIME)[1]
            duration = self.player.query_duration(Gst.Format.TIME)[1]
        except Exception as e:    #manchmal geht es nicht, bspw. wenn gerade erst geseekt wurde
            self.log.warning("except!", e)
            return

        self.current_frame_position = current_position * self.framerate_num / self.framerate_denom / Gst.SECOND

        if self.keyframes != None and self.current_frame_position in self.keyframes :
            self.builder.get_object('label_time').set_text('Frame(K): %i/%i, Zeit %s/%s' % (self.current_frame_position, self.get_frames() - 1, self.convert_sec(current_position), self.convert_sec(duration)))
        else:
            self.builder.get_object('label_time').set_text('Frame: %i/%i, Zeit %s/%s' % (self.current_frame_position, self.get_frames() - 1, self.convert_sec(current_position), self.convert_sec(duration)))

    def update_slider(self):
        try:
            nanosecs = self.player.query_position(Gst.Format.TIME)[1]

            # block seek handler so we don't seek when we set_value()
            self.builder.get_object('slider').handler_block_by_func(self.on_slider_value_changed)

            frames = nanosecs * self.framerate_num / self.framerate_denom / Gst.SECOND
            self.builder.get_object('slider').set_value(frames)

            self.builder.get_object('slider').handler_unblock_by_func(self.on_slider_value_changed)

        # TODO check port 2.7 to 3.0
        # catch Gst.QueryError
        except TypeError as typeError:
           pass

    def update_listview(self):
        global path
        listview = self.builder.get_object('cutsview')
        listselection = listview.get_selection()
        listmodel, listiter = listselection.get_selected()
        if listiter:
            path = listmodel.get_path(listiter)
        listview.set_model(None)                # for speeding up the update of the view
        listmodel.clear()

        if not self.getVideoLength:
            inverted = self.invert_simple(self.timelines[-1])
            # print inverted
            for start, duration in inverted:
                listmodel.append((start, start + duration - 1))

        listview.set_model(listmodel)
        if listiter:
            listselection.select_path(path)

    def is_remove_modus(self):
        return self.cut_selected < 0 or self.hide_cuts

    def update_remove_button(self):
        if self.is_remove_modus():
            self.builder.get_object('button_remove').set_label('Bereich entfernen')
        else:
            self.builder.get_object('button_remove').set_label('Veränderung übernehmen')

    def convert_sec(self, time):
        s, rest = divmod(time, Gst.SECOND)

        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)

        time_str = "%02i:%02i:%02i.%03i" % (h, m, s, rest*1000/Gst.SECOND)

        return time_str

    def on_eos(self, bus, msg):
        self.player.set_state(Gst.State.NULL)
        self.builder.get_object('label_time').set_text('Frame: 0/0, Zeit 0s/0s')

    def on_error(self, bus, msg):
        err, debug = msg.parse_error()
        self.log.error("Error: %s" % err, debug)
        self.player.set_state(Gst.State.NULL)
        self.builder.get_object('label_time').set_text('Frame: 0/0, Zeit 0s/0s')

    def on_sync_message(self, bus, message):
        #if message.structure is None:
        #    return

        #if message.structure.get_name() == "prepare-xwindow-id":
        #    imagesink = message.src
        #    imagesink.set_property("force-aspect-ratio", True)
        #    imagesink.set_xwindow_id(self.movie_xid)

        if message.get_structure().get_name() == 'prepare-window-handle':
            self.log.info('prepare-window-handle')
            message.src.set_window_handle(self.xid)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ASYNC_DONE:
            if self.getVideoLength:
                self.getVideoLength = not self.getVideoLength
                self.log.info('Async done')
                self.videolength = self.playbin.query_duration(Gst.Format.TIME)
                self.frames = self.videolength[1] * self.framerate_num / self.framerate_denom / Gst.SECOND
                self.slider.set_range(0, self.get_frames())
                self.timelines = [self.get_cuts_in_frames(self.initial_cutlist, self.initial_cutlist_in_frames)]
                self.builder.get_object('slider').set_range(0, self.get_frames())
                self.slider.queue_draw()
                self.log.info("Timelines: {0}".format(self.timelines))
                self.log.info("framerate_num: {0}".format(self.framerate_num))
                self.log.info("framerate_denom: {0}".format(self.framerate_denom))
                self.log.info("videolength: {0}".format(self.videolength))
                self.log.info("frames: {0}".format(self.frames))

    # signals #

    def on_window_key_press_event(self, widget, event, *args):
        """handle keyboard events"""
        keyname = Gdk.keyval_name(event.keyval).upper()
        if event.type == Gdk.EventType.KEY_PRESS:
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
                if self.is_playing:
                    self.on_button_pause_clicked(None)
                else:
                    self.on_button_play_clicked(None)
                return True
            else:
                self.log.info("keyname: {0}".format(keyname))

        return False

    def on_window_key_release_event(self, widget, event, *args):
        """handle keyboard events"""
        keyname = Gdk.keyval_name(event.keyval).upper()
        if event.type == Gdk.EventType.KEY_RELEASE:
            if keyname == 'LEFT':
                self.on_button_back_clicked(None)
                return True
            elif keyname == 'RIGHT':
                self.on_button_forward_clicked(None)
                return True

    def on_slider_key_press_event(self, widget, event):
        # override normal keybindings for slider (HOME and END are used for markers)
        keyname = Gdk.keyval_name(event.keyval).upper()
        if keyname == 'HOME' or keyname=='END':
            return True

    def on_slider_value_changed(self, slider):
        frames = slider.get_value()
        self.log.info("Slider value = {0}".format(frames))
        if frames >= self.get_frames():
            self.log.info("restrict")
            frames = self.get_frames() - 1
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, frames * Gst.SECOND * self.framerate_denom / self.framerate_num)
        if not self.is_playing:
            self.log.info("update by slider change")
            self.update_frames_and_time()

    def on_button_play_clicked(self, button, data=None):
        self.is_playing = True
        self.player.set_state(Gst.State.PLAYING)

    def on_button_pause_clicked(self, button, data=None):
        self.is_playing = False
        self.player.set_state(Gst.State.PAUSED)
        self.update_frames_and_time()

    def jump_relative(self, frames, flags = Gst.SeekFlags.ACCURATE):
        try:
            nano_seconds = self.player.query_position(Gst.Format.TIME)[1]
        except Exception as e:
            time.sleep(0.04)
            nano_seconds = self.player.query_position(Gst.Format.TIME)[1]

        self.videolength = self.player.query_duration(Gst.Format.TIME)[1]
        self.frames = self.videolength * self.framerate_num / self.framerate_denom / Gst.SECOND

        nano_seconds += frames * (1 * Gst.SECOND * self.framerate_denom / self.framerate_num)
        if nano_seconds < 0:
            self.log.info("restrict")
            nano_seconds = 0
        elif nano_seconds * self.framerate_num / self.framerate_denom / Gst.SECOND >= self.get_frames():
            self.log.info("restrict")
            nano_seconds = (self.get_frames() - 1) * Gst.SECOND * self.framerate_denom / self.framerate_num

        self.jump_to(nanoseconds=nano_seconds, flags=flags)

    def jump_key(self, direction):
        # gcurse

        if direction == "backward":
            jumpto = self.get_keyframe_in_front_of_frame(self.keyframes, frame)
        else:
            jumpto = self.get_keyframe_after_frame(self.keyframes, frame)

        self.log.info("jumpto = {0}".format(jumpto))
        self.jump_to(frames=jumpto, flags=flags)

    def on_button_keyfast_back_clicked(self, widget, data=None):
        #self.jump_key('backward')
        # gcurse
        self.jump_to(frames=self.current_frame_position - 1,
                    flags=Gst.SeekFlags.KEY_UNIT | Gst.SeekFlags.SNAP_BEFORE)

    def on_button_ffast_back_clicked(self, widget, data=None):
        self.jump_relative(-100)

    def on_button_fast_back_clicked(self, widget, data=None):
        self.jump_relative(-10)

    def on_button_back_clicked(self, widget, data=None):
        self.jump_relative(-1)

    def on_button_forward_clicked(self, widget, data=None):
        self.jump_relative(1)

    def on_button_fast_forward_clicked(self, widget, data=None):
        self.jump_relative(10)

    def on_button_ffast_forward_clicked(self, widget, data=None):
        self.jump_relative(100)

    def on_button_keyfast_forward_clicked(self, widget, data=None):
        #self.jump_key('forward')
        # gcurse
        self.jump_to(frames=self.current_frame_position + 1,
                    flags=Gst.SeekFlags.KEY_UNIT | Gst.SeekFlags.SNAP_AFTER)

    def on_button_a_clicked(self, *args):
        # TODO: warn if Marker A = B or distance between them to low
        self.log.info('marker a = {0}'.format(self.current_frame_position))
        self.set_marker(a=self.current_frame_position)
        self.slider.queue_draw()

    def on_button_b_clicked(self, *args):
        # TODO: warn if Marker A = B or distance between them to low
        self.log.info('marker b = {0}'.format(self.current_frame_position))
        self.set_marker(b=self.current_frame_position)
        self.slider.queue_draw()

    def on_button_remove_clicked(self, widget):
        self.log.info("marker a = ".format(self.marker_a))
        self.log.info("marker b = ".format(self.marker_b))
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
        self.is_playing = False
        self.player.set_state(Gst.State.PAUSED)
        self.update_frames_and_time()
        marker_a = self.get_absolute_position(self.marker_a)
        marker_b = self.get_absolute_position(self.marker_b)
        pos = self.get_absolute_position(self.current_frame_position)
        self.log.info("Absolute position: ".format(pos))

        self.hide_cuts = widget.get_active()
        self.config.set('general', 'cutinterface_hide_cuts',self.hide_cuts)
        self.update_timeline()
        if self.hide_cuts:
            self.set_marker(self.get_relative_position(marker_a),self.get_relative_position(marker_b))
        else:
            self.builder.get_object('cutsview').get_selection().unselect_all()
            self.set_marker(marker_a,marker_b)

        self.update_remove_button()
        self.slider.queue_draw()

        # print "Relative position: ", self.get_relative_position(pos)
        time.sleep(0.2)
        if self.hide_cuts:
            self.jump_to(frames=self.get_relative_position(pos))
        else:
            self.jump_to(frames=pos)

    def on_cuts_selection_changed(self, treeselection):
        cutslist, cutsiter = treeselection.get_selected()
        button_delete_cut = self.builder.get_object('button_delete_cut')
        button_deselect = self.builder.get_object('button_deselect')

        if cutsiter:
            self.cut_selected = cutslist.get_path(cutsiter)[0]
            self.log.info("Selected cut = {0}".format(self.cut_selected))
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
        global marker_a, marker_b, pos, playing
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
        self.builder.get_object('cutsview').get_selection().unselect_all()
        self.slider.clear_marks()
        self.marker_a = -1
        self.marker_b = -1

    def on_button_cut_clicked(self, widget, data=None):
        self.buttonOk = True
        self.set_cuts(self.cutlist, self.timelines[-1])
        if self.timer != None:
            GObject.source_remove(self.timer)
        self.close()

    def on_button_cancel_clicked(self, widget, data=None):
        self.buttonClose = True
        self.set_cuts(self.cutlist, [])
        if self.timer != None:
            GObject.source_remove(self.timer)
        self.callback(self.cutlist)
        self.close()

    def on_slider_draw_event(self, widget, cr):
        self.redraw(cr)

    def redraw(self, cr):
        slider = self.builder.get_object('slider')

        border = 11
        if self.get_frames() != 0:
            # draw line from marker a to marker b and for all cuts
            try:
                one_frame_in_pixels = (slider.get_allocation().width - 2*border) / float(self.get_frames())
                # draw only if ...
                if self.marker_a != self.marker_b and self.marker_a >= 0 and self.marker_b >= 0:
                    self.log.debug("Slider allocation size: {0} x {1}".format(slider.get_allocation().width, slider.get_allocation().height))
                    self.log.debug("one_frame_in_pixels: {0}".format(one_frame_in_pixels))
                    marker_a = border + int(round(self.marker_a * one_frame_in_pixels))
                    marker_b = border + int(round(self.marker_b * one_frame_in_pixels))

                    cr.set_source_rgb(1.0,0.0,0.0)  # red
                    cr.rectangle(marker_a, 0, marker_b - marker_a, 5)
                    cr.fill()

                if not self.hide_cuts:
                    inverted = self.invert_simple(self.timelines[-1])
                    for start, duration in inverted:
                        pixel_start = border + int(round(start * one_frame_in_pixels))
                        pixel_duration = int(round(duration * one_frame_in_pixels))
                        
                        # draw keyframe cuts that don't need reencoding with a different color
                        if ((start + duration) in self.keyframes) or (start + duration == self.frames):
                            cr.set_source_rgb(0.0,0.6,0.0)  # green
                        else:
                            cr.set_source_rgb(1.0,0.6,0.0)  # orange

                        cr.rectangle(pixel_start, slider.get_allocation().height - 5, pixel_duration, 5)
                        cr.fill()

                # slider.queue_draw()
            except AttributeError as ex:
                self.log.warning("Exeption: {0}".format(ex))
                pass

    def on_load_button_clicked(self, widget):
        load_dialog = LoadCutDialog.NewLoadCutDialog(self.app, self.app.gui)
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

def NewCutinterfaceDialog():
    glade_filename = path.getdatapath('ui', 'CutinterfaceDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("cutinterface_dialog")
    return dialog

