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

from pathlib import Path
import logging
import os

from gi import require_version

require_version("Gdk", "3.0")
require_version("GdkPixbuf", "2.0")
require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gtk

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
        self.log = logging.getLogger(self.__class__.__name__)
        self.app = app
        self.ci_instance = None
        self.cursor_blank = Gdk.Cursor(Gdk.CursorType.BLANK_CURSOR)
        self.cursor_wait = Gdk.Cursor(Gdk.CursorType.WATCH)

        def set_transient_modal(self, instance):
            instance.set_transient_for(self.main_window)
            instance.set_modal(True)

        self.main_window = MainWindow.new(app)
        self.main_window.post_init()

        self.monitors = []
        self.monitored = []

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

    def start_directory_monitors(self, restart=False):
        if not restart:
            self.monitored = [
                [
                    Path(self.app.config.get("general", "folder_uncut_avis")),
                    Section.VIDEO_UNCUT,
                    self.app.regex_uncut_video,
                ],
                [Path(self.app.config.get("general", "folder_cut_avis")), Section.VIDEO_CUT, self.app.regex_cut_video],
                [Path(self.app.config.get("general", "folder_new_otrkeys")), Section.OTRKEY, self.app.regex_otrkey],
            ]
            for folder, section, regex in self.monitored:
                if os.path.exists(folder):
                    self.monitors.append(DirectoryMonitor(self.app, folder, section, regex))
            for monitor in self.monitors:
                monitor.start()
        else:
            monitored_paths = [
                Path(self.app.config.get("general", "folder_uncut_avis")),
                Path(self.app.config.get("general", "folder_cut_avis")),
                Path(self.app.config.get("general", "folder_new_otrkeys")),
            ]
            for index in range(len(monitored_paths)):
                folder, section, regex = self.monitored[index]
                if not folder == monitored_paths[index]:
                    self.monitors[index].monitor.cancel()
                    self.log.debug(f"Monitor for {folder} canceled.")
                    if os.path.exists(monitored_paths[index]):
                        self.monitors[index] = DirectoryMonitor(self.app, monitored_paths[index], section, regex)
                        self.log.debug(f"Monitor for {monitored_paths[index]} added.")
            for monitor in self.monitors:
                monitor.start()

    def run(self):
        self.start_directory_monitors()
        Gtk.main()

    # Helpers

    @staticmethod
    def set_model_from_list(cb, items):
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

    # Dialogs

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
