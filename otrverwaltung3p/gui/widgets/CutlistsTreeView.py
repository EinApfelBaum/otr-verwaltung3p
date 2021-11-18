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

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gtk

from otrverwaltung3p import path as otrvpath


class CutlistsTreeView(Gtk.TreeView):
    def __init__(self):
        Gtk.TreeView.__init__(self)

        self.pixbuf_warning = GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path("error.png"))

        self.errors = {
            "100000": "Fehlender Beginn",
            "010000": "Fehlendes Ende",
            "001000": "Kein Video",
            "000100": "Kein Audio",
            "000010": "Anderer Fehler",
            "000001": "Falscher Inhalt/EPG-Error",
        }

        # setup combobox_archive
        self.liststore = Gtk.ListStore(object)
        self.set_model(self.liststore)

        # create the TreeViewColumns to display the data
        column_names = [
            ("Art", "quality"),
            ("Autor", "author"),
            ("A.wert", "ratingbyauthor"),
            ("B.wert", self._treeview_rating),
            ("Kommentar", "usercomment"),
            ("Fehler", self._treeview_errors),
            ("Eigentl. Inhalt", self._treeview_actualcontent),
            ("Cuts", "countcuts"),
            ("Dateiname", "filename"),
            ("Dauer [s]", "duration"),
            ("Dauer", "duration_hms"),
            ("Down", "downloadcount"),
        ]

        self.tooltip_text = [
            "Qualität: HD/HQ/AVI/MP4",
            "Autor",
            "Bewertung des Autors",
            "Bewertung der Benutzer (Anzahl der Bewertungen)",
            "Kommentar",
            "Falscher Inhalt/EPG-Fehler",
            "Eigentlicher Inhalt",
            "Anzahl der Schnitte",
            "Dateiname",
            "Dauer in Sekunden",
            "Dauer in Stunden:Minuten:Sekunden",
            "Anzahl der Downloads",
        ]

        # add a pixbuf renderer in case of errors in cutlists
        cell_renderer_pixbuf = Gtk.CellRendererPixbuf()
        col = Gtk.TreeViewColumn("", cell_renderer_pixbuf)
        col.set_cell_data_func(cell_renderer_pixbuf, self._treeview_warning)
        self.append_column(col)

        self.columntitles_index = {}
        # append the columns
        for count, (text, data_func) in enumerate(column_names):
            self.columntitles_index[text] = count
            renderer_left = Gtk.CellRendererText()
            renderer_left.set_property("xalign", 0.0)
            col = Gtk.TreeViewColumn(text, renderer_left)

            if type(data_func) == str:
                col.set_cell_data_func(renderer_left, self._treeview_standard, data_func)
            else:
                col.set_cell_data_func(renderer_left, data_func)

            col.set_resizable(True)
            if count == 5 or count == 6:
                col.set_fixed_width(20)
            self.append_column(col)

        self.props.has_tooltip = True
        self.connect("query-tooltip", self._on_query_tooltip)

    def _on_query_tooltip(self, widget, x, y, keyboard_tooltip, tooltip):
        if keyboard_tooltip:
            path, column = self.get_cursor()
            if not path:
                return False
        else:
            bin_x, bin_y = self.convert_widget_to_bin_window_coords(x, y)
            result = self.get_path_at_pos(bin_x, bin_y)
            if result is None:
                return False
            path, column, _, _ = result

        tooltip.set_text(self.tooltip_text[self.columntitles_index[column.props.title]])
        self.set_tooltip_cell(tooltip, path, column, None)
        return True

    def get_selected(self):
        model, selected_row = self.get_selection().get_selected()
        if selected_row:
            return model.get_value(selected_row, 0)
        else:
            return None

    @staticmethod
    def _treeview_standard(column, cell, model, iter_, attribute_name):
        cutlist = model.get_value(iter_, 0)
        try:
            cell.set_property("text", str(getattr(cutlist, attribute_name)))
        except AttributeError:
            pass

    def _treeview_warning(self, column, cell, model, iter_, data):
        cutlist = model.get_value(iter_, 0)

        if cutlist.errors or cutlist.actualcontent or cutlist.othererrordescription:
            cell.set_property("pixbuf", self.pixbuf_warning)
        else:
            cell.set_property("pixbuf", None)

    @staticmethod
    def _treeview_rating(column, cell, model, iter_, data):
        cutlist = model.get_value(iter_, 0)
        if cutlist.rating:
            cell.set_property("text", f"{cutlist.rating} ({cutlist.ratingcount})")
        else:
            cell.set_property("text", "Keine")

    @staticmethod
    def _treeview_actualcontent(column, cell, model, iter_, data):
        cutlist = model.get_value(iter_, 0)
        cell.set_property("markup", f"<span foreground='red'>{cutlist.actualcontent}</span>")

    @staticmethod
    def _treeview_errors(column, cell, model, iter_, data):
        cutlist = model.get_value(iter_, 0)
        text = f"<span foreground='red'>{cutlist.errors}"
        if cutlist.othererrordescription:
            text += f" ({cutlist.othererrordescription})"
        text += "</span>"

        cell.set_property("markup", text)

    @staticmethod
    def _treeview_error_desc(column, cell, model, iter_):
        cutlist = model.get_value(iter_, 0)
        cell.set_property("markup", f"<span foreground='red'>{cutlist.othererrordescription}</span>")

    def add_cutlist(self, c):
        columns = self.get_columns()
        if c.errors in self.errors:
            columns[6].set_fixed_width(-1)
            columns[7].set_fixed_width(-1)
            c.errors = self.errors[c.errors]
        else:
            c.errors = ""

        self.liststore.append([c])
