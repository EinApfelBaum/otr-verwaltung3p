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

import logging
import os
import re

from gi import require_version

require_version("Gdk", "3.0")
require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

import otrverwaltung3p.cutlists as cutlists_management
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.GeneratorTask import GeneratorTask
from otrverwaltung3p.gui.widgets.CutlistsTreeView import CutlistsTreeView


class LoadCutDialog(Gtk.Dialog, Gtk.Buildable):
    """ Dialog, um Cutlists lokal oder von cutlist.at zu laden """

    __gtype_name__ = "LoadCutDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.builder = None
        self.chosen_cutlist = None
        self.cutlists_list = []
        self.cutlists_list_before_size_search = []
        self.download_error = False
        self.download_try = 0
        self.filename = ""
        self.local_cutlist_avail = False
        self.result = None
        self.treeview_download_cutlists = None
        self.treeview_local_cutlists = None
        # self.regex_uncut_video = re.compile(
        #     r".*_([0-9]{2}\.){2}([0-9]){2}_([0-9]){2}-([0-9]){2}_.*_([0-9])"
        #     r"*_TVOON_DE.mpg\.(avi|HQ\.avi|HD\.avi|HD\.test\.avi|mp4|mkv|HQ\.mkv"
        #     r"|HD\.mkv|HD\.test\.mkv|mp4\.mkv|HQ\.mp4|HD\.mp4)$"
        # )

    def do_parser_finished(self, builder):
        self.log.debug("Function start")
        self.builder = builder
        self.builder.connect_signals(self)

        self.treeview_local_cutlists = CutlistsTreeView()
        self.treeview_local_cutlists.show()
        self.treeview_local_cutlists.get_selection().connect("changed", self._on_local_selection_changed)
        self.builder.get_object("scrolledwindow_local").add(self.treeview_local_cutlists)
        self.treeview_download_cutlists = CutlistsTreeView()
        self.treeview_download_cutlists.show()
        self.treeview_download_cutlists.get_selection().connect("changed", self._on_download_selection_changed)
        self.builder.get_object("scrolledwindow_download").add(self.treeview_download_cutlists)
        lcd_window = self.builder.get_object("load_cut_dialog")
        lcd_window.set_size_request(
            int(lcd_window.size_request().width * 1.00), int(lcd_window.size_request().height * 1.50),
        )

    # Convenience methods

    def setup(self, video_file):
        self.filename = video_file
        self.builder.get_object("label_file").set_markup(f"<b>{os.path.basename(video_file)}</b>")
        self.builder.get_object("btn_search_size").set_visible = False

        # looking for local cutlists
        p, filename = os.path.split(video_file)
        cutregex = re.compile("^" + filename + r"\.?(.*).cutlist$")
        files = os.listdir(p)
        local_cutlists = []
        for f in files:
            match = cutregex.match(f)
            if match:
                local_cutlists.append(p + "/" + match.group())
            else:
                pass

        if len(local_cutlists) > 0:
            self.treeview_local_cutlists.get_model().clear()
            self.builder.get_object("scrolledwindow_local").set_sensitive(True)
            self.builder.get_object("button_local").set_sensitive(True)
            local_cutlists_list = []  # Sorting
            for c in local_cutlists:
                cutlist = cutlists_management.Cutlist()
                cutlist.local_filename = c
                cutlist.read_from_file()
                local_cutlists_list.append(cutlist)
                # ~ self.treeview_local_cutlists.add_cutlist(cutlist)
            # Sorting <--
            local_cutlists_list.sort(key=lambda x: x.quality, reverse=False)
            for cutlist_obj in local_cutlists_list:
                self.treeview_local_cutlists.add_cutlist(cutlist_obj)
            # --> Sorting
            self.local_cutlist_avail = True  # gcurse: ONLY_ONE_CUTLIST
        else:
            self.builder.get_object("scrolledwindow_local").set_sensitive(False)
            self.builder.get_object("button_local").set_active(False)
            self.builder.get_object("button_local").set_sensitive(False)

        self.download_generator(False)

    def download_generator(self, get_all_qualities, search_for_size=False):
        # start looking for downloadable cutlists
        self.treeview_download_cutlists.get_model().clear()
        self.builder.get_object("label_status").set_markup("<b>Cutlisten werden heruntergeladen...</b>")
        self.download_error = False

        # Empty the list for reuse
        self.cutlists_list = []
        if search_for_size:
            choose_cutlists_by = 0  # by size
        else:
            if not self.app.config.get("cutinterface", "not_force_search_cutlist_by_name"):
                choose_cutlists_by = 1  # by name
            else:
                choose_cutlists_by = self.app.config.get("general", "choose_cutlists_by")

        GeneratorTask(cutlists_management.download_cutlists, None, self._completed).start(
            self.filename,
            self.app.config.get("general", "server"),
            choose_cutlists_by,
            self.app.config.get("general", "cutlist_mp4_as_hq"),
            self._error_cb,
            self._cutlist_found_cb,
            get_all_qualities,
        )

    def _error_cb(self, error):
        if error == "Keine Cutlists gefunden" and self.download_try < 1:
            self.download_try = 1
            self.builder.get_object("label_status").set_markup(f"<b>{error}</b>. Versuche es mit allen Qualitäten.")
            self.download_generator(True, False)
        elif error == "Keine Cutlists gefunden" and self.download_try == 1:
            self.download_try = 2
            self.builder.get_object("label_status").set_markup(
                f"<b>{error}</b>. Letzte Chance! Suche nach Dateigröße."
            )
            self.download_generator(True, True)
        else:
            self.builder.get_object("label_status").set_markup(
                f"<b>{error}</b> (Es wurde nach allen Qualitäten " "und nach Dateigröße gesucht)"
            )
            self.download_error = True

    def _cutlist_found_cb(self, cutlist):
        # root, extension = os.path.splitext(
        #     self.filename
        # )
        # filename = os.path.basename(root)
        # parts = filename.split("_")
        # # parts.reverse()
        # # title_list = parts[6: len(parts)]
        # # title_list.reverse()
        # # title = "_".join(title_list)
        # time = parts[4]
        # date = parts[5]
        # station = parts[3]
        #
        # if all(cutlist.filename_original.find(i) >= 0 for i in [station, time, date]):
        self.cutlists_list.append(cutlist)

    def _completed(self):
        if not self.download_error:
            # Do not sort cutlists if they were found by size
            if self.download_try < 2:
                self.cutlists_list.sort(key=lambda x: x.quality, reverse=False)

            if self.cutlists_list_before_size_search is not None:
                # We did search cutlists by size. only add cutlists that have not been found before
                cutlist_ids = []
                for cutlist_obj in self.cutlists_list_before_size_search:
                    self.add_cutlist(cutlist_obj)  # Add cutlist found before size search
                    cutlist_ids.append(cutlist_obj.id)  # Make a list of found cutlist.ids
                # Add found cutlists to treeview
                for cutlist_obj in self.cutlists_list:
                    if cutlist_obj.id not in cutlist_ids:  # Add only new cutlists
                        self.add_cutlist(cutlist_obj)
            else:
                # Add found cutlists to treeview
                for cutlist_obj in self.cutlists_list:
                    self.add_cutlist(cutlist_obj)

            if self.download_try == 2:
                self.builder.get_object("label_status").set_markup("<b>ACHTUNG:</b> Es wurde nach Dateigröße gesucht!")
            elif self.download_try == 1:
                self.builder.get_object("label_status").set_markup("Es wurde nach allen Qualitäten gesucht.")
            else:
                self.builder.get_object("label_status").set_markup("Es wurde exakt gesucht.")

            if len(self.cutlists_list) != 0:
                self.treeview_download_cutlists.grab_focus()
                if self.treeview_download_cutlists is not None:
                    self.treeview_download_cutlists.get_selection().select_path(Gtk.TreePath.new_first())
            if self.download_try < 2:
                self.builder.get_object("btn_search_size").set_visible = True
            # gcurse: ONLY_ONE_CUTLIST <--
            if len(self.cutlists_list) == 1 and not self.local_cutlist_avail and not self.download_try == 2:
                # Close dialog and return the only cutlist
                self.on_button_ok_clicked(None)
            # --> ONLY_ONE_CUTLIST

    def add_cutlist(self, c):
        self.treeview_download_cutlists.add_cutlist(c)

    # Signal handlers

    def on_load_cut_dialog_key_press_event(self, widget, event, *args):
        """handle keyboard events"""
        keyname = Gdk.keyval_name(event.keyval).upper()
        mod_ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        mod_shift = event.state & Gdk.ModifierType.SHIFT_MASK
        mod_alt = event.state & Gdk.ModifierType.MOD1_MASK

        if event.type == Gdk.EventType.KEY_PRESS:
            # print(keyname)
            if not mod_ctrl and not mod_shift and not mod_alt:
                if keyname == "RETURN":
                    self.builder.get_object("button_ok").clicked()
                    # print("Button OK")
                    return True

    def _on_local_selection_changed(self, selection, data=None):
        model, paths = selection.get_selected_rows()
        if paths:
            self.builder.get_object("button_local").set_active(True)
            self.treeview_download_cutlists.get_selection().unselect_all()

    def _on_download_selection_changed(self, selection, data=None):
        model, paths = selection.get_selected_rows()
        if paths:
            self.builder.get_object("button_download").set_active(True)
            self.treeview_local_cutlists.get_selection().unselect_all()

    def on_button_ok_clicked(self, widget, data=None):
        if self.builder.get_object("button_local").get_active():
            cutlist = self.treeview_local_cutlists.get_selected()
            if not cutlist:
                self.app.gui.message_error_box("Es wurde keine Cutlist ausgewählt!")
                return
            self.result = cutlist
            self.response(1)

        elif self.builder.get_object("button_download").get_active():
            cutlist = self.treeview_download_cutlists.get_selected()
            if not cutlist:
                self.app.gui.message_error_box("Es wurde keine Cutlist ausgewählt!")
                return
            cutlist.download(self.app.config.get("general", "server"), self.filename)
            self.result = cutlist
            self.response(1)

    def on_load_cut_dialog_close(self, widget):
        # self.builder.get_object('btn_search_size').set_visible = False
        return False

    def on_btn_search_size_clicked(self, widget, data=None):
        self.cutlists_list_before_size_search = self.cutlists_list
        self.cutlists_list = []
        self.download_try = 2
        self.download_generator(False, True)


def new(app):
    glade_filename = otrvpath.getdatapath("ui", "LoadCutDialog.glade")
    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("load_cut_dialog")
    dialog.app = app
    return dialog
