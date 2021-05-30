#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import sys
import subprocess

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

from otrverwaltung3p.pluginsystem import Plugin
from otrverwaltung3p.constants import Section


class Mediainfo(Plugin):
    Name = "MediaInfo"
    Desc = "Analyse der Mediendatei"
    Author = "monarc99"
    Configurable = True
    Config = {"mediainfo": "mediainfo-gui"}

    def enable(self):
        icon_size = self.app.config.get("general", "icon_size")
        icon = GdkPixbuf.Pixbuf.new_from_file_at_size(self.get_path("mediainfo.svg"), icon_size, icon_size)
        self.toolbutton = self.gui.main_window.add_toolbutton(
            Gtk.Image.new_from_pixbuf(icon),
            "MediaInfo",
            [Section.VIDEO_UNCUT, Section.VIDEO_CUT, Section.ARCHIVE, Section.TRASH],
        )
        self.toolbutton.connect("clicked", self.mediainfo)

    def disable(self):
        self.gui.main_window.remove_toolbutton(self.toolbutton)

        def configurate(self, dialog):
            dialog.vbox.set_spacing(4)

            dialog.vbox.pack_start(Gtk.Label("Aufrufname der mediainfo GUI:"), expand=False)

            entry_mediainfo = Gtk.Entry()
            dialog.vbox.pack_start(entry_mediainfo, expand=False)

            def on_entry_mediainfo_changed(widget, data=None):
                self.Config["mediainfo"] = widget.get_text()

            entry_mediainfo.connect("changed", on_entry_mediainfo_changed)

            # current config
            entry_mediainfo.set_text(self.Config["mediainfo"])

            return dialog

    def mediainfo(self, widget):
        """ Öffne die Datei mit mediainfo """

        args = self.gui.main_window.get_selected_filenames()
        if sys.platform == "win32":
            args[:0] = [self.app.config.get_program("mediainfo")]
        else:
            args[:0] = [self.Config["mediainfo"]]

        subprocess.Popen(args, stdout=subprocess.PIPE)
