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

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import os, re, logging

from otrverwaltung.constants import Cut_action
import otrverwaltung.cutlists as cutlists_management
from otrverwaltung import fileoperations
from otrverwaltung import path
from otrverwaltung.gui.widgets.CutlistsTreeView import CutlistsTreeView
from otrverwaltung.GeneratorTask import GeneratorTask


class LoadCutDialog(Gtk.Dialog, Gtk.Buildable):
    """ Dialog, um Cutlists lokal oder von cutlist.at zu laden """

    __gtype_name__ = "LoadCutDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.download_error = False
        self.cutlists_list = []
        self.download_first_try = True

    def do_parser_finished(self, builder):
        self.log.debug("Function start")
        self.builder = builder
        self.builder.connect_signals(self)

        self.chosen_cutlist = None

        self.treeview_local_cutlists = CutlistsTreeView()
        self.treeview_local_cutlists.show()
        self.treeview_local_cutlists.get_selection().connect(
                                                    'changed', self._on_local_selection_changed)
        self.builder.get_object('scrolledwindow_local').add(self.treeview_local_cutlists)
        self.treeview_download_cutlists = CutlistsTreeView()
        self.treeview_download_cutlists.show()
        self.treeview_download_cutlists.get_selection().connect(
                                                    'changed', self._on_download_selection_changed)
        self.builder.get_object('scrolledwindow_download').add(self.treeview_download_cutlists)

        self.filename = ""

    ###
    ### Convenience methods
    ###

    def setup(self, video_file):
        self.filename = video_file
        self.builder.get_object('label_file').set_markup("<b>%s</b>" % os.path.basename(video_file))

        # looking for local cutlists
        p, filename = os.path.split(video_file)
        cutregex = re.compile("^" + filename + "\.?(.*).cutlist$")
        files = os.listdir(p)
        local_cutlists = []
        for f in files:
            match = cutregex.match(f)
            if match:
                local_cutlists.append(p + '/' + match.group())
            else:
                pass

        if len(local_cutlists) > 0:
            self.treeview_local_cutlists.get_model().clear()
            self.builder.get_object('scrolledwindow_local').set_sensitive(True)
            self.builder.get_object('button_local').set_sensitive(True)
            for c in local_cutlists:
                cutlist = cutlists_management.Cutlist()
                cutlist.local_filename = c
                cutlist.read_from_file()
                self.cutlists_list.append(cutlist)
                # ~ self.treeview_local_cutlists.add_cutlist(cutlist)
            ## Sorting ->
            self.cutlists_list.sort(key=lambda x: x.quality, reverse=False)
            for cutlist_obj in self.cutlists_list:
                self.treeview_local_cutlists.add_cutlist(cutlist_obj)
            ## <- Sorting

        else:
            self.builder.get_object('scrolledwindow_local').set_sensitive(False)
            self.builder.get_object('button_local').set_active(False)
            self.builder.get_object('button_local').set_sensitive(False)

        self.download_generator(False)

    def download_generator(self, get_all_qualities):
        # start looking for downloadable cutlists
        self.treeview_download_cutlists.get_model().clear()
        self.builder.get_object('label_status').set_markup(
                                                "<b>Cutlisten werden heruntergeladen...</b>")
        self.download_error = False

        # Empty the list for reuse
        self.cutlists_list = []
        GeneratorTask(cutlists_management.download_cutlists, None, self._completed).\
                            start(self.filename, self.app.config.get('general', 'server'),
                                  self.app.config.get('general', 'choose_cutlists_by'),
                                  self.app.config.get('general', 'cutlist_mp4_as_hq'),
                                  self._error_cb, self._cutlist_found_cb, get_all_qualities)

    def _error_cb(self, error):
        if error == "Keine Cutlists gefunden" and self.download_first_try:
            self.download_first_try = False
            self.builder.get_object('label_status').set_markup("<b>%s</b>" % error +
                                                        ". Versuche es mit allen Qualitäten")
            self.download_generator(True)
        else:
            self.builder.get_object('label_status').set_markup("<b>%s</b>" % error +
                                                    " (Es wurde nach allen Qualitäten gesucht)")
            self.download_error = True
            self.download_first_try = True

    def _cutlist_found_cb(self, cutlist):
        ## Sorting
        # ~ self.add_cutlist(cutlist)
        self.cutlists_list.append(cutlist)

    def _completed(self):
        if not self.download_error:
            ## Sorting ->
            self.cutlists_list.sort(key=lambda x: x.quality, reverse=False)
            for cutlist_obj in self.cutlists_list:
                self.add_cutlist(cutlist_obj)
            ## <- Sorting
            self.builder.get_object('label_status').set_markup("")

    def add_cutlist(self, c):
        self.treeview_download_cutlists.add_cutlist(c)

    ###
    ### Signal handlers
    ###

    def _on_local_selection_changed(self, selection, data=None):
        model, paths = selection.get_selected_rows()
        if paths:
            self.builder.get_object('button_local').set_active(True)
            self.treeview_download_cutlists.get_selection().unselect_all()

    def _on_download_selection_changed(self, selection, data=None):
        model, paths = selection.get_selected_rows()
        if paths:
            self.builder.get_object('button_download').set_active(True)
            self.treeview_local_cutlists.get_selection().unselect_all()

    def on_button_ok_clicked(self, widget, data=None):
        if self.builder.get_object('button_local').get_active() == True:
            cutlist = self.treeview_local_cutlists.get_selected()

            if not cutlist:
                self.gui.message_error_box("Es wurde keine Cutlist ausgewählt!")
                return

            self.result = cutlist
            self.response(1)

        elif self.builder.get_object('button_download').get_active() == True:
            cutlist = self.treeview_download_cutlists.get_selected()

            if not cutlist:
                self.gui.message_error_box("Es wurde keine Cutlist ausgewählt!")
                return

            cutlist.download(self.app.config.get('general', 'server'), self.filename)
            self.result = cutlist
            self.response(1)


def NewLoadCutDialog(app, gui):
    glade_filename = path.getdatapath('ui', 'LoadCutDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("load_cut_dialog")
    dialog.app = app
    dialog.gui = gui

    return dialog
