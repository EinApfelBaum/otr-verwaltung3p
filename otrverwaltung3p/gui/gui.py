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

import os

from gi import require_version

require_version("GdkPixbuf", "2.0")
require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gtk

from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.constants import Section
from otrverwaltung3p.directorymonitor import DirectoryMonitor
from otrverwaltung3p.gui import (
    ArchiveDialog,
    ConclusionDialog,
    CutDialog,
    EmailPasswordDialog,
    MainWindow,
    PlanningDialog,
    PluginsDialog,
    PreferencesWindow,
    RenameDialog,
)


class Gui:
    def __init__(self, app):
        self.app = app
        self.ci_instance = None

        def set_transient_modal(self, instance):
            instance.set_transient_for(self.main_window)
            instance.set_modal(True)

        # TODO: einheitliches benennungsschema für widgets: MainWindow oder main_window
        self.main_window = MainWindow.new(app)
        self.main_window.post_init()

        self.preferences_window = PreferencesWindow.new()
        self.preferences_window.bind_config(app)
        set_transient_modal(self, self.preferences_window)

        self.dialog_archive = ArchiveDialog.new()
        set_transient_modal(self, self.dialog_archive)

        self.dialog_conclusion = ConclusionDialog.new(app)
        set_transient_modal(self, self.dialog_conclusion)

        self.dialog_cut = CutDialog.new(app, self)
        set_transient_modal(self, self.dialog_cut)

        self.dialog_email_password = EmailPasswordDialog.new(app)
        set_transient_modal(self, self.dialog_email_password)

        self.dialog_rename = RenameDialog.new()
        set_transient_modal(self, self.dialog_rename)

        self.dialog_planning = PlanningDialog.new(self)
        set_transient_modal(self, self.dialog_planning)

        self.dialog_plugins = PluginsDialog.new(self)
        set_transient_modal(self, self.dialog_plugins)

        for window in [self.main_window]:
            window.set_icon(GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path("icon.png")))

    def run(self):
        # DirectoryMonitor
        monitors = []
        monitored = [
            [self.app.config.get("general", "folder_uncut_avis"), Section.VIDEO_UNCUT, self.app.regex_uncut_video],
            [self.app.config.get("general", "folder_cut_avis"), Section.VIDEO_CUT, self.app.regex_cut_video],
            [self.app.config.get("general", "folder_new_otrkeys"), Section.OTRKEY, self.app.regex_otrkey],
        ]

        for folder, section, regex in monitored:
            if os.path.exists(folder):
                monitors.append(DirectoryMonitor(self.app, folder, section, regex))
        for monitor in monitors:
            monitor.start()

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
            cb.add_attribute(cell, "text", 0)

    #
    # Dialogs
    #

    def message_info_box(self, message_text):
        dialog = self.__get_dialog(Gtk.MessageType.INFO, Gtk.ButtonsType.OK, message_text)

        dialog.run()
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
        dialog = Gtk.MessageDialog(
            self.main_window,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            message_type,
            message_buttons,
        )
        dialog.set_markup(message_text)
        return dialog
