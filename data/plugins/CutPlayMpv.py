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

import subprocess, time
import os.path
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from otrverwaltung.pluginsystem import Plugin

import otrverwaltung.cutlists as cutlists_management
from otrverwaltung import fileoperations
from otrverwaltung.constants import Section


class CutPlayMpv(Plugin):
    Name = "Mit mpv geschnitten abspielen"
    Desc = "Spielt Video-Dateien mit Hilfe von Cutlisten geschnitten ab, ohne jedoch die Datei zu schneiden. Es werden die Server-Einstellungen von OTR-Verwaltung benutzt."
    Author = "Benjamin Elbers, gcurse"
    Configurable = False

    def enable(self):
        self.toolbutton = self.gui.main_window.add_toolbutton(Gtk.Image.new_from_file(self.get_path('play.png')),
                                                              'Mpv geschnitten abspielen', [Section.VIDEO_UNCUT])
        self.toolbutton.connect('clicked', self.on_cut_play_clicked)

    def disable(self):
        self.gui.main_window.remove_toolbutton(self.toolbutton)

        # plugin methods

    # signal methods
    def on_cut_play_clicked(self, widget, data=None):
        filename = self.gui.main_window.get_selected_filenames()[0]

        error, cutlists = cutlists_management.download_cutlists(filename, self.app.config.get('general', 'server'),
                                                                self.app.config.get('general', 'choose_cutlists_by'),
                                                                self.app.config.get('general', 'cutlist_mp4_as_hq'))
        if error:
            return

        cutlist = cutlists_management.get_best_cutlist(cutlists)
        cutlist.download(self.app.config.get('general', 'server'), filename)
        cutlist.read_cuts()

        # delete cutlist?        
        if self.app.config.get('general', 'delete_cutlists'):
            fileoperations.remove_file(cutlist.local_filename)

        # make edl
        # https://github.com/mpv-player/mpv-player.github.io/blob/master/guides/edl-playlists.rst
        edlurl="edl://"

        for count, (start, duration) in enumerate(cutlist.cuts_seconds):
            edlurl = edlurl + filename + "," + str(start) + "," + str(duration) + ";"

        p = subprocess.Popen([self.app.config.get_program('mpv'), edlurl])

        while p.poll() == None:
            time.sleep(1)
            while Gtk.events_pending():
                Gtk.main_iteration()
