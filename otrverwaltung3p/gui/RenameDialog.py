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

from os.path import basename

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from otrverwaltung3p import path as otrvpath


class RenameDialog(Gtk.Dialog, Gtk.Buildable):
    __gtype_name__ = "RenameDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        pass

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

    def init_and_run(self, title, filenames):
        entries = {}
        for f in filenames:
            entries[f] = Gtk.Entry()
            entries[f].set_text(basename(f))
            entries[f].set_activates_default(True)
            entries[f].show()
            self.builder.get_object('vboxRename').pack_start(entries[f], False, True, 0)

        self.set_title(title)
        response = self.run()
        self.hide()

        # get new names
        new_names = {}
        for f in filenames:
            new_names[f] = entries[f].get_text()

        # remove entry widgets
        for f in entries:
            self.builder.get_object('vboxRename').remove(entries[f])

        return response == Gtk.ResponseType.OK, new_names


def NewRenameDialog():
    glade_filename = otrvpath.getdatapath('ui', 'RenameDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("rename_dialog")

    return dialog
