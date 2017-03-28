import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, GObject, Gst

GObject.threads_init()
import threading
Gst.init(None)




class KeySeekElement(Gst.Element):
    """ Seek to next or previous Keyframe by custom events """

    __gstdetails__ = (
        "KeySeekElement plugin",
        "KeySeekElement.py",
        "gst.Element, that implements seeks to next or previous Keyframe",
        "Jan Schole <jan581984@web.de>")

    _keyseeksrctemplate = Gst.PadTemplate.new(
        'keyseek-src',
        Gst.PadDirection.SRC,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any())

    _secondsrctemplate = Gst.PadTemplate.new(
        'secondary-src',
        Gst.PadDirection.SRC,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any())

    _keyseeksinktemplate = Gst.PadTemplate.new(
        'keyseek-sink',
        Gst.PadDirection.SINK,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any())

    _secondsinktemplate = Gst.PadTemplate.new(
        'secondary-sink',
        Gst.PadDirection.SINK,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any()
    )

    __gsttemplates__ = (
        _keyseeksrctemplate,
        _secondsrctemplate,
        _keyseeksinktemplate,
        _secondsinktemplate
    )

    def __init__(self, *args, **kwargs):
        # init parent
        Gst.Element.__init__(self)
        # gst.Element.__init__(self, *args, **kwargs)
        self.backward_seek = False
        self.forward_seek = False
        self.stepnanoseconds = 1
        self.step = 0
        self.update = False
        self.rate = 1.0
        self.format = Gst.Format.TIME
        self.start = 0
        self.stop = -1
        self.position = 0
        self.seg_position = 0
        self.qlock = threading.Lock()
        self.cond_add = threading.Condition(self.qlock)
        self.cond_del = threading.Condition(self.qlock)
        self.seeklock = threading.Lock()
        self.gui_wait = threading.Lock()
        self.stored_buf = None
        self.stored_event = None
        self.running = False
        self.item_waiting = False
        self.push_newsegment = False
        self.event_result = True
        self.restrict = False
        self.buf_result = Gst.FlowReturn.OK

        # create pads data handling functions
        self.keyseeksrcpad = Gst.Pad.new_from_template(self._keyseeksrctemplate, 'keyseek-src')
        self.keyseeksrcpad.set_event_function_full(self._handle_src_event)
        self.keyseeksrcpad.set_link_function_full(self._link_src)
        self.keyseeksrcpad.set_query_function_full(self._handle_query)
        self.add_pad(self.keyseeksrcpad)

        self.keyseeksinkpad = Gst.Pad.new_from_template(self._keyseeksinktemplate, 'keyseek-sink')
        self.keyseeksinkpad.set_chain_function_full(self._chain)
        self.keyseeksinkpad.set_event_function_full(self._handle_sink_event)
        self.add_pad(self.keyseeksinkpad)

        self.secondsrcpad = Gst.Pad.new_from_template(self._secondsrctemplate, 'secondary-src')
        self.secondsrcpad.set_event_function_full(self._handle_audio_event)
        self.secondsrcpad.set_query_function_full(self._handle_query)
        self.add_pad(self.secondsrcpad)

        self.secondsinkpad = Gst.Pad.new_from_template(self._secondsinktemplate, 'secondary-sink')
        self.secondsinkpad.set_event_function_full(self._handle_audio_event)
        self.secondsinkpad.set_chain_function_full(self._audio_chain)
        self.secondsinkpad.set_query_function_full(self._handle_query)
        self.add_pad(self.secondsinkpad)

        #self.keyseeksinkpad.set_getcaps_function(self._getcaps)
        #self.keyseeksinkpad.set_setcaps_function(self._setcaps)
        #self.keyseeksinkpad.set_activatepush_function(self._sink_activate_push)


        #self.keyseeksrcpad.set_activatepush_function(self._src_activate_push)
        #self.keyseeksrcpad.set_getcaps_function(self._getcaps)

        #self.secondsinkpad.set_getcaps_function(self._getcaps)
        #self.secondsinkpad.set_setcaps_function(self._setcaps)

        #self.secondsrcpad.set_getcaps_function(self._getcaps)


    # common functions for audio and video
    def _get_otherpad(self, pad):
        if pad == self.keyseeksinkpad:
            otherpad = self.keyseeksrcpad
        elif pad == self.keyseeksrcpad:
            otherpad = self.keyseeksinkpad
        elif pad == self.secondsinkpad:
            otherpad = self.secondsrcpad
        else:
            otherpad = self.secondsinkpad
        return otherpad

    def _getcaps(self, pad):
        otherpad = self._get_otherpad(pad)

        res = otherpad.peer_get_caps()
        if res == None:
            res = Gst.Caps.new_any()
        return res

    def _setcaps(self, pad, caps):
        return True

    def _handle_query(self, pad, parent, query):
        otherpad = self._get_otherpad(pad)
        return otherpad.peer_query(query)

    # functions for audio pads
    def _handle_audio_event(self, pad, event):
        # print "Pushing audio event %s" % event.type.value_name
        if event.type != Gst.EventType.EOS:
            otherpad = self._get_otherpad(pad)
            return otherpad.push_event(event)
        else:
            return True

    def _audio_chain(self, pad, buf):
        return self.secondsrcpad.push(buf)

    # functions for video pads
    def _link_src(self, pad, peer):
        self.qlock.acquire()
        if self.running:
            pad.start_task(self._loop, None)
        self.qlock.release()
        return Gst.PadLinkReturn.OK

    def _seek_step(self, step):
        self.seeklock.acquire()
        new_pos = self.position + step * self.stepnanoseconds
        restrict = False
        duration = self.keyseeksinkpad.query_peer_duration(Gst.Format.TIME, None)[0]
        if new_pos < 0:
            print("Restrict!")
            new_pos = 0
            self.restrict = True
        elif new_pos >= duration:
            print("Restrict!")
            new_pos = duration - 1
            self.restrict = True
        seek_event = Gst.Event.new_seek(self.rate, self.format, Gst.SeekFlags.KEY_UNIT | Gst.SeekFlags.FLUSH,
                                        Gst.SeekType.SET, new_pos, Gst.SeekType.NONE, 0)
        # print "Doing keyseek to time %i" % (new_pos)
        res = self.keyseeksinkpad.push_event(seek_event)
        if not res:
            print("Seek for keyframe failed")
            self.backward_seek = False
            self.forward_seek = False
            self.step = 0
            self.gui_wait.release()
        else:
            # print "Step %i succeeded" % step
            self.step = step
        self.seeklock.release()

    # print "Exiting _seek_step"

    def _store_event(self, event):
        res = True
        # print "Storing event %s" % event.type.value_name
        self.qlock.acquire()
        while self.running and self.item_waiting:
            self.cond_add.wait()
        if self.running:
            self.stored_event = event
            self.cond_del.notify()
            self.item_waiting = True
            if event.type == Gst.EventType.EOS:
                res = True
            else:
                while self.item_waiting:
                    self.cond_add.wait()
                res = self.event_result
        self.qlock.release()
        return res

    def _store_buf(self, buf):
        res = Gst.FlowReturn.OK
        self.qlock.acquire()
        while self.running and self.item_waiting:
            self.cond_add.wait()
        if self.running:
            self.stored_buf = buf
            self.cond_del.notify()
            self.item_waiting = True
            while self.item_waiting:
                self.cond_add.wait()
            res = self.buf_result
        self.qlock.release()
        return res

    def _handle_item(self):
        self.qlock.acquire()
        while self.running and not self.item_waiting:
            self.cond_del.wait()
        if self.running:
            if self.stored_buf != None:
                # print "Got Buffer with timestamp %i and forward_seek %r and backward_seek %r at position %i and segment position %i" % (self.stored_buf.timestamp,self.forward_seek,self.backward_seek,self.position, self.seg_position)
                if self.restrict or (self.forward_seek and (self.stored_buf.timestamp > self.position)) or (
                            self.backward_seek and (self.stored_buf.timestamp < self.position)):
                    self.position = self.stored_buf.timestamp
                    self.forward_seek = False
                    self.backward_seek = False
                    self.step = 0
                    self.restrict = False
                    seek_event = Gst.Event.new_seek(self.rate, self.format,
                                                    Gst.SeekFlags.CCURATE | Gst.SeekFlags.FLUSH, Gst.SeekType.SET,
                                                    self.position, Gst.SeekType.NONE, 0)
                    res = self.secondsinkpad.push_event(seek_event)
                    if not res:
                        print("Secondary-seek failed")
                    self._push_segment()
                    self.gui_wait.release()
                    self.buf_result = self.keyseeksrcpad.push(self.stored_buf)
                    self.item_waiting = False
                    self.stored_buf = None
                    self.cond_add.notify()
                    self.qlock.release()
                elif self.forward_seek:
                    self.buf_result = Gst.FlowReturn.OK
                    self.item_waiting = False
                    self.stored_buf = None
                    self.cond_add.notify()
                    self.qlock.release()
                    self._seek_step(self.step + 1)
                elif self.backward_seek:
                    self.buf_result = Gst.FlowReturn.OK
                    self.item_waiting = False
                    self.stored_buf = None
                    self.cond_add.notify()
                    self.qlock.release()
                    self._seek_step(self.step - 1)
                else:
                    self.position = self.stored_buf.timestamp
                    # print "Pushing buffer with pts %i" % self.stored_buf.timestamp
                    self.buf_result = self.keyseeksrcpad.push(self.stored_buf)
                    # print "Result: %r" % self.buf_result
                    self.item_waiting = False
                    self.stored_buf = None
                    self.cond_add.notify()
                    self.qlock.release()
            else:
                if self.stored_event.type == Gst.EventType.SEGMENT:
                    self.update, self.rate, self.format, self.start, self.stop, self.seg_position = self.stored_event.parse_new_segment()
                    # print "Received Segment with update=%r, rate=%r, format=%i, start=%i, stop=%i, position=%i" % (self.update,self.rate,self.format,self.start,self.stop,self.seg_position)
                    if (not self.forward_seek) and (not self.backward_seek):
                        # print "Forwarding segment"
                        self.event_result = self.keyseeksrcpad.push_event(self.stored_event)
                    else:
                        self.event_result = True
                elif self.stored_event.type == Gst.EventType.EOS:
                    # print "Forwarding EOS"
                    self.event_result = self.keyseeksrcpad.push_event(self.stored_event)
                    self.running = False
                    self.cond_add.notify_all()
                    self.cond_del.notify_all()
                    self.keyseeksrcpad.pause_task()

                else:
                    # print "Forwarding event %r" % self.stored_event.type
                    self.event_result = self.keyseeksrcpad.push_event(self.stored_event)
                self.stored_event = None
                self.item_waiting = False
                self.cond_add.notify()
                self.qlock.release()
        else:
            self.qlock.release()

    def _push_segment(self):
        # print "Pushing Segment with update=%r, rate=%r, format=%i, start=%i, stop=%i, position=%i" % (self.update,self.rate,self.format,self.start,self.stop,self.seg_position)
        new_segment_event = Gst.Event.new_new_segment(False, self.rate, self.format, self.start, self.stop,
                                                      self.seg_position)
        self.keyseeksrcpad.push_event(new_segment_event)

    def _chain(self, pad, parent, buf):
        # print "Received buffer with pts %i" % buf.timestamp
        return self._store_buf(buf)

    def _is_running(self):
        self.qlock.acquire()
        res = self.running
        self.qlock.release()
        return res

    def _loop(self, data):
        while self._is_running():
            self._handle_item()

    def _locked_flush(self):
        self.stored_buf = None
        self.stored_event = None
        self.item_waiting = False
        self.update = False
        self.rate = 1.0
        self.format = Gst.Format.TIME
        self.start = 0
        self.stop = -1
        self.seg_position = 0
        self.event_result = True
        self.buf_result = Gst.FlowReturn.OK

    def _handle_sink_event(self, pad, parent, event):
        # print "Received sink event %r" % event.type
        if event.type == Gst.EventType.FLUSH_START:
            res = self.keyseeksrcpad.push_event(event)
            self.qlock.acquire()
            self.running = False
            self.item_waiting = False
            self.cond_add.notify_all()
            self.cond_del.notify_all()
            self.qlock.release()
            self.keyseeksrcpad.pause_task()
            return res
        elif event.type == Gst.EventType.FLUSH_STOP:
            res = self.keyseeksrcpad.push_event(event)
            self.qlock.acquire()
            self.running = True
            self._locked_flush()
            if self.keyseeksrcpad.is_linked:
                self.keyseeksrcpad.start_task(self._loop, None)
            self.qlock.release()
            return res
        else:
            return self._store_event(event)

    def _handle_src_event(self, pad, event):
        # print "Received src event %r" % event.type
        self.gui_wait.acquire()
        if event.type == Gst.EventType.CUSTOM_UPSTREAM:
            # print event.get_structure().get_name()
            if event.get_structure().get_name() == 'forward':
                self.forward_seek = True
                self.backward_seek = False
                self._seek_step(0)
            else:
                self.forward_seek = False
                self.backward_seek = True
                self._seek_step(0)
            return True
        else:
            self.gui_wait.release()
            return self.keyseeksinkpad.push_event(event)

    def _sink_activate_push(self, pad, active):
        if active:
            self.qlock.acquire()
            self.running = True
            self.qlock.release()
        else:
            self.qlock.acquire()
            self.running = False
            self._locked_flush()
            self.cond_add.notify_all()
            self.cond_del.notify_all()
            self.gui_wait.acquire(False)
            self.gui_wait.release()
            self.qlock.release()
        return True

    def _src_activate_push(self, pad, active):
        res = True
        if active:
            self.qlock.acquire()
            self.running = True
            if self.keyseeksrcpad.is_linked():
                res = self.keyseeksrcpad.start_task(self._loop, None)
            self.qlock.release()
        else:
            self.qlock.acquire()
            self.running = False
            self.cond_add.notify_all()
            self.cond_del.notify_all()
            self.gui_wait.acquire(False)
            self.gui_wait.release()
            self.qlock.release()
            res = self.keyseeksrcpad.stop_task()
        return res


GObject.type_register(KeySeekElement)