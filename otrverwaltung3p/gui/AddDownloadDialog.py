# -*- coding: utf-8 -*-
# BEGIN LICENSE
# This file is in the public domain
# END LICENSE

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

# import base64
# ~ import libtorrent as lt
# import os
# import requests
# import subprocess
# import urllib, urllib2
# import urllib.request as request
import re

from otrverwaltung3p.GeneratorTask import GeneratorTask
from otrverwaltung3p import cutlists
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.scraper import scrape
from otrverwaltung3p.gui.widgets.CutlistsTreeView import CutlistsTreeView


class AddDownloadDialog(Gtk.Dialog, Gtk.Buildable):
    __gtype_name__ = "AddDownloadDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        self.builder, self.cutlists_treeview, self.error = None, None, None
        self.mode = 0
        self.filename = ""

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

        self.cutlists_treeview = CutlistsTreeView()
        self.cutlists_treeview.show()
        self.cutlists_treeview.get_selection().connect("changed", self.treeview_cutlists_selection_changed)
        self.builder.get_object("scrolledwindow_cutlists").add(self.cutlists_treeview)

        animation = GdkPixbuf.PixbufAnimation.new_from_file(otrvpath.get_image_path("spinner.gif"))
        self.builder.get_object("image_spinner").set_from_animation(animation)
        self.builder.get_object("image_spinner_download").set_from_animation(animation)

        selection = self.builder.get_object("treeview_programs").get_selection()
        selection.connect("changed", self.treeview_programs_selection_changed)

    # del_libtorrent ->
    """
    def get_download_options(self):
        if self.builder.get_object('radiobutton_torrent').get_active():
            return 'torrent'
        else:
            link = self.builder.get_object('entry_link').get_text()

            if self.builder.get_object('checkbutton_cut').get_active():
                cutlist_id = self.cutlists_treeview.get_selected().id
                return 'normal', 'decodeandcut', link, cutlist_id

            if self.builder.get_object('checkbutton_decode').get_active():
                return 'normal', 'decode', link

            return 'normal', link

    #
    # SEARCH
    #

    def search(self, text):
        try:
            # html = urllib.urlopen("http://otrkeyfinder.com/?search=%s" % text).read()
            # html = Request.urlopen("http://otrkeyfinder.com/?search=%s" % text).read()
            html = requests.get("http://otrkeyfinder.com/?search=%s" % text)
        except IOError:
            yield 'Verbindungsprobleme'
            return

        results = re.findall(r'title="(([^&]*)_([0-9\.]*)_([0-9-]*)_([^_]*)_([0-9]*)_TVOON_DE.mpg\.'
                             r'(avi|HQ\.avi|HD\.avi|mp4).otrkey)"[^\(]*>\(([0-9]*)\)', html)
        for result in results:
            filename, name, date, time, station, length, format, mirrors = result

            name = name.replace('_', ' ')
            date = "%s.%s.20%s" % tuple(reversed(date.split('.')))
            time = time.replace('-', ':')
            station = station.capitalize()
            length = "%s min" % length

            yield [filename, name, station, date, time, format, length, int(mirrors)]

    def search_callback(self, row):
        model = self.builder.get_object('treeview_programs').get_model()
        if type(row) == str:
            self.error = row
        else:
            model.append(row)

    def search_stop(self):
        model = self.builder.get_object('treeview_programs').get_model()
        self.builder.get_object('scrolledwindow_programs').show()
        self.builder.get_object('vbox_searching').hide()
        self.builder.get_object('button_search').set_sensitive(True)
        if self.error:
            self.builder.get_object('label_status').set_markup("<b>%s</b>" % self.error)
        else:
            if len(model) == 1:
                self.builder.get_object('label_status').set_text("Es wurden eine Datei gefunden")
            else:
                self.builder.get_object('label_status').set_text("Es wurden %i Dateien gefunden" % len(model))

    #
    # GATHER_INFORMATION
    #

    def forward(self, iter=None, link=None):
        # ~ iter==None --> programs search was skipped
        # ~ iter!=None --> iter is the selected program
        # ~ link!=None --> executable was called with 'link' argument

        self.mode = 1  # download

        self.builder.get_object('vbox_search').hide()
        self.builder.get_object('vbox_download').show()
        self.builder.get_object('button_ok').set_label("_Download")
        self.builder.get_object('button_ok').set_sensitive(True)

        if iter:
            self.filename, mirrors = self.builder.get_object('liststore_programs').get(iter, 0, 7)

            if mirrors == 1:
                self.builder.get_object('button_mirror_search').set_label("Auf einem Mirror suchen")
            else:
                self.builder.get_object('button_mirror_search').set_label("Auf %i Mirrors suchen" % mirrors)

            GeneratorTask(self.gather_information, self.gather_information_callback,
                          self.gather_information_stop).start()
        else:
            self.builder.get_object('image_spinner_download').hide()
            self.builder.get_object('button_mirror_search').hide()
            self.builder.get_object('label_torrent').set_markup("Download via Torrent")
            self.builder.get_object('label_error').set_markup('')

            if link:
                self.builder.get_object('entry_link').set_text(link)
            else:
                self.builder.get_object('label_download_status').set_markup("Füge einen Downloadlink in das Feld ein!")

    def gather_information(self):
        self.builder.get_object('image_spinner_download').show()
        self.builder.get_object('label_download_status').set_markup(
            "Es soll die Datei\n<b>%s</b>\nheruntergeladen werden." % self.filename)
        self.cutlists_treeview.get_model().clear()

        without_otrkey = self.filename[:-7]

        # search for torrents
        torrent_filename = os.path.join(self.config.get('general', 'folder_new_otrkeys'), self.filename + '.torrent')
        if not os.path.exists(torrent_filename):
            url = 'http://81.95.11.2/torrents/' + self.filename + '.torrent'
            try:
                request.urlretrieve(url, torrent_filename)
            except IOError:
                yield 'torrent_error', "Torrentdatei konnte nicht heruntergeladen werden (%s)!"
        # read filename
        torrent = lt.bdecode(open(torrent_filename, 'rb').read())
        info = lt.torrent_info(torrent)
        info_hash = str(info.info_hash())

        try:
            result = scrape('http://81.95.11.2:8080/announce', [info_hash])
            for hash, stats in result.iteritems():
                yield 'torrent', stats["seeds"], stats["peers"]
        except:
            yield 'torrent_error', "Tracker konnte nicht erreicht werden"

        if os.path.isfile(torrent_filename):
            os.remove(torrent_filename)

        # search for cutlists
        error, cutlists_found = cutlists.download_cutlists(without_otrkey, self.config.get('general', 'server'), 1,
                                                           False)
        if error:
            yield 'cutlist_error', error
        else:
            yield 'cutlist', cutlists_found

    def gather_information_callback(self, value, *args):
        # torrent
        if value == 'torrent_error':
            self.builder.get_object('label_torrent').set_markup("Download via Torrent (<b>%s</b>)" % args[0])
        elif value == 'torrent':
            self.builder.get_object('label_torrent').set_markup(
                "Download via Torrent (<b>%i Seeder, %i Leecher</b>)" % args)
            self.builder.get_object('radiobutton_torrent').set_sensitive(True)

        # cutlist
        elif value == 'cutlist_error':
            self.builder.get_object('checkbutton_cut').set_sensitive(False)
            self.builder.get_object('label_error').set_markup('<b>%s</b>' % args[0])
        elif value == 'cutlist':
            if len(args[0]) == 0:
                self.builder.get_object('checkbutton_cut').set_sensitive(False)
                self.builder.get_object('label_error').set_markup('<b>Keine Cutlists gefunden</b>')
            else:
                self.builder.get_object('label_error').set_markup('')
                self.builder.get_object('checkbutton_cut').set_sensitive(True)
                for cutlist in args[0]:
                    self.cutlists_treeview.add_cutlist(cutlist)

    def gather_information_stop(self):
        self.builder.get_object('image_spinner_download').hide()

        #

    # SIGNALS
    #

    def on_entry_link_changed(self, widget, data=None):
        download_link = widget.get_text()
        result = re.findall("([a-z._\-0-9]*_TVOON_DE[a-z0-9.]*\.otrkey)", download_link, re.IGNORECASE)
        if result:
            self.filename = result[0]

            GeneratorTask(self.gather_information, self.gather_information_callback,
                          self.gather_information_stop).start()
        else:
            pass

    def treeview_cutlists_selection_changed(self, treeselection, data=None):
        model, iter = treeselection.get_selected()
        if iter:
            self.builder.get_object('checkbutton_cut').set_active(True)

    def treeview_programs_selection_changed(self, treeselection, data=None):
        model, iter = treeselection.get_selected()
        self.builder.get_object('button_ok').set_sensitive(iter != None)

    def on_button_search_clicked(self, widget, data=None):
        text = self.builder.get_object('entry_search').get_text()
        if len(text) < 3:
            self.builder.get_object('label_status').set_markup("<b>Die Suche muss mindesten 3 Zeichen haben!</b>")
            return
        else:
            for char in text:
                if not char.lower() in 'abcdefghijklmnopqrstuvwxyz0123456789.-_ *':
                    self.builder.get_object('label_status').set_markup(
                        "<b>Erlaubt sind nur Groß- und Kleinbuchstaben, die Ziffern 0 bis 9, der Punkt, das Minus, der Unterstrich und der Stern/Leerzeichen als Platzhalter!</b>")
                    return

            self.builder.get_object('label_status').set_markup("")

        model = self.builder.get_object('liststore_programs')
        model.clear()
        self.builder.get_object('scrolledwindow_programs').hide()
        self.builder.get_object('vbox_searching').show()
        self.builder.get_object('button_search').set_sensitive(False)

        self.error = ""

        GeneratorTask(self.search, self.search_callback, self.search_stop).start(text)

    def on_treeview_programs_row_activated(self, treeview, path, view_column, data=None):
        iter = treeview.get_model().get_iter(path)
        self.forward(iter)

    def on_checkbutton_cut_toggled(self, widget, data=None):
        if widget.get_active():
            self.builder.get_object('checkbutton_decode').set_active(True)

    def on_radiobutton_torrent_toggled(self, widget, data=None):
        self.builder.get_object('box_normal').set_sensitive(not widget.get_active())

    def on_button_mirror_search_clicked(self, widget, data=None):
        uri = f"http://otrkeyfinder.com/?search={self.filename}"
        Gtk.show_uri_on_window(self, uri, Gdk.CURRENT_TIME)

    def on_button_cancel_clicked(self, widget, data=None):
        self.response(-6)

    def on_button_ok_clicked(self, widget, data=None):
        if self.mode == 0:  # search for files
            selection = self.builder.get_object('treeview_programs').get_selection()
            model, iter = selection.get_selected()
            self.forward(iter)

        else:  # actual download
            if self.builder.get_object('radiobutton_normal').get_active():
                if not self.builder.get_object('entry_link').get_text():
                    self.gui.message_error_box("Es ist kein Download-Link eingetragen!")
                    return
                if self.builder.get_object('checkbutton_cut').get_active():
                    if not self.cutlists_treeview.get_selected():
                        self.gui.message_error_box("Es ist keine Cutlist ausgewählt!")
                        return

            self.response(-5)
    """

    # <- del_libtorrent


def new(gui, config, via_link, link=None):
    glade_filename = otrvpath.getdatapath("ui", "AddDownloadDialog.glade")

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("add_download_dialog")
    dialog.gui = gui
    dialog.config = config
    if via_link:
        dialog.forward(link=link)
    return dialog
