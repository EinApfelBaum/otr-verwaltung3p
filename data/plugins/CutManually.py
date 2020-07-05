# -*- coding: utf-8 -*-
# BEGIN LICENSE
# Copyright (C) 2018 Dirk Lorenzen a.k.a gCurse
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
require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.constants import Action, Cut_action, Section
from otrverwaltung3p.pluginsystem import Plugin


class CutManually(Plugin):
    Name = "Manuell schneiden"
    Desc = "Öffnet das Cutinterface."
    Author = "Dirk Lorenzen"
    Configurable = False

    def enable(self):
        self.relevant_sections = [Section.VIDEO_UNCUT, Section.VIDEO_CUT]

        if self.app.config.get('general', 'use_internal_icons'):
            image = Gtk.Image.new_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    otrvpath.get_image_path('cut.png'),
                    self.app.config.get("general", "icon_size"),
                    self.app.config.get("general", "icon_size"),
                )
            )
        else:
            image = Gtk.Image.new_from_pixbuf(Gtk.IconTheme.get_default().
                                              load_icon('edit-cut',
                                              self.app.config.get('general', 'icon_size'), 0))

        self.toolbutton = self.gui.main_window.add_toolbutton(image, 'Manuell schneiden', self.relevant_sections)
        self.toolbutton.connect('clicked', self.on_cut_clicked)

        # self.row_activate_id = self.gui.main_window.builder.get_object(
        #     'treeview_files').connect('row-activated', self.on_row_activated)

    def disable(self):
        self.gui.main_window.remove_toolbutton(self.toolbutton)
        # self.gui.main_window.builder.get_object('treeview_files').disconnect(self.row_activate_id)

    # plugin methods
    def start_cut(self):
        self.app.perform_action(Action.CUT, Cut_action.MANUALLY)

    # signal methods
    def on_cut_clicked(self, widget, data=None):
        self.start_cut()

    def on_row_activated(self, treeview, path, view_column):
        if self.app.section in self.relevant_sections:
            self.start_cut()
