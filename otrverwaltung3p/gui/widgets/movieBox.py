# BEGIN LICENSE
# Copyright (C) 2020 Dirk Lorenzen <gcurse@web.de>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.
# END LICENSE

from gi import require_version

require_version("Gtk", "3.0")
require_version("Gst", "1.0")
from gi.repository import Gst, Gtk

Gst.init(None)
Gst.init_check(None)


class MovieBox(Gtk.Box):
    __gtype_name__ = "MovieBox"

    def __init__(self):
        super().__init__()

        self.gtksink = Gst.ElementFactory.make("gtksink")
        self.movie_widget = self.gtksink.props.widget
        self.pack_start(self.movie_widget, True, True, 0)

        self.player = Gst.ElementFactory.make("playbin")
        self.player.set_property("video-sink", self.gtksink)
        self.player.set_property("force-aspect-ratio", True)

        self.movie_widget.show()
