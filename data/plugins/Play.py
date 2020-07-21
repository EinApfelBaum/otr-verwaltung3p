# -*- coding: utf-8 -*-
# BEGIN LICENSE
# Copyright (C) 2010 Benjamin Elbers <elbersb@gmail.com>
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
# with this program.  If not, see <http://www.gnu.org/licenses/>.
# END LICENSE

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import Gtk

from otrverwaltung3p.pluginsystem import Plugin
from otrverwaltung3p.constants import Section


class Play(Plugin):
    Name = "Abspielen"
    Desc = "Spielt Video-Dateien ab."
    Author = "Benjamin Elbers"
    Configurable = False

    def enable(self):
        self.relevant_sections = [
            Section.VIDEO_UNCUT,
            Section.VIDEO_CUT,
            Section.ARCHIVE,
        ]

        if self.app.config.get("general", "use_internal_icons"):
            image = Gtk.Image.new_from_file(self.get_path("play.png"))
        else:
            image = Gtk.Image.new_from_pixbuf(
                Gtk.IconTheme.get_default().load_icon(
                    "media-playback-start", self.app.config.get("general", "icon_size"), 0,
                )
            )

        self.toolbutton = self.gui.main_window.add_toolbutton(image, "Abspielen", self.relevant_sections)
        self.toolbutton.connect("clicked", self.on_play_clicked)

        # self.row_activate_id = self.gui.main_window.builder.get_object('treeview_files').connect(
        #     'row-activated', self.on_row_activated)

    def disable(self):
        self.gui.main_window.remove_toolbutton(self.toolbutton)
        # self.gui.main_window.builder.get_object('treeview_files').disconnect(self.row_activate_id)

    # plugin methods
    def start_player(self):
        try:
            filename = self.gui.main_window.get_selected_filenames()[0]
            self.app.play_file(filename)
        except IndexError:
            pass

    # signal methods
    def on_play_clicked(self, widget, data=None):
        self.start_player()

    # def on_row_activated(self, treeview, path, view_column):
    #     if self.app.section in self.relevant_sections:
    #         self.start_player()
