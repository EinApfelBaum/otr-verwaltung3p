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
from gi.repository import Gtk

from otrverwaltung import path
from otrverwaltung.gui.widgets.FolderChooserComboBox import FolderChooserComboBox

gi.require_version('Gtk', '3.0')


class ArchiveDialog(Gtk.Dialog, Gtk.Buildable):
    __gtype_name__ = "ArchiveDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        pass

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

        self.combobox_folder = FolderChooserComboBox()
        self.combobox_folder.show()
        self.builder.get_object('vbox_main').pack_end(self.combobox_folder, False, False, 0)

    #
    # Convenience methods
    #

    def run(self, filenames, archive_directory):

        self.combobox_folder.fill(archive_directory)
        self.combobox_folder.set_active(0)

        self.builder.get_object('label_files').set_text(str(len(filenames)) + " Datei(en) zum Archivieren ausgewählt.")

        self.builder.get_object('liststore_rename').clear()
        for filename in filenames:
            self.builder.get_object('liststore_rename').append([basename(filename), filename])

        result = Gtk.Dialog.run(self)

        if result == Gtk.ResponseType.OK:
            renamed_filenames = {}
            for row in self.builder.get_object('liststore_rename'):
                renamed, original = row[0], row[1]
                renamed_filenames[original] = renamed
            return True, renamed_filenames, self.combobox_folder.get_active_path()
        else:
            return False, None, None

    #
    # Signal handlers
    #

    def new_name_cell_edited(self, cell, path, new_text):
        # update new name of file in model
        self.builder.get_object('liststore_rename')[path][0] = new_text


def NewArchiveDialog():
    glade_filename = path.getdatapath('ui', 'ArchiveDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("archive_dialog")

    return dialog
