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

import gi
from gi.repository import Gtk, GdkPixbuf, Pango
import os
gi.require_version('Gtk', '3.0')


class FolderChooserComboBox(Gtk.ComboBox):
    def __init__(self, add_empty_entry=False):
        Gtk.ComboBox.__init__(self)

        self.add_empty_entry = add_empty_entry

        # setup combobox_archive       name    pixbuf     indent path
        self.liststore = Gtk.ListStore(str, GdkPixbuf.Pixbuf, str, str)
        self.COL_NAME = 0
        self.COL_PIXBUF = 1
        self.COL_PATH = 3
        self.set_model(self.liststore)

        cell = Gtk.CellRendererText()
        self.pack_start(cell, False)
        self.add_attribute(cell, 'text', 2)

        cell = Gtk.CellRendererPixbuf()
        cell.set_property('xpad', 5)
        self.pack_start(cell, False)
        self.add_attribute(cell, 'pixbuf', self.COL_PIXBUF)

        cell = Gtk.CellRendererText()
        cell.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', self.COL_NAME)

    def __separator(self, model, iter, data=None):
        return (model.get_value(iter, self.COL_NAME) == '-')

    def get_active_path(self):
        iter = self.get_active_iter()
        if iter:
            return self.liststore.get_value(iter, self.COL_PATH)
        else:
            return ""

    def fill(self, path):
        image = Gtk.IconTheme.get_default().load_icon('folder-symbolic', 16, Gtk.IconLookupFlags.USE_BUILTIN)

        self.liststore.clear()

        if self.add_empty_entry:
            self.liststore.append(["Nicht archivieren", None, "", ""])
            self.liststore.append(["-", None, "", ""])
            self.set_row_separator_func(self.__separator)

        # root folder
        self.liststore.append([path.split('/')[-1], image, "", path])

        fill_up = "—"
        for root, dirs, files in os.walk(path):
            directory = root[len(path) + 1:].split('/')

            if not directory[0]: continue

            self.liststore.append([directory[-1], image, fill_up * len(directory), root])
