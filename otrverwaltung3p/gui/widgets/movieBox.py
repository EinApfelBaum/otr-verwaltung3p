import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject

Gst.init(None)
Gst.init_check(None)


class MovieBox(Gtk.Box):
    __gtype_name__ = "MovieBox"

    def __init__(self):
        super().__init__()

        self.gtksink = Gst.ElementFactory.make('gtksink')
        self.movie_widget = self.gtksink.props.widget
        self.pack_start(self.movie_widget, True, True, 0)

        self.player = Gst.ElementFactory.make('playbin')
        self.player.set_property('video-sink', self.gtksink)
        self.player.set_property('force-aspect-ratio', True)

        self.movie_widget.show()
