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
import sys

try:
    import gi

    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GdkPixbuf
except:
    print("PyGTK/GTK is missing.")
    sys.exit(-1)

from otrverwaltung.gui import MainWindow, PreferencesWindow, ArchiveDialog, ConclusionDialog, CutDialog, \
    EmailPasswordDialog, RenameDialog, PlanningDialog, PluginsDialog

from otrverwaltung import path


class Gui:
    def __init__(self, app):
        self.app = app

        # TODO: einheitliches benennungsschema für widgets: MainWindow oder main_window        
        self.main_window = MainWindow.NewMainWindow(app, self)
        self.main_window.post_init()
        self.preferences_window = PreferencesWindow.NewPreferencesWindow(app, self)
        self.preferences_window.bind_config(app.config)

        self.dialog_archive = ArchiveDialog.NewArchiveDialog()
        self.dialog_conclusion = ConclusionDialog.NewConclusionDialog(app, self)
        self.dialog_cut = CutDialog.NewCutDialog(app, self)
        self.dialog_email_password = EmailPasswordDialog.NewEmailPasswordDialog()
        # self.dialog_rename = RenameDialog.NewRenameDialog()
        # self.dialog_planning = PlanningDialog.NewPlanningDialog(self)
        # self.dialog_plugins = PluginsDialog.NewPluginsDialog(self)

        for window in [self.main_window]:
            window.set_icon(GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('icon3.png')))

    def run(self):
        Gtk.main()

    #
    # Helpers
    #

    def set_model_from_list(self, cb, items):
        """Setup a ComboBox or ComboBoxEntry based on a list of strings."""
        for i in items:
            cb.append_text(i)
        if type(cb) == Gtk.ComboBoxText:
            cb.set_active(0)
            pass
        elif type(cb) == Gtk.ComboBox:
            cell = Gtk.CellRendererText()
            cb.pack_start(cell, True)
            cb.add_attribute(cell, 'text', 0)

    #
    # Dialogs
    #

    def message_info_box(self, message_text):
        dialog = self.__get_dialog(Gtk.MessageType.INFO, Gtk.ButtonsType.OK, message_text)

        result = dialog.run()
        dialog.destroy()

    def message_error_box(self, message_text):
        dialog = self.__get_dialog(Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, message_text)

        dialog.run()
        dialog.destroy()

    def question_box(self, message_text):
        dialog = self.__get_dialog(Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, message_text)

        result = dialog.run()
        dialog.destroy()

        return result == Gtk.ResponseType.YES

    def __get_dialog(self, message_type, message_buttons, message_text):
        return Gtk.MessageDialog(
            self.main_window,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            message_type,
            message_buttons,
            message_text)


if __name__ == "__main__":
    print("Usage: otr.py")
    sys.exit(-1)
