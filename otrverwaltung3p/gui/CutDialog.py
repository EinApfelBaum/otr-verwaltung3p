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
from gi.repository import Gtk
from os.path import basename, exists

from otrverwaltung3p.constants import Cut_action
import otrverwaltung3p.cutlists as cutlists_management
from otrverwaltung3p import fileoperations
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.gui.widgets.CutlistsTreeView import CutlistsTreeView
from otrverwaltung3p.GeneratorTask import GeneratorTask

gi.require_version('Gtk', '3.0')

class CutDialog(Gtk.Dialog, Gtk.Buildable):
    """ Dialog, um den Schnittmodus constants.Cut_action und ggf die Cutlist auszuwählen """

    __gtype_name__ = "CutDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        pass

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

        self.chosen_cutlist = None

        self.treeview_cutlists_download = CutlistsTreeView()
        self.treeview_cutlists_download.show()
        self.treeview_cutlists_download.get_selection().connect('changed',
                                                            self._on_selection_changed_download)
        self.builder.get_object('scrolledwindow_cutlists').add(self.treeview_cutlists_download)

        self.filename = ""

    #
    # Convenience methods
    #

    def setup(self, video_file, folder_cut_avis, cut_action_ask):
        self.filename = video_file
        self.builder.get_object('label_file').set_markup("<b>%s</b>" % basename(video_file))
        self.builder.get_object('label_warning').set_markup(
                    '<span size="small">Wichtig! Um eine Cutlist zu erstellen muss das Projekt ' +
                    'im Ordner ' + folder_cut_avis + ' gespeichert werden (siehe ' +
                    'Website->Einstieg->Funktionen). OTR-Verwaltung schneidet die ' +
                    'Datei dann automatisch.</span>')

        if cut_action_ask:
            self.builder.get_object('radio_best_cutlist').set_active(True)
        else:
            self.builder.get_object('radio_choose_cutlist').set_active(True)

        # looking for a local cutlist
        filename_cutlist = video_file + ".cutlist"
        if exists(filename_cutlist):
            self.builder.get_object('label_cutlist').set_markup("<b>%s</b>" % filename_cutlist)
            self.builder.get_object('radio_local_cutlist').set_sensitive(True)
        else:
            self.builder.get_object('label_cutlist').set_markup("Keine lokale Cutlist gefunden.")
            self.builder.get_object('radio_local_cutlist').set_sensitive(False)

        # start looking for cutlists
        self.treeview_cutlists_download.get_model().clear()
        self.builder.get_object('label_status').set_markup(
                                                    "<b>Cutlisten werden heruntergeladen...</b>")

    def add_cutlist(self, c):
        self.treeview_cutlists_download.add_cutlist(c)

    #
    # Signal handlers
    #

    def _on_radio_manually_toggled(self, widget, data=None):
        self.builder.get_object('button_show_cuts').set_sensitive(not widget.get_active())

    def _on_radio_best_cutlist_toggled(self, widget, data=None):
        self.builder.get_object('button_show_cuts').set_sensitive(not widget.get_active())

    def _on_button_show_cuts_clicked(self, widget, data=None):
        cutlist = cutlists_management.Cutlist()

        if self.builder.get_object('radio_local_cutlist').get_active():
            cutlist.local_filename = self.builder.get_object('label_cutlist').get_text()

        else:
            cutlist = self.treeview_cutlists_download.get_selected()

            if not cutlist:
                self.gui.message_error_box("Es wurde keine Cutlist ausgewählt!")
                return

            error = cutlist.download(self.app.config.get('general', 'server'), self.filename)

            if error:
                self.gui.message_error_box(error)
                return

        self.app.show_cuts(self.filename, cutlist)

        # delete cutlist
        if self.app.config.get('general', 'delete_cutlists'):
            fileoperations.remove_file(cutlist.local_filename)

    def _on_selection_changed_download(self, selection, data=None):
        model, paths = selection.get_selected_rows()
        if paths:
            self.builder.get_object('radio_choose_cutlist').set_active(True)

    def _on_buttonCutOK_clicked(self, widget, data=None):
        if self.builder.get_object('radio_best_cutlist').get_active() == True:
            self.response(Cut_action.BEST_CUTLIST)

        elif self.builder.get_object('radio_choose_cutlist').get_active() == True:
            cutlist = self.treeview_cutlists_download.get_selected()

            if not cutlist:
                self.gui.message_error_box("Es wurde keine Cutlist ausgewählt!")
                return

            self.chosen_cutlist = cutlist
            self.response(Cut_action.CHOOSE_CUTLIST)

        elif self.builder.get_object('radio_local_cutlist').get_active() == True:
            self.response(Cut_action.LOCAL_CUTLIST)
        else:
            self.response(Cut_action.MANUALLY)


def NewCutDialog(app, gui):
    glade_filename = otrvpath.getdatapath('ui', 'CutDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("cut_dialog")
    dialog.app = app
    dialog.gui = gui

    return dialog
