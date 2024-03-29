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

import datetime
import logging

import os

# import sys
import time
import webbrowser
from os.path import basename

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import GLib, Gdk, GdkPixbuf, Gio, Gtk

from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.GeneratorTask import GeneratorTask
from otrverwaltung3p.constants import Action, CutAction, DownloadStatus, Section
from otrverwaltung3p.gui import DownloadPropertiesDialog
from otrverwaltung3p.gui.widgets.DownloadsTreeView import DownloadsTreeView
from otrverwaltung3p.gui.widgets.EntrySearchToolItem import EntrySearchToolItem
from otrverwaltung3p.gui.widgets.Sidebar import Sidebar


class MainWindow(Gtk.Window, Gtk.Buildable):
    __gtype_name__ = "MainWindow"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)

        self.builder = None
        self.conclusion_eventbox = None
        self.conclusion_css = b"""
                                * {
                                    transition-property: color, background-color;
                                    transition-duration: 2.5s;
                                }
                                .conclusion {
                                    background-image: none;
                                    background-color: rgb(255,180,0);
                                    color: black;
                                }
                                .conclusion2 {
                                    background-image: none;
                                    background-color: rgb(255,225,0);
                                    color: black;
                                }
                               """
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(self.conclusion_css)
        self.svn_version_url = ""  # gcurse: Delete this later
        self.treeview_files = None

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

    def conf_g(self, option_str):
        self.app.config.get("general", option_str)

    def post_init(self):
        self.__setup_toolbar()
        self.__setup_treeview_planning()
        self.__setup_treeview_download()
        self.__setup_treeview_files()
        self.__setup_widgets()

    def __get_cut_menu(self, action):
        # menu for cut/decodeandcut
        cut_menu = Gtk.Menu()
        items = [
            ("Nachfragen", CutAction.ASK),
            ("Beste Cutlist", CutAction.BEST_CUTLIST),
            ("Cutlist wählen", CutAction.CHOOSE_CUTLIST),
            ("Lokale Cutlist", CutAction.LOCAL_CUTLIST),
            ("Manuell (und Cutlist erstellen)", CutAction.MANUALLY),
        ]

        for label, cut_action in items:
            item = Gtk.MenuItem(label)
            item.show()
            item.connect("activate", self._on_toolbutton_clicked, action, cut_action)
            cut_menu.add(item)

        return cut_menu

    def __setup_toolbar(self):
        toolbar_buttons_internal = [
            ("decodeandcut", "decodeandcut.png", "Dekodieren und Schneiden", Action.DECODEANDCUT,),
            ("decode", "decode.png", "Dekodieren", Action.DECODE),
            ("delete", "bin.png", "In den Müll verschieben", Action.DELETE),
            ("archive", "archive.png", "Archivieren", Action.ARCHIVE),
            ("cut", "cut.png", "Schneiden", Action.CUT),
            ("restore", "restore.png", "Wiederherstellen", Action.RESTORE),
            ("rename", "rename.png", "Umbenennen", Action.RENAME),
            ("new_folder", "new_folder.png", "Neuer Ordner", Action.NEW_FOLDER),
            ("real_delete", "delete.png", "Löschen", Action.REAL_DELETE),
        ]

        toolbar_buttons = [
            ("decodeandcut", "edit-cut", "Dekodieren und Schneiden", Action.DECODEANDCUT,),
            ("decode", "system-lock-screen", "Dekodieren", Action.DECODE),
            ("delete", "user-trash", "In den Müll verschieben", Action.DELETE),
            ("archive", "system-file-manager", "Archivieren", Action.ARCHIVE),
            ("cut", "edit-cut", "Schneiden", Action.CUT),
            ("restore", "view-refresh", "Wiederherstellen", Action.RESTORE),
            ("rename", "edit-redo", "Umbenennen", Action.RENAME),
            ("new_folder", "folder-new", "Neuer Ordner", Action.NEW_FOLDER),
            ("real_delete", "edit-delete", "Löschen", Action.REAL_DELETE),
        ]

        if self.app.config.get("general", "use_internal_icons"):
            toolbar_buttons = toolbar_buttons_internal

        self.__toolbar_buttons = {}
        for key, image_name, text, action in toolbar_buttons:
            if self.app.config.get("general", "use_internal_icons"):
                # image = Gtk.Image.new_from_file(otrvpath.get_image_path(image_name))
                image = Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_size(
                        otrvpath.get_image_path(image_name),
                        self.app.config.get("general", "icon_size"),
                        self.app.config.get("general", "icon_size"),
                    )
                )
            else:
                # Gtk.IconSize.LARGE_TOOLBAR
                # if type(image_name) is list:  # It's a list so we create an emblemed icon
                #     try:
                #         image = Gtk.Image.new_from_gicon(
                #             Gio.EmblemedIcon.new(
                #                 Gio.ThemedIcon.new(image_name[0]), Gio.Emblem.new(Gio.ThemedIcon.new(image_name[1])),
                #             ),
                #             self.app.config.get("general", "icon_size"),
                #         )
                #     except Exception as e:
                #         # Fallback to internal icon
                #         image = Gtk.Image.new_from_pixbuf(
                #             GdkPixbuf.Pixbuf.new_from_file_at_size(
                #                 otrvpath.get_image_path(image_name),
                #                 self.app.config.get("general", "icon_size"),
                #                 self.app.config.get("general", "icon_size"),
                #             )
                #         )
                #         self.log.info(f"Exception: {e}")
                # else:
                try:
                    image = Gtk.Image.new_from_pixbuf(
                        Gtk.IconTheme.get_default().load_icon(
                            image_name, self.app.config.get("general", "icon_size"), 0,
                        )
                    )
                except Exception as e:
                    self.log.info(f"Exception: {e}")

            try:
                image.show()
            except UnboundLocalError:
                # Fallback to internal icon
                index = [i for i, v in enumerate(toolbar_buttons_internal) if v[0] == key]
                image_name_internal = toolbar_buttons_internal[index[0]][1]

                image = Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_size(
                        otrvpath.get_image_path(image_name_internal),
                        self.app.config.get("general", "icon_size"),
                        self.app.config.get("general", "icon_size"),
                    )
                )
                image.show()

            if key == "cut" or key == "decodeandcut":
                self.__toolbar_buttons[key] = Gtk.MenuToolButton.new(image, text)
                self.__toolbar_buttons[key].set_menu(self.__get_cut_menu(action))
            else:
                self.__toolbar_buttons[key] = Gtk.ToolButton.new(image, text)

            self.__toolbar_buttons[key].connect("clicked", self._on_toolbutton_clicked, action)
            self.__toolbar_buttons[key].show()

        self.__sets_of_toolbars = {
            # ~ Section.PLANNING: ['plan_add', 'plan_edit', 'plan_remove', 'plan_search'],
            # ~ Section.DOWNLOAD: ['download_add_link', 'download_start', 'download_stop','download_remove'],
            Section.OTRKEY: ["decodeandcut", "decode", "delete", "real_delete"],
            Section.VIDEO_UNCUT: ["cut", "delete", "real_delete", "archive"],
            Section.VIDEO_CUT: ["archive", "delete", "real_delete", "cut", "rename"],
            Section.ARCHIVE: ["delete", "real_delete", "rename", "new_folder"],
            Section.TRASH: ["real_delete", "restore"],
            Section.TRASH_AVI: ["real_delete", "restore"],
            Section.TRASH_CUTLIST: ["real_delete", "restore"],
            Section.TRASH_OTRKEY: ["real_delete", "restore"],
        }
        if self.app.config.get("general", "hide_archive_buttons"):
            for section, buttons in self.__sets_of_toolbars.items():
                if "archive" in buttons:
                    buttons.remove("archive")
                    self.__sets_of_toolbars[section] = buttons

        # create sets of toolbuttons
        for section, button_names in self.__sets_of_toolbars.items():
            toolbar_buttons = []
            for button_name in button_names:
                toolbar_buttons.append(self.__toolbar_buttons[button_name])

            self.__sets_of_toolbars[section] = toolbar_buttons

        # toolbar_search
        self.search_tool_item = EntrySearchToolItem("Durchsuchen")
        self.search_tool_item.entry.set_can_focus(True)
        self.builder.get_object("toolbar_search").insert(self.search_tool_item, -1)
        self.search_tool_item.connect("search", lambda w, search: self.do_search(search))
        self.search_tool_item.connect("clear", self.on_search_clear)

    def add_toolbutton(self, image, text, sections):
        """ Fügt einen neuen Toolbutton hinzu.
              image ein gtk.Image()
              text Text des Toolbuttons
              sections Liste von Sections, in denen der Toolbutton angezeigt wird.
          """
        image.show()
        toolbutton = Gtk.ToolButton.new(image, text)
        toolbutton.show()

        for section in sections:
            self.__sets_of_toolbars[section].append(toolbutton)

        self.set_toolbar(self.app.section)
        return toolbutton

    def remove_toolbutton(self, toolbutton):
        """ Entfernt den angegebenen toolbutton. """
        for section in self.__sets_of_toolbars.keys():
            if toolbutton in self.__sets_of_toolbars[section]:
                self.__sets_of_toolbars[section].remove(toolbutton)

        self.set_toolbar(self.app.section)

    def __setup_treeview_planning(self):
        treeview = self.builder.get_object("treeview_planning")

        model = Gtk.ListStore(object)
        treeview.set_model(model)

        # allow multiple selection
        treeselection = treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)

        # sorting
        treeview.get_model().set_sort_func(0, self.__tv_planning_sort, None)
        treeview.get_model().set_sort_column_id(0, Gtk.SortType.ASCENDING)

        column, renderer = (
            self.builder.get_object("treeviewcolumn_broadcasttitle"),
            self.builder.get_object("cellrenderer_broadcasttitle"),
        )
        column.set_cell_data_func(renderer, self.__treeview_planning_title)
        column, renderer = (
            self.builder.get_object("treeviewcolumn_broadcastdatetime"),
            self.builder.get_object("cellrenderer_broadcastdatetime"),
        )
        column.set_cell_data_func(renderer, self.__treeview_planning_datetime)
        column, renderer = (
            self.builder.get_object("treeviewcolumn_broadcaststation"),
            self.builder.get_object("cellrenderer_broadcaststation"),
        )
        column.set_cell_data_func(renderer, self.__treeview_planning_station)

    def __setup_treeview_download(self):
        self.treeview_download = DownloadsTreeView()
        self.treeview_download.connect("row-activated", self.on_treeview_download_row_activated)
        self.treeview_download.show()
        self.builder.get_object("scrolledwindow_download").add(self.treeview_download)

        treeselection = self.treeview_download.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)

    def __setup_treeview_files(self):
        treeview = self.builder.get_object("treeview_files")
        treeview.connect("button_press_event", self._on_treeview_context_menu)
        treeview.connect("popup-menu", self._on_treeview_context_menu)
        treeview.connect("row-activated", self._on_treeview_files_row_activated)
        # TreeStore fields: filename, recording_date, size, date_modified, isdir, unlocked
        store = Gtk.TreeStore(str, str, float, float, bool, bool)  # gcurse:LOCK
        treeview.set_model(store)

        # constants for model and columns
        self.__FILENAME = 0
        self.__REC_DATE = 1
        self.__SIZE = 2
        self.__DATE = 3
        self.__ISDIR = 4
        self.__LOCKED = 5  # gcurse:LOCK

        # create the TreeViewColumns to display the data
        column_names = ["Dateiname", "Aufnahmedatum", "Größe", "Geändert"]
        tvcolumns = [None] * len(column_names)

        # pixbuf and filename
        cell_renderer_pixbuf = Gtk.CellRendererPixbuf()
        tvcolumns[self.__FILENAME] = Gtk.TreeViewColumn(column_names[self.__FILENAME], cell_renderer_pixbuf)
        cell_renderer_text_name = Gtk.CellRendererText()
        tvcolumns[self.__FILENAME].pack_start(cell_renderer_text_name, False)
        tvcolumns[self.__FILENAME].set_cell_data_func(cell_renderer_pixbuf, self.__tv_files_pixbuf)
        tvcolumns[self.__FILENAME].set_cell_data_func(cell_renderer_text_name, self.__tv_files_name)

        # recording date
        cell_renderer_text_record = Gtk.CellRendererText()
        tvcolumns[self.__REC_DATE] = Gtk.TreeViewColumn(column_names[self.__REC_DATE], cell_renderer_text_record)
        tvcolumns[self.__REC_DATE].set_cell_data_func(cell_renderer_text_record, self.__tv_files_record)

        # size
        cell_renderer_text_size = Gtk.CellRendererText()
        cell_renderer_text_size.set_property("xalign", 1.0)
        tvcolumns[self.__SIZE] = Gtk.TreeViewColumn(column_names[self.__SIZE], cell_renderer_text_size)
        tvcolumns[self.__SIZE].set_cell_data_func(cell_renderer_text_size, self.__tv_files_size)

        # date
        cell_renderer_text_date = Gtk.CellRendererText()
        tvcolumns[self.__DATE] = Gtk.TreeViewColumn(column_names[self.__DATE], cell_renderer_text_date)
        tvcolumns[self.__DATE].set_cell_data_func(cell_renderer_text_date, self.__tv_files_date)

        # append the columns
        for col in tvcolumns:
            col.set_resizable(True)
            treeview.append_column(col)

        # allow multiple selection
        treeselection = treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)
        treeselection.set_select_function(self.__treeview_files_select_function)  # gcurse:LOCK

        # sorting
        treeview.get_model().set_sort_func(0, self.__tv_files_sort)
        tvcolumns[self.__FILENAME].set_sort_column_id(0)
        tvcolumns[self.__REC_DATE].set_sort_column_id(1)
        tvcolumns[self.__SIZE].set_sort_column_id(2)
        tvcolumns[self.__DATE].set_sort_column_id(3)

        # load pixbufs for treeview
        if self.app.config.get("general", "use_internal_icons"):
            self.__pix_avi = GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path("avi.png"))
            self.__pix_otrkey = GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path("decode.png"))
            self.__pix_folder = GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path("folder.png"))
        else:
            try:
                self.__pix_avi = Gtk.IconTheme.get_default().load_icon(
                    "video-x-generic", self.app.config.get("general", "icon_size"), 0
                )
                self.__pix_otrkey = Gtk.IconTheme.get_default().load_icon(
                    "dialog-password", self.app.config.get("general", "icon_size"), 0
                )
                self.__pix_folder = Gtk.IconTheme.get_default().load_icon(
                    "folder", self.app.config.get("general", "icon_size"), 0
                )
            except Exception as e:
                self.log.debug(f"{e}")

        # gcurse:LOCK cellrenderer's property "sensitive" is set to the value of the model column "unlocked"
        treeview.get_column(0).add_attribute(cell_renderer_text_name, "sensitive", self.__LOCKED)
        treeview.get_column(1).add_attribute(cell_renderer_text_record, "sensitive", self.__LOCKED)
        treeview.get_column(2).add_attribute(cell_renderer_text_size, "sensitive", self.__LOCKED)
        treeview.get_column(3).add_attribute(cell_renderer_text_date, "sensitive", self.__LOCKED)
        treeview.props.enable_search = False

        self.treeview_files = treeview

    def __treeview_files_select_function(self, treeselection, model, path, current):
        return model[path][self.__LOCKED]

    def __setup_widgets(self):
        self.builder.get_object("menu_bottom").set_active(self.app.config.get("general", "show_bottom"))

        self.builder.get_object("image_status").clear()

        # sidebar ##
        self.sidebar = Sidebar()

        # ~ planned = self.sidebar.add_element(Section.PLANNING, '', False)  # TAG:Geplante Sendungen
        # ~ planned.set_sensitive(False)  # TAG:Geplante Sendungen
        # ~ download = self.sidebar.add_element(Section.DOWNLOAD, '', False)
        # ~ download.set_sensitive(False)
        self.sidebar.add_section("OTRKEYS")
        self.sidebar.add_element(Section.OTRKEY, "Nicht dekodiert")

        self.sidebar.add_section("VIDEOS")
        self.sidebar.add_element(Section.VIDEO_UNCUT, "Ungeschnitten")
        self.sidebar.add_element(Section.VIDEO_CUT, "Geschnitten")
        self.sidebar.add_element(Section.ARCHIVE, "Archiv")

        self.sidebar.add_section("PAPIERKORB")
        self.sidebar.add_element(Section.TRASH, "Alles")
        self.sidebar.add_element(Section.TRASH_AVI, "Avi", True, 10)
        self.sidebar.add_element(Section.TRASH_CUTLIST, "Cutlist", True, 10)
        self.sidebar.add_element(Section.TRASH_OTRKEY, "Otrkey", True, 10)

        self.builder.get_object("hbox_main").pack_start(self.sidebar, expand=False, fill=False, padding=0)
        self.builder.get_object("hbox_main").reorder_child(self.sidebar, 0)

        self.sidebar.connect("element-clicked", self._on_sidebar_toggled)
        self.sidebar.set_active(Section.VIDEO_UNCUT)

        # add planning badge
        self.eventbox_planning = Gtk.EventBox()
        self.label_planning_current = Gtk.Label()

        self.eventbox_planning.add(self.label_planning_current)
        self.eventbox_planning.set_size_request(30, 15)

        # style = self.eventbox_planning.get_style().copy()
        # pixmap, mask = GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path('badge.png')).render_pixmap_and_mask()
        # style.bg_pixmap[Gtk.StateFlags.NORMAL] = pixmap
        # self.eventbox_planning.shape_combine_mask(mask, 0, 0)
        # self.eventbox_planning.set_style(style)
        # ~ planned.add_widget(self.eventbox_planning)  # TAG:Geplante Sendungen

        self.sidebar.show_all()
        self.sidebar.set_size_request(
            int(self.sidebar.size_request().width * 1.05), int(self.sidebar.size_request().height * 1.0),
        )
        # sidebar end ##

        # change background of conclusion button
        conclusion_button = self.builder.get_object("button_show_conclusion")
        # https://stackoverflow.com/q/11927785
        # conclusion_eventbox = self.builder.get_object("box_conclusion")
        # eventbox = self.builder.get_object("box_conclusion")
        conclusion_button.get_style_context().add_provider(self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # cmap = eventbox.get_colormap()
        # colour = cmap.alloc_color("#E8E7B6")
        conclusion_button.get_style_context().add_class("conclusion")
        # style = eventbox.get_style().copy()
        # Soft blinking
        # style.bg[Gtk.StateFlags.NORMAL] = colour
        GLib.timeout_add(2500, self._css_callback, conclusion_button)
        # eventbox.set_style(style)

    @staticmethod
    def _css_callback(widget):
        if widget.get_style_context().has_class("conclusion"):
            widget.get_style_context().remove_class("conclusion")
            widget.get_style_context().add_class("conclusion2")
        else:
            widget.get_style_context().remove_class("conclusion2")
            widget.get_style_context().add_class("conclusion")

        return True

    # treeview_files

    def treeview_files_grab(self):
        # Set focus on treeview
        self.treeview_files.grab_focus()
        # self.treeview_files.get_selection().select_path(Gtk.TreePath.new_first())
        sort_column = 1 if self.app.config.get("general", "sort_record_date") else 0
        self.treeview_files.get_model().set_sort_column_id(sort_column, Gtk.SortType.ASCENDING)

    def clear_files(self):
        """ Entfernt alle Einträge aus den Treeviews treeview_files."""
        self.treeview_files.get_model().clear()

    def show_treeview(self, visible_treeview):
        for treeview in [
            "scrolledwindow_planning",
            "scrolledwindow_download",
            "scrolledwindow_files",
        ]:
            self.builder.get_object(treeview).props.visible = treeview == visible_treeview

    def get_selected_filenames(self):
        """ Returns the selected filenames. """
        model, selected_rows = self.treeview_files.get_selection().get_selected_rows()

        return [model.get_value(model.get_iter(row), self.__FILENAME) for row in selected_rows]

    def append_row_files(self, parent, filename, rec_date, size, date, isdir=False, unlocked=True):
        """ Fügt eine neue Datei zu treeview_files hinzu.
            * parent            For 'Archiv': the folder's parent iter, else None
            * filename          Filename
            * record_datetime   Recording date and time taken from filename (for sorting)
            * size              Filesize in bytes
            * date              File modified date and time
            * isdir             if it is a directory
            * locked            if the file (row) is in processing  # gcurse:LOCK
        """

        data = [
            filename,
            rec_date,
            size,
            date,
            isdir,
            unlocked,
        ]  # gcurse:LOCK add column "unlocked"

        iter_files = self.treeview_files.get_model().append(parent, data)
        return iter_files

    @staticmethod
    def humanize_size(bytz):
        bytz = float(bytz)
        if bytz >= 1099511627776:
            terabytes = bytz / 1099511627776
            size = f"{terabytes}.1f T"
        elif bytz >= 1073741824:
            gigabytes = bytz / 1073741824
            size = f"{gigabytes:.1f} GB"
        elif bytz >= 1048576:
            megabytes = bytz / 1048576
            size = f"{megabytes:.1f} MB"
        elif bytz >= 1024:
            kilobytes = bytz / 1024
            size = f"{kilobytes:.1f} K"
        else:
            size = f"{bytz:.1f} b"
        return size

    def __tv_files_sort(self, model, iter1, iter2, data=None):
        # -1 if the iter1 row should precede the iter2 row; 0, if the rows are equal;
        # and, 1 if the iter2 row should precede the iter1 row

        filename_iter1 = model.get_value(iter1, self.__FILENAME)
        filename_iter2 = model.get_value(iter2, self.__FILENAME)

        # why?
        if filename_iter2 is None:
            return -1

        iter1_isdir = model.get_value(iter1, self.__ISDIR)
        iter2_isdir = model.get_value(iter2, self.__ISDIR)

        if (iter1_isdir and iter2_isdir) or (not iter1_isdir and not iter2_isdir):
            # both are folders OR none of them is a folder
            # put names into array and sort them
            folders = [filename_iter1, filename_iter2]
            folders.sort()

            # check if the first element is still iter1
            if folders[0] == filename_iter1:
                return -1
            else:
                return 1

        elif iter1_isdir:  # iter1 is a folder
            return -1
        else:  # iter2 is a folder
            return 1

            # displaying methods for treeview_files

    def __tv_files_size(self, column, cell, model, iter1, data=None):
        if model.get_value(iter1, self.__ISDIR):
            cell.set_property("text", "")
        else:
            cell.set_property("text", self.humanize_size(model.get_value(iter1, self.__SIZE)))

    def __tv_files_date(self, column, cell, model, iter1, data=None):
        cell.set_property(
            "text", time.strftime("%d.%m.%Y, %H:%M", time.localtime(model.get_value(iter1, self.__DATE))),
        )

    def __tv_files_name(self, column, cell, model, iter1, data=None):
        cell.set_property("text", basename(model.get_value(iter1, self.__FILENAME)))

    def __tv_files_record(self, column, cell, model, iter1, data=None):
        cell.set_property("text", model.get_value(iter1, self.__REC_DATE))

    def __tv_files_pixbuf(self, column, cell, model, iter1, data=None):
        filename = model.get_value(iter1, self.__FILENAME)

        if model.get_value(iter1, self.__ISDIR):
            cell.set_property("pixbuf", self.__pix_folder)
        else:
            if filename.endswith(".otrkey"):
                cell.set_property("pixbuf", self.__pix_otrkey)
            else:
                cell.set_property("pixbuf", self.__pix_avi)

    #
    # treeview_planning
    #

    @staticmethod
    def __treeview_planning_title(column, cell, model, iter1, data=None):
        broadcast = model.get_value(iter1, 0)

        if broadcast.datetime < time.time():
            cell.set_property("markup", f"<b>{broadcast.title}</b>")
        else:
            cell.set_property("markup", broadcast.title)

    @staticmethod
    def __treeview_planning_datetime(column, cell, model, iter1, data=None):
        broadcast = model.get_value(iter1, 0)
        date_time = time.strftime("%a, %d.%m.%Y, %H:%M", time.localtime(broadcast.datetime))

        if broadcast.datetime < time.time():
            cell.set_property("markup", f"<b>{date_time}</b>")
        else:
            cell.set_property("markup", date_time)

    @staticmethod
    def __treeview_planning_station(column, cell, model, iter1, data=None):
        broadcast = model.get_value(iter1, 0)

        if broadcast.datetime < time.time():
            cell.set_property("markup", f"<b>{broadcast.station}</b>")
        else:
            cell.set_property("markup", broadcast.station)

    def append_row_planning(self, broadcast):
        """ Fügt eine geplante Sendung zu treeview_planning hinzu.
             broadcast Instanz von planning.PlanningItem """

        iter1 = self.builder.get_object("treeview_planning").get_model().append([broadcast])
        return iter1

    @staticmethod
    def __tv_planning_sort(model, iter1, iter2, data):
        """ -1 if the iter1 row should precede the iter2 row; 0, if the rows are equal;
            and 1 if the iter2 row should precede the iter1 row """
        time1 = model.get_value(iter1, 0).datetime
        time2 = model.get_value(iter2, 0).datetime

        if time1 > time2:
            return 1
        elif time1 < time2:
            return -1
        else:
            return 0

    # Convenience

    def set_toolbar(self, section):
        """ Fügt die entsprechenden Toolbuttons in die Toolbar ein.
              section """

        for toolbutton in self.builder.get_object("toolbar").get_children():
            self.builder.get_object("toolbar").remove(toolbutton)

        for toolbutton in self.__sets_of_toolbars[section]:
            self.builder.get_object("toolbar").insert(toolbutton, -1)

    def block_gui(self, state):
        for button in ["decode", "cut", "decodeandcut"]:
            self.__toolbar_buttons[button].set_sensitive(not state)

    def on_button_show_conclusion_clicked(self, widget, data=None):
        self.get_window().set_cursor(self.app.gui.cursor_wait)
        self.app.conclusions_manager.show_conclusions()
        self.app.show_section(self.app.section)

    def broadcasts_badge(self):
        count = 0
        now = time.time()
        for broadcast in self.app.planned_broadcasts:
            if broadcast.datetime < now:
                count += 1

        if count == 0:
            self.eventbox_planning.hide()
        else:
            self.eventbox_planning.show()
            self.label_planning_current.set_markup(f"<b>{count:d}</b>")

    def change_status(self, message_type, message, permanent=False):
        """ Zeigt ein Bild und einen Text in der Statusleiste an.
              message_type 0 = Information-Icon, -1  = kein Icon
              message Anzuzeigender Text
              permanent: wenn e False, verschwindet die Nachricht nach 10s wieder."""

        self.builder.get_object("label_statusbar").set_text(message)
        if message_type == 0:
            self.builder.get_object("image_status").set_from_file(otrvpath.get_image_path("information.png"))
        if not permanent:

            def wait():
                yield 0  # fake generator
                time.sleep(10)

            def completed():
                self.builder.get_object("label_statusbar").set_text("")
                self.builder.get_object("image_status").clear()

            GeneratorTask(wait, None, completed).start()

    def set_tasks_visible(self, visible):
        """ Zeigt/Versteckt einen Text und einen Fortschrittsbalken, um Aufgaben auszuführen. """
        if visible:
            self.builder.get_object("box_tasks").show()
        else:
            self.builder.get_object("box_tasks").hide()
        self.builder.get_object("label_tasks").set_markup("")
        self.builder.get_object("progressbar_tasks").set_fraction(0)

    def set_tasks_text(self, text):
        """ Zeigt den angegebenen Text im Aufgabenfenster an. """
        self.builder.get_object("label_tasks").set_markup(f"<b>{text}</b>")

    def set_tasks_progress(self, progress):
        """ Setzt den Fortschrittsbalken auf die angegebene %-Zahl. """
        self.builder.get_object("progressbar_tasks").set_fraction(progress / 100.0)

    #  Signal handlers

    def _on_treeview_files_row_activated(self, treeview, tree_path, column, data=None):
        if self.app.section == Section.OTRKEY:
            self.app.perform_action(Action.DECODE)
        elif self.app.section == Section.VIDEO_UNCUT:
            self.app.perform_action(Action.CUT)
        elif self.app.section == Section.VIDEO_CUT:
            self._cmenu_play_file()
        elif self.app.section in [
            Section.TRASH,
            Section.TRASH_AVI,
            Section.TRASH_OTRKEY,
        ]:
            self.app.perform_action(Action.RESTORE)

    def _on_treeview_context_menu(self, treeview, event=None, *args):
        if event:
            if event.type == Gdk.EventType.BUTTON_PRESS and event.button is Gdk.BUTTON_SECONDARY:  # right-click
                treeview_files_selection = treeview.get_selection()
                # Select row if no row is selected or only one other row is selected
                if treeview_files_selection.count_selected_rows() <= 1:
                    tree_path = treeview.get_path_at_pos(event.x, event.y)[0]
                    treeview_files_selection.unselect_all()
                    treeview_files_selection.select_path(tree_path)
                    self._contextmenu_treeview_files()
                    return True
        else:
            self._contextmenu_treeview_files()
            return True

    def _contextmenu_treeview_files(self, *args):
        menu = self._cmenu_build()
        if menu is not None:
            menu.show_all()
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def _cmenu_build(self):
        menu = None
        selected_files = self.get_selected_filenames()
        multiple = True if len(selected_files) > 1 else False
        if not multiple:
            try:
                if "otrkey" not in selected_files[0]:
                    menu = Gtk.Menu()
                    if self.app.section == Section.VIDEO_UNCUT:
                        m_cut_manually = Gtk.MenuItem("Manuell Schneiden")
                        menu.append(m_cut_manually)
                        m_cut_manually.connect("activate", self._cmenu_cut_manually)

                        m_cut = Gtk.MenuItem("Schneiden - Standard")
                        menu.append(m_cut)
                        m_cut.connect("activate", self._cmenu_cut)
                    m_play = Gtk.MenuItem("Abspielen")
                    menu.append(m_play)
                    m_play.connect("activate", self._cmenu_play_file)
            except IndexError:
                pass
        return menu

    def _cmenu_play_file(self, *args):
        fname = self.get_selected_filenames()[0]
        self.app.play_file(fname)

    def _cmenu_cut(self, *args):
        self.app.perform_action(Action.CUT)

    def _cmenu_cut_manually(self, *args):
        self.app.perform_action(Action.CUT, cut_action=CutAction.MANUALLY)

    def on_treeview_download_row_activated(self, treeview, path, view_colum, data=None):
        iter1 = treeview.get_model().get_iter(path)
        download = treeview.get_model().get_value(iter1, 0)
        dialog = DownloadPropertiesDialog.new()
        dialog.run(download)
        if dialog.changed:
            download.stop()
            if self.app.gui.question_box("Soll der Download wieder gestartet werden?"):
                download.start()
        dialog.destroy()

    def _on_menu_check_update_activate(self, widget, data=None):
        pass
        # ~ current_version = open(otrvpath.getdatapath("VERSION"), 'r').read().strip()
        # try:
        #     svn_version = urlopen(self.svn_version_url).read().strip().decode('utf-8')
        # except IOError:
        #     self.app.gui.message_error_box("Konnte keine Verbindung mit dem Internet herstellen!")
        #     return
        # self.app.gui.message_info_box(
        #     f"Ihre Version ist:\n{current_version}\n\nAktuelle Version ist:\n{svn_version}")

    @staticmethod
    def _on_menu_help_help_activate(widget, data=None):
        webbrowser.open("https://github.com/EinApfelBaum/otr-verwaltung3p/wiki")

    def _on_menu_help_about_activate(self, widget, data=None):
        try:
            version = open(otrvpath.getdatapath("VERSION-git"), "r").read().strip()
        except FileNotFoundError:
            version = open(otrvpath.getdatapath("VERSION"), "r").read().strip()
        # script_root_dir = os.path.abspath(os.path.realpath(sys.argv[0]) + "/../..")
        authors = [
            "EinApfelBaum https://github.com/EinApfelBaum",
            "gCurse https://github.com/gCurse",
            "binsky08 https://github.com/binsky08",
            "Mainboand https://github.com/Mainboand",
            "",
            "Predecessors:",
            "otr-verwaltung++ (2012-):",
            "monarc99 https://github.com/monarc99",
            "JanS",
            "",
            "otr-verwaltung (-2010):",
            "B. Elbers",
        ]

        license_ = "GPL version 3, see http://www.gnu.org/licenses/gpl-3.0.html#content"

        about_dialog = Gtk.AboutDialog(
            parent=self.app.gui.main_window,
            program_name=self.app.app_name,
            version=version,
            copyright="\xa9 2010 - " + str(datetime.datetime.now().year) + " B. Elbers and others",
            license=license_,
            website="https://github.com/EinApfelBaum/otr-verwaltung3p/wiki",
            comments="Verwalten und Schneiden der Dateien von onlinetvrecorder.com",
            authors=authors,
            logo=GdkPixbuf.Pixbuf.new_from_file(otrvpath.get_image_path("icon.png")),
        )

        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_size_request(500, 300)
        about_dialog.run()
        about_dialog.destroy()

    def _on_menu_edit_plugins_activate(self, widget, data=None):
        self.app.gui.dialog_plugins.run_()

    def _on_menu_edit_preferences_activate(self, widget, data=None):
        self.app.gui.preferences_window.show()

    def _on_main_window_configure_event(self, widget, event, data=None):
        self.size = self.get_size()

    def _on_main_window_window_state_event(self, widget, event, data=None):
        state = event.new_window_state
        if state & Gdk.WindowState.MAXIMIZED:
            self.maximized = True
        else:
            self.maximized = False

    @staticmethod
    def _on_main_window_destroy(widget, data=None):
        Gtk.main_quit()

    def _on_main_window_delete_event(self, widget, data=None):
        if self.app.locked:
            if not self.app.gui.question_box(
                "Das Programm arbeitet noch. \
                                          Soll wirklich abgebrochen werden?"
            ):
                return True  # won't be destroyed

        for row in self.treeview_download.liststore:
            if row[0].information["status"] in [
                DownloadStatus.RUNNING,
                DownloadStatus.SEEDING,
            ]:
                if not self.app.gui.question_box(
                    "Es gibt noch laufende Downloads. \
                                              Soll wirklich abgebrochen werden?"
                ):
                    return True  # won't be destroyed
                break

        return False

    @staticmethod
    def _on_menu_file_quit_activate(*args):
        Gtk.main_quit()

    def _on_menu_edit_search_activate(self, widget, data=None):
        self.search_tool_item.entry.grab_focus()

    def _on_menu_bottom_toggled(self, widget, data=None):
        self.app.config.set("general", "show_bottom", widget.get_active())
        self.builder.get_object("box_bottom").props.visible = widget.get_active()

    # toolbar actions
    def _on_toolbutton_clicked(self, button, action, cut_action=None):
        self.app.perform_action(action, cut_action)

    # sidebar
    def _on_sidebar_toggled(self, widget, section):
        self.app.show_section(section)

        if section == Section.PLANNING:
            # select already broadcasted
            selection = self.builder.get_object("treeview_planning").get_selection()
            selection.unselect_all()
            now = time.time()

            for row in self.builder.get_object("treeview_planning").get_model():
                if row[0].datetime < now:
                    selection.select_iter(row.iter)

    def _on_window_key_press_event(self, widget, event, *args):
        """ Ctrl-f will focus the search entry """
        keyname = Gdk.keyval_name(event.keyval).upper()
        mod_ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        mod_shift = event.state & Gdk.ModifierType.SHIFT_MASK
        mod_alt = event.state & Gdk.ModifierType.MOD1_MASK

        if event.type == Gdk.EventType.KEY_PRESS:
            if not mod_shift and not mod_alt and mod_ctrl:  # CTRL
                if keyname == "F":
                    if not self.search_tool_item.entry.has_focus():
                        self.search_tool_item.entry.grab_focus()
        return False

    def do_search(self, search):
        if not search:
            return

        counts_of_section = self.app.start_search(search)
        self.sidebar.set_search(counts_of_section)

    def on_search_clear(self, widget):
        self.app.stop_search()
        self.sidebar.set_search(None)

    # bottom
    def on_notebook_bottom_page_added(self, notebook, child, page_num, data=None):
        self.builder.get_object("menu_bottom").set_sensitive(True)

    def on_notebook_bottom_page_removed(self, notebook, child, page_num, data=None):
        self.builder.get_object("menu_bottom").set_sensitive(False)
        self.builder.get_object("menu_bottom").set_active(False)


def new(app):
    logger = logging.getLogger(__name__)
    glade_filename = otrvpath.getdatapath("ui", "MainWindow.glade")
    version = open(otrvpath.getdatapath("VERSION"), "r").read().strip()
    logger.info("Version: " + version)

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    window = builder.get_object("main_window")

    window.app = app
    # window.gui = gui
    return window
