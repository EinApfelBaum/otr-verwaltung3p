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

import os.path
import shutil
import subprocess
import time

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gio, Gtk

from otrverwaltung3p.pluginsystem import Plugin

from otrverwaltung3p import fileoperations
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.constants import Section
import otrverwaltung3p.cutlists as cutlists_management


class CutPlay(Plugin):
    Name = "Geschnittenes Abspielen"
    Desc = (
        "Spielt Video-Dateien mit Hilfe von Cutlisten geschnitten ab, ohne jedoch die "
        "Datei zu schneiden. Es werden die Server-Einstellungen von OTR-Verwaltung benutzt."
    )
    Author = "Benjamin Elbers, gCurse"
    Configurable = False

    def enable(self):
        if self.app.config.get("general", "use_internal_icons"):
            image = Gtk.Image.new_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    otrvpath.get_image_path("play.png"),
                    self.app.config.get("general", "icon_size"),
                    self.app.config.get("general", "icon_size"),
                )
            )
        else:
            image = Gtk.Image.new_from_pixbuf(
                Gtk.IconTheme.get_default().load_icon(
                    "media-playback-start", self.app.config.get("general", "icon_size"), 0,
                )
            )

        self.toolbutton = self.gui.main_window.add_toolbutton(image, "Geschnitten abspielen", [Section.VIDEO_UNCUT])
        self.toolbutton.connect("clicked", self.on_cut_play_clicked)

    def disable(self):
        self.gui.main_window.remove_toolbutton(self.toolbutton)

    ### signal methods ###

    def on_cut_play_clicked(self, widget, data=None):
        filename = self.gui.main_window.get_selected_filenames()[0]

        error, cutlists = cutlists_management.download_cutlists(
            filename,
            self.app.config.get("general", "server"),
            self.app.config.get("general", "choose_cutlists_by"),
            self.app.config.get("general", "cutlist_mp4_as_hq"),
        )
        if error:
            return

        cutlist = cutlists_management.get_best_cutlist(cutlists)
        cutlist.download(self.app.config.get("general", "server"), filename)
        cutlist.read_cuts()

        # delete cutlist?
        if self.app.config.get("general", "delete_cutlists"):
            fileoperations.remove_file(cutlist.local_filename)

        # make mplayer edl
        # http://www.mplayerhq.hu/DOCS/HTML/en/edl.html
        # [Begin Second] [End Second] [0=Skip/1=Mute]
        edl_filename = os.path.join(self.app.config.get("general", "folder_uncut_avis"), ".tmp.edl")
        with open(edl_filename, "w") as f:
            f.write("0 %s 0\n" % (cutlist.cuts_seconds[0][0] - 1))
            for count, (start, duration) in enumerate(cutlist.cuts_seconds):
                end = start + duration
                if count + 1 == len(cutlist.cuts_seconds):
                    f.write("%s 50000 0\n" % end)
                else:
                    f.write("%s %s 0\n" % (end, (cutlist.cuts_seconds[count + 1][0] - 1)))

        # make mpv edl
        # https://github.com/mpv-player/mpv-player.github.io/blob/master/guides/edl-playlists.rst
        edlurl = "edl://"
        for count, (start, duration) in enumerate(cutlist.cuts_seconds):
            edlurl = edlurl + filename + "," + str(start) + "," + str(duration) + ";"

        def check_prog(prog):
            cmdfound = False
            plays = False

            if shutil.which(prog):
                cmdfound = True
                if not subprocess.call(
                    prog, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                ):
                    plays = True
                else:
                    self.log.error("{} failed to start.".format(prog))
            else:
                exist = False
                self.log.error("{} is not installed.".format(prog))
            return cmdfound and plays

        def play_with(prog):
            if prog == "mplayer":
                self.p = subprocess.Popen([self.app.config.get_program("mplayer"), "-edl", edl_filename, filename,])
            elif prog == "mpv":
                self.p = subprocess.Popen([self.app.config.get_program("mpv"), edlurl])

        if self.app.config.get("general", "prefer_mplayer"):
            self.playprog = ["mplayer", "mpv"]
        else:
            self.playprog = ["mpv", "mplayer"]

        if check_prog(self.playprog[0]):
            play_with(self.playprog[0])
        elif check_prog(self.playprog[1]):
            play_with(self.playprog[1])
        else:
            self.gui.message_error_box(
                "Zum Anzeigen der Schnitte sind weder mpv noch mplayer " "installiert bzw. funktionieren nicht."
            )
            return

        while self.p.poll() is None:
            time.sleep(1)
            while Gtk.events_pending():
                Gtk.main_iteration()

        fileoperations.remove_file(edl_filename)
        print("removing: {}".format(edl_filename))
