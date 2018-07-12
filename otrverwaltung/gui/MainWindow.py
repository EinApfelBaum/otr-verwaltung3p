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

from os.path import basename

import time
# ~ import urllib.request
from urllib.request import Request, urlopen
import webbrowser
import git
import sys, os, datetime, logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, Gdk, Gio

from otrverwaltung import path
from otrverwaltung.constants import Action, Section, Cut_action, DownloadStatus
from otrverwaltung.gui.widgets.DownloadsTreeView import DownloadsTreeView
from otrverwaltung.gui.widgets.Sidebar import Sidebar
from otrverwaltung.gui.widgets.EntrySearchToolItem import EntrySearchToolItem
from otrverwaltung.gui import DownloadPropertiesDialog
from otrverwaltung.GeneratorTask import GeneratorTask


class MainWindow(Gtk.Window, Gtk.Buildable):
    __gtype_name__ = "MainWindow"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.svn_version_url = ''

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

    def pre_init(self):
        pass

    # TODO: only workaround. try to remove.
    def post_init(self):
        self.__setup_toolbar()
        self.__setup_treeview_planning()
        self.__setup_treeview_download()
        self.__setup_treeview_files()
        self.__setup_widgets()

        # set window title
        current_version = open(path.getdatapath("VERSION"), 'r').read().strip()
        self.svn_version_url = "https://raw.githubusercontent.com/einapfelbaum/otr-verwaltung3p/master/data/VERSION"

        try:
           svn_version = urlopen(self.svn_version_url).read().strip().decode('utf-8')
        except IOError:
           self.set_title('OTR-Verwaltung3p' + ' ' + current_version)
        else:
            if current_version in str(svn_version):
                self.set_title('OTR-Verwaltung3p' + ' ' + current_version + '  -  Aktuell!')
            else:
                self.set_title('OTR-Verwaltung3p' + ' ' + current_version + '  -  aktuelle Version: ' + str(svn_version))
                self._on_menu_check_update_activate(self)

        # ~ self.treeview_files = self.builder.get_object('treeview_files')

    def __get_cut_menu(self, action):
        # menu for cut/decodeandcut
        cut_menu = Gtk.Menu()
        items = [
            ("Nachfragen", Cut_action.ASK),
            ("Beste Cutlist", Cut_action.BEST_CUTLIST),
            ("Cutlist wählen", Cut_action.CHOOSE_CUTLIST),
            ("Lokale Cutlist", Cut_action.LOCAL_CUTLIST),
            ("Manuell (und Cutlist erstellen)", Cut_action.MANUALLY)
        ]

        for label, cut_action in items:
            item = Gtk.MenuItem(label)
            item.show()
            item.connect("activate", self._on_toolbutton_clicked, action, cut_action)
            cut_menu.add(item)

        return cut_menu

    def __setup_toolbar(self):

        # ~ toolbar_buttons = [
            # ~ ('decodeandcut', 'decodeandcut.png', "Dekodieren und Schneiden", Action.DECODEANDCUT),
            # ~ ('decode', 'decode.png', 'Dekodieren', Action.DECODE),
            # ~ ('delete', 'bin.png', "In den Müll verschieben", Action.DELETE),
            # ~ ('archive', 'archive.png', "Archivieren", Action.ARCHIVE),
            # ~ ('cut', 'cut.png', "Schneiden", Action.CUT),
            # ~ ('restore', 'restore.png', "Wiederherstellen", Action.RESTORE),
            # ~ ('rename', 'rename.png', "Umbenennen", Action.RENAME),
            # ~ ('new_folder', 'new_folder.png', "Neuer Ordner", Action.NEW_FOLDER),
            # ~ ('real_delete', 'delete.png', "Löschen", Action.REAL_DELETE),
            # ~ ('plan_add', 'film_add.png', "Hinzufügen", Action.PLAN_ADD),
            # ~ ('plan_remove', 'film_delete.png', "Löschen", Action.PLAN_REMOVE),
            # ~ ('plan_edit', 'film_edit.png', "Bearbeiten", Action.PLAN_EDIT),
            # ~ ('plan_search', 'film_search.png', "Auf Mirror suchen", Action.PLAN_SEARCH),
            # ~ ('download_add', 'add_download.png', "Download hinzufügen", Action.DOWNLOAD_ADD),
            # ~ ('download_add_link', 'add_download.png', "Link hinzufügen", Action.DOWNLOAD_ADD_LINK),
            # ~ ('download_start', 'download_start.png', "Start", Action.DOWNLOAD_START),
            # ~ ('download_stop', 'download_stop.png', "Stop", Action.DOWNLOAD_STOP),
            # ~ ('download_remove', 'delete.png', "Löschen", Action.DOWNLOAD_REMOVE),
        # ~ ]
        toolbar_buttons = [
            ('decodeandcut', ['dialog-password', 'edit-cut'],
                                                "Dekodieren und Schneiden", Action.DECODEANDCUT),
            ('decode', 'dialog-password', 'Dekodieren', Action.DECODE),
            ('delete', 'user-trash', "In den Müll verschieben", Action.DELETE),
            ('archive', 'system-file-manager', "Archivieren", Action.ARCHIVE),
            ('cut', 'edit-cut', "Schneiden", Action.CUT),
            ('restore', 'view-refresh', "Wiederherstellen", Action.RESTORE),
            ('rename', 'accessories-text-editor_', "Umbenennen", Action.RENAME),
            ('new_folder', 'folder-new', "Neuer Ordner", Action.NEW_FOLDER),
            ('real_delete', 'edit-del', "Löschen", Action.REAL_DELETE),
        ]

        self.__toolbar_buttons = {}
        for key, image_name, text, action in toolbar_buttons:
            # Gtk.IconSize.LARGE_TOOLBAR
            if type(image_name) == type([]):  # It's a list
                # Create an emblemed icon
                try:
                    image = Gtk.Image.new_from_gicon(Gio.EmblemedIcon.new(
                                                Gio.ThemedIcon.new(image_name[0]),
                                                Gio.Emblem.new(Gio.ThemedIcon.new(image_name[1]))),
                                                24)
                except: pass
            else:
                try:
                    image = Gtk.Image.new_from_pixbuf(Gtk.IconTheme.get_default().load_icon(
                                                                                image_name, 24, 0))
                except: pass
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
            # ~ Section.DOWNLOAD: ['download_add_link', 'download_start', 'download_stop', 'download_remove'],
            Section.OTRKEY: ['decodeandcut', 'decode', 'delete', 'real_delete'],
            Section.VIDEO_UNCUT: ['cut', 'delete', 'real_delete', 'archive'],
            Section.VIDEO_CUT: ['archive', 'delete', 'real_delete', 'cut', 'rename'],
            Section.ARCHIVE: ['delete', 'real_delete', 'rename', 'new_folder'],
            Section.TRASH: ['real_delete', 'restore'],
            Section.TRASH_AVI: ['real_delete', 'restore'],
            Section.TRASH_OTRKEY: ['real_delete', 'restore']
        }

        # create sets of toolbuttons
        for section, button_names in self.__sets_of_toolbars.items():
            toolbar_buttons = []
            for button_name in button_names:
                toolbar_buttons.append(self.__toolbar_buttons[button_name])

            self.__sets_of_toolbars[section] = toolbar_buttons

        # toolbar_search
        self.search_tool_item = EntrySearchToolItem("Durchsuchen")
        self.builder.get_object('toolbar_search').insert(self.search_tool_item, -1)

        self.search_tool_item.connect('search', lambda w, search: self.do_search(search))
        self.search_tool_item.connect('clear', self.on_search_clear)

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
        """ Entfernt den angegebenen toolbutton.
              toolbutton"""

        for section in self.__sets_of_toolbars.keys():
            if toolbutton in self.__sets_of_toolbars[section]:
                self.__sets_of_toolbars[section].remove(toolbutton)

        self.set_toolbar(self.app.section)

    def __setup_treeview_planning(self):
        treeview = self.builder.get_object('treeview_planning')

        model = Gtk.ListStore(object)
        treeview.set_model(model)

        # allow multiple selection
        treeselection = treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)

        # sorting
        treeview.get_model().set_sort_func(0, self.__tv_planning_sort, None)
        treeview.get_model().set_sort_column_id(0, Gtk.SortType.ASCENDING)

        column, renderer = self.builder.get_object('treeviewcolumn_broadcasttitle'), self.builder.get_object(
            'cellrenderer_broadcasttitle')
        column.set_cell_data_func(renderer, self.__treeview_planning_title)
        column, renderer = self.builder.get_object('treeviewcolumn_broadcastdatetime'), self.builder.get_object(
            'cellrenderer_broadcastdatetime')
        column.set_cell_data_func(renderer, self.__treeview_planning_datetime)
        column, renderer = self.builder.get_object('treeviewcolumn_broadcaststation'), self.builder.get_object(
            'cellrenderer_broadcaststation')
        column.set_cell_data_func(renderer, self.__treeview_planning_station)

    def __setup_treeview_download(self):
        self.treeview_download = DownloadsTreeView()
        self.treeview_download.connect('row-activated', self.on_treeview_download_row_activated)
        self.treeview_download.show()
        self.builder.get_object('scrolledwindow_download').add(self.treeview_download)

        treeselection = self.treeview_download.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)

    def __setup_treeview_files(self):
        treeview = self.builder.get_object('treeview_files')
        treeview.connect('button_press_event', self._on_treeview_files_button_pressed)
        store = Gtk.TreeStore(str, float, float, bool)  # filename, size, date, locked
        treeview.set_model(store)

        # constants for model and columns
        self.__FILENAME = 0
        self.__SIZE = 1
        self.__DATE = 2
        self.__ISDIR = 3

        # create the TreeViewColumns to display the data
        column_names = ['Dateiname', 'Größe', 'Geändert']
        tvcolumns = [None] * len(column_names)

        # pixbuf and filename
        cell_renderer_pixbuf = Gtk.CellRendererPixbuf()
        tvcolumns[self.__FILENAME] = Gtk.TreeViewColumn(column_names[self.__FILENAME], cell_renderer_pixbuf)
        cell_renderer_text_name = Gtk.CellRendererText()
        tvcolumns[self.__FILENAME].pack_start(cell_renderer_text_name, False)
        tvcolumns[self.__FILENAME].set_cell_data_func(cell_renderer_pixbuf, self.__tv_files_pixbuf)
        tvcolumns[self.__FILENAME].set_cell_data_func(cell_renderer_text_name, self.__tv_files_name)

        # size
        cell_renderer_text_size = Gtk.CellRendererText()
        cell_renderer_text_size.set_property('xalign', 1.0)
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

        # sorting
        treeview.get_model().set_sort_func(0, self.__tv_files_sort)
        tvcolumns[self.__FILENAME].set_sort_column_id(0)
        tvcolumns[self.__SIZE].set_sort_column_id(1)
        tvcolumns[self.__DATE].set_sort_column_id(2)

        # load pixbufs for treeview
        # ~ self.__pix_avi = GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('avi.png'))
        # ~ self.__pix_otrkey = GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('decode.png'))
        # ~ self.__pix_folder = GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('folder.png'))
        try:
            self.__pix_avi = Gtk.IconTheme.get_default().load_icon('video-x-generic', 16, 0)
            self.__pix_otrkey = Gtk.IconTheme.get_default().load_icon('dialog-password', 16, 0)
            self.__pix_folder = Gtk.IconTheme.get_default().load_icon('folder', 24, 0)
        except: pass

    def __setup_widgets(self):
        self.builder.get_object('menu_bottom').set_active(self.app.config.get('general', 'show_bottom'))

        self.builder.get_object('image_status').clear()

        ## sidebar ##
        self.sidebar = Sidebar()

        # ~ planned = self.sidebar.add_element(Section.PLANNING, '', False)  # TAG:Geplante Sendungen
        # ~ planned.set_sensitive(False)  # TAG:Geplante Sendungen
        # ~ download = self.sidebar.add_element(Section.DOWNLOAD, '', False)
        # ~ download.set_sensitive(False)
        self.sidebar.add_section('OTRKEYS')
        self.sidebar.add_element(Section.OTRKEY, 'Nicht dekodiert')

        self.sidebar.add_section('VIDEOS')
        self.sidebar.add_element(Section.VIDEO_UNCUT, 'Ungeschnitten')
        self.sidebar.add_element(Section.VIDEO_CUT, 'Geschnitten')
        self.sidebar.add_element(Section.ARCHIVE, 'Archiv')

        self.sidebar.add_section('PAPIERKORB')
        self.sidebar.add_element(Section.TRASH, 'Alles')
        self.sidebar.add_element(Section.TRASH_AVI, 'Avi', True, 10)
        self.sidebar.add_element(Section.TRASH_OTRKEY, 'Otrkey', True, 10)

        self.builder.get_object('hbox_main').pack_start(self.sidebar, expand=False, fill=False, padding=0)
        self.builder.get_object('hbox_main').reorder_child(self.sidebar, 0)

        self.sidebar.connect('element-clicked', self._on_sidebar_toggled)
        self.sidebar.set_active(Section.VIDEO_UNCUT)

        # add planning badge
        self.eventbox_planning = Gtk.EventBox()
        self.label_planning_current = Gtk.Label()

        # TODO eventbox
        self.eventbox_planning.add(self.label_planning_current)
        self.eventbox_planning.set_size_request(30, 15)

        style = self.eventbox_planning.get_style().copy()
        # pixmap, mask = GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('badge.png')).render_pixmap_and_mask()
        # style.bg_pixmap[Gtk.StateFlags.NORMAL] = pixmap
        # self.eventbox_planning.shape_combine_mask(mask, 0, 0)
        # self.eventbox_planning.set_style(style)
        # ~ planned.add_widget(self.eventbox_planning)  # TAG:Geplante Sendungen

        self.sidebar.show_all()
        ## sidebar end ##

        # change background of conclusin bar
        # TODO: maybe change background with CssProvider
        # http://stackoverflow.com/questions/11927785/how-to-make-buttons-different-colours-in-python-gtk3-using-gi
        eventbox = self.builder.get_object('box_conclusion')
        # cmap = eventbox.get_colormap()
        # colour = cmap.alloc_color("#E8E7B6")
        # style = eventbox.get_style().copy()
        # style.bg[Gtk.StateFlags.NORMAL] = colour
        # eventbox.set_style(style)

    #
    # treeview_files
    #

    def _on_treeview_files_button_pressed(self, widget, data=None):
        pass

    def treeview_files(self):
        # ~ self.builder.get_object('treeview_files').set_cursor(Gtk.TreePath(0))
        # ~ self.builder.get_object('treeview_files').row_activated(Gtk.TreePath(0), Gtk.TreeViewColumn(None))
        self.builder.get_object('treeview_files').grab_focus()

    def clear_files(self):
        """ Entfernt alle Einträge aus den Treeviews treeview_files."""
        self.builder.get_object('treeview_files').get_model().clear()

    def show_treeview(self, visible_treeview):
        for treeview in ["scrolledwindow_planning", "scrolledwindow_download", "scrolledwindow_files"]:
            self.builder.get_object(treeview).props.visible = (treeview == visible_treeview)

    def get_selected_filenames(self):
        """ Gibt die ausgewählten Dateinamen zurück. """
        model, selected_rows = self.builder.get_object('treeview_files').get_selection().get_selected_rows()

        return [model.get_value(model.get_iter(row), self.__FILENAME) for row in selected_rows]

    def append_row_files(self, parent, filename, size, date, isdir=False):
        """ Fügt eine neue Datei zu treeview_files hinzu.
              parent Für Archiv, ansonsten None: der übergeordnete iter des Ordners
              filename Dateiname
              size Dateigröße in Bytes
              date Änderungsdatum der Datei
              isdir
          """

        data = [filename, size, date, isdir]

        # TODO implement liststore into glade ?
        # http://fo2adzz.blogspot.de/2012/09/gtktreeview-glade-with-python-tutorial.html
        iter = self.builder.get_object('treeview_files').get_model().append(parent, data)
        return iter

    def humanize_size(self, bytes):
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = '%.1f T' % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.1f GB' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.1f MB' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.1f K' % kilobytes
        else:
            size = '%.1f b' % bytes
        return size

    def __tv_files_sort(self, model, iter1, iter2, data=None):
        # -1 if the iter1 row should precede the iter2 row; 0, if the rows are equal; and, 1 if the iter2 row should precede the iter1 row

        filename_iter1 = model.get_value(iter1, self.__FILENAME)
        filename_iter2 = model.get_value(iter2, self.__FILENAME)

        # why?
        if filename_iter2 == None:
            return -1

        iter1_isdir = model.get_value(iter1, self.__ISDIR)
        iter2_isdir = model.get_value(iter2, self.__ISDIR)

        if (iter1_isdir and iter2_isdir) or (
            not iter1_isdir and not iter2_isdir):  # both are folders OR none of them is a folder
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

    def __tv_files_size(self, column, cell, model, iter, data=None):
        if model.get_value(iter, self.__ISDIR):
            cell.set_property('text', "")
        else:
            cell.set_property('text', self.humanize_size(model.get_value(iter, self.__SIZE)))

    def __tv_files_date(self, column, cell, model, iter, data=None):
        cell.set_property('text',
                          time.strftime("%a, %d.%m.%Y, %H:%M", time.localtime(model.get_value(iter, self.__DATE))))

    def __tv_files_name(self, column, cell, model, iter, data=None):
        cell.set_property('text', basename(model.get_value(iter, self.__FILENAME)))

    def __tv_files_pixbuf(self, column, cell, model, iter, data=None):
        filename = model.get_value(iter, self.__FILENAME)

        if model.get_value(iter, self.__ISDIR):
            cell.set_property('pixbuf', self.__pix_folder)
        else:
            if filename.endswith('.otrkey'):
                cell.set_property('pixbuf', self.__pix_otrkey)
            else:
                cell.set_property('pixbuf', self.__pix_avi)

    #
    # treeview_planning
    #

    def __treeview_planning_title(self, column, cell, model, iter, data=None):
        broadcast = model.get_value(iter, 0)

        if broadcast.datetime < time.time():
            cell.set_property('markup', "<b>%s</b>" % broadcast.title)
        else:
            cell.set_property('markup', broadcast.title)

    def __treeview_planning_datetime(self, column, cell, model, iter, data=None):
        broadcast = model.get_value(iter, 0)
        datetime = time.strftime("%a, %d.%m.%Y, %H:%M", time.localtime(broadcast.datetime))

        if broadcast.datetime < time.time():
            cell.set_property('markup', "<b>%s</b>" % datetime)
        else:
            cell.set_property('markup', datetime)

    def __treeview_planning_station(self, column, cell, model, iter, data=None):
        broadcast = model.get_value(iter, 0)

        if broadcast.datetime < time.time():
            cell.set_property('markup', "<b>%s</b>" % broadcast.station)
        else:
            cell.set_property('markup', broadcast.station)

    def append_row_planning(self, broadcast):
        """ Fügt eine geplante Sendung zu treeview_planning hinzu.
             broadcast Instanz von planning.PlanningItem """

        iter = self.builder.get_object('treeview_planning').get_model().append([broadcast])
        return iter

    def __tv_planning_sort(self, model, iter1, iter2, data):
        # -1 if the iter1 row should precede the iter2 row; 0, if the rows are equal; and, 1 if the iter2 row should precede the iter1 row
        time1 = model.get_value(iter1, 0).datetime
        time2 = model.get_value(iter2, 0).datetime

        if time1 > time2:
            return 1
        elif time1 < time2:
            return -1
        else:
            return 0

    #
    # Convenience
    #

    def set_toolbar(self, section):
        """ Fügt die entsprechenden Toolbuttons in die Toolbar ein.
              section """

        for toolbutton in self.builder.get_object('toolbar').get_children():
            self.builder.get_object('toolbar').remove(toolbutton)

        for toolbutton in self.__sets_of_toolbars[section]:
            self.builder.get_object('toolbar').insert(toolbutton, -1)

    def block_gui(self, state):
        for button in ["decode", "cut", "decodeandcut"]:
            self.__toolbar_buttons[button].set_sensitive(not state)

    def on_button_show_conclusion_clicked(self, widget, data=None):
        self.app.conclusions_manager.show_conclusions()
        self.app.show_section(self.app.section)

    def broadcasts_badge(self):
        count = 0
        now = time.time()
        for broadcast in self.app.planned_broadcasts:
            if broadcast.datetime < now:
                count += 1

        if count == 0:
            pass
            self.eventbox_planning.hide()
        else:
            self.eventbox_planning.show()
            self.label_planning_current.set_markup("<b>%i</b>" % count)

    def change_status(self, message_type, message, permanent=False):
        """ Zeigt ein Bild und einen Text in der Statusleiste an.
              message_type 0 = Information-Icon, -1  = kein Icon
              message Anzuzeigender Text
              permanent: wenn \e False, verschwindet die Nachricht nach 10s wieder."""

        self.builder.get_object('label_statusbar').set_text(message)

        if message_type == 0:
            self.builder.get_object('image_status').set_from_file(path.get_image_path("information.png"))

        if not permanent:
            def wait():
                yield 0  # fake generator
                time.sleep(10)

            def completed():
                self.builder.get_object('label_statusbar').set_text("")
                self.builder.get_object('image_status').clear()

            GeneratorTask(wait, None, completed).start()

    def set_tasks_visible(self, visible):
        """ Zeigt/Versteckt einen Text und einen Fortschrittsbalken, um Aufgaben auszuführen. """
        if visible:
            self.builder.get_object('box_tasks').show()
        else:
            self.builder.get_object('box_tasks').hide()
        self.builder.get_object('label_tasks').set_markup("")
        self.builder.get_object('progressbar_tasks').set_fraction(0)

    def set_tasks_text(self, text):
        """ Zeigt den angegebenen Text im Aufgabenfenster an. """
        self.builder.get_object('label_tasks').set_markup("<b>%s</b>" % text)

    def set_tasks_progress(self, progress):
        """ Setzt den Fortschrittsbalken auf die angegebene %-Zahl. """
        self.builder.get_object('progressbar_tasks').set_fraction(progress / 100.)

    #
    #  Signal handlers
    #

    def on_treeview_download_row_activated(self, treeview, path, view_colum, data=None):
        iter = treeview.get_model().get_iter(path)
        download = treeview.get_model().get_value(iter, 0)
        dialog = DownloadPropertiesDialog.NewDownloadPropertiesDialog()
        dialog.run(download)
        if dialog.changed:
            download.stop()
            if self.gui.question_box("Soll der Download wieder gestartet werden?"):
                download.start()
        dialog.destroy()

    def _on_menu_check_update_activate(self, widget, data=None):
        current_version = open(path.getdatapath("VERSION"), 'r').read().strip()

        try:
            svn_version = urlopen(self.svn_version_url).read().strip().decode('utf-8')
        except IOError:
            self.gui.message_error_box("Konnte keine Verbindung mit dem Internet herstellen!")
            return

        if current_version in svn_version:
            self.gui.message_info_box("Ihre Version ist:\n%s\n\nAktuelle Version ist:\n%s" % \
                                                                    (current_version, svn_version))
        else:
            if self.gui.question_box("Ihre Version ist:\n%s\n\nAktuelle Version ist:\n%s\n\n\
                                        Automatisch updaten?\n" % (current_version, svn_version)):
                # TODO: script_root_dir won't work when program is installed?
                #get new version from git
                script_root_dir = os.path.abspath(os.path.realpath(sys.argv[0])+'/../..')
                file = open(script_root_dir+"/.git/config", "r")
                filelist = file.read()
                # check if program is in right repo
                if 'url = https://github.com/EinApfelBaum/otr-verwaltung3p.git' in filelist:
                    g = git.cmd.Git(script_root_dir+'/')
                    self.log.debug(g.checkout('master'))
                    git_pull_output=g.pull()
                    self.log.debug(git_pull_output)
                    if "Already up-to-date" in git_pull_output:
                        self.gui.message_error_box("Es konnten keine Updates gefunden werden.\n\
                                    Bitte starte das Programm neu, damit ein bereits eingespieltes \
                                    Update angewendet werden kann!\n")
                    else:
                        if self.gui.question_box("Die Version wurde auf %s geupdated.\n\nBestätige \
                                    mit 'Ja', damit das Programm neu gestartet wird und das Update \
                                    direkt angewendet werden kann!\n" %
                                        (open(path.getdatapath("VERSION"), 'r').read().strip())):
                            os.execv(sys.executable, ['python'] + sys.argv)
                            sys.exit()

    def _on_menuHelpHelp_activate(self, widget, data=None):
        webbrowser.open("https://github.com/EinApfelBaum/otr-verwaltung3p/wiki")

    def _on_menuHelpAbout_activate(self, widget, data=None):

        version = open(path.getdatapath("VERSION"), 'r').read().strip()
        # TODO: script_root_dir won't work when program is installed?
        script_root_dir = os.path.abspath(os.path.realpath(sys.argv[0])+'/../..')
        with open(os.path.join(script_root_dir, 'AUTHORS'), 'r') as f:
            authors = f.readlines()
        authors = [x.strip() for x in authors]

        with open(os.path.join(script_root_dir, 'LICENSE'), 'r') as f:
            license = f.read()

        about_dialog = Gtk.AboutDialog(parent=self.gui.main_window,
                program_name=self.app.app_name,
                version=version,
                copyright='\xa9 2010 - ' + str(datetime.datetime.now().year) +' B. Elbers and others',
                license=license,
                website='https://github.com/EinApfelBaum/otr-verwaltung3p/wiki',
                comments='Zum Verwalten von Dateien von onlinetvrecorder.com',
                authors=authors,
                logo=GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('icon.png'))
                )
                # ~ title='About {}'.format(self.app.app_name))

        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_size_request(500, 300)
        about_dialog.run()
        about_dialog.destroy()

    def _on_menuEditPlugins_activate(self, widget, data=None):
        self.gui.dialog_plugins._run()

    def _on_menuEditPreferences_activate(self, widget, data=None):
        self.gui.preferences_window.show()

    def _on_main_window_configure_event(self, widget, event, data=None):
        self.size = self.get_size()

    def _on_main_window_window_state_event(self, widget, event, data=None):
        state = event.new_window_state
        if (state & Gdk.WindowState.MAXIMIZED):
            self.maximized = True
        else:
            self.maximized = False

    def _on_main_window_destroy(self, widget, data=None):
        Gtk.main_quit()

    def _on_main_window_delete_event(self, widget, data=None):
        if self.app.locked:
            if not self.gui.question_box("Das Programm arbeitet noch. \
                                          Soll wirklich abgebrochen werden?"):
                return True  # won't be destroyed

        for row in self.treeview_download.liststore:
            if row[0].information['status'] in [DownloadStatus.RUNNING, DownloadStatus.SEEDING]:
                if not self.gui.question_box("Es gibt noch laufende Downloads. \
                                              Soll wirklich abgebrochen werden?"):
                    return True  # won't be destroyed
                break

        return False

    def _on_menuFileQuit_activate(self, widget, data=None):
        Gtk.main_quit()

    def _on_menuEditSearch_activate(self, widget, data=None):
        self.search_tool_item.entry.grab_focus()

    def _on_menu_bottom_toggled(self, widget, data=None):
        self.app.config.set('general', 'show_bottom', widget.get_active())
        self.builder.get_object('box_bottom').props.visible = widget.get_active()

    # toolbar actions
    def _on_toolbutton_clicked(self, button, action, cut_action=None):
        self.app.perform_action(action, cut_action)

    # sidebar
    def _on_sidebar_toggled(self, widget, section):
        self.app.show_section(section)

        if section == Section.PLANNING:
            # select already broadcasted
            selection = self.builder.get_object('treeview_planning').get_selection()
            selection.unselect_all()
            now = time.time()

            for row in self.builder.get_object('treeview_planning').get_model():
                if row[0].datetime < now:
                    selection.select_iter(row.iter)

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
        self.builder.get_object('menu_bottom').set_sensitive(True)

    def on_notebook_bottom_page_removed(self, notebook, child, page_num, data=None):
        self.builder.get_object('menu_bottom').set_sensitive(False)
        self.builder.get_object('menu_bottom').set_active(False)


def NewMainWindow(app, gui):
    logger = logging.getLogger(__name__)
    glade_filename = path.getdatapath('ui', 'MainWindow.glade')
    version = open(path.getdatapath("VERSION"), 'r').read().strip()
    logger.info("Version: " + version)

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    window = builder.get_object("main_window")

    window.app = app
    window.gui = gui
    return window
