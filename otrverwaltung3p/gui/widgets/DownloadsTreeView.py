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
from gi.repository import GObject, Gdk, GdkPixbuf, Gtk

from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.constants import DownloadStatus, DownloadTypes


class DownloadsTreeView(Gtk.TreeView):
    def __init__(self):
        Gtk.TreeView.__init__(self)

        self.liststore = Gtk.ListStore(object)
        self.set_model(self.liststore)

        self.set_headers_visible(False)

        rend = CellRendererDownload()
        column = Gtk.TreeViewColumn("col", rend, download=0)
        self.append_column(column)

        self.set_rules_hint(True)

    def __update_view(self):
        self.queue_draw()

    def add_objects(self, *args):
        for obj in args:
            obj.update_view = self.__update_view
            self.liststore.append([obj])

    def remove_objects(self, *args):
        for row in self.liststore:
            if row[0] in args:
                del self.liststore[row.iter]


class CellRendererDownload(Gtk.CellRenderer):
    __gtype_name__ = "CellRendererDownload"

    __gproperties__ = {"download": (GObject.TYPE_PYOBJECT, "Download", "Download", GObject.PARAM_READWRITE,)}

    def __init__(self):
        Gtk.CellRenderer.__init__(self)
        # self.__gobject_init__()

        self.set_property("mode", Gtk.CellRendererMode.ACTIVATABLE)

        self.statuses = {
            DownloadStatus.RUNNING: GdkPixbuf.Pixbuf.new_from_file(
                otrvpath.getdatapath("media", "download_start.png")
            ),
            DownloadStatus.STOPPED: GdkPixbuf.Pixbuf.new_from_file(otrvpath.getdatapath("media", "download_stop.png")),
            DownloadStatus.ERROR: GdkPixbuf.Pixbuf.new_from_file(otrvpath.getdatapath("media", "error.png")),
            DownloadStatus.FINISHED: GdkPixbuf.Pixbuf.new_from_file(otrvpath.getdatapath("media", "finished.png")),
            DownloadStatus.SEEDING: GdkPixbuf.Pixbuf.new_from_file(otrvpath.getdatapath("media", "finished.png")),
        }

        self.types = {
            DownloadTypes.TORRENT: "Torrent-Download",
            DownloadTypes.BASIC: "Normaler Download",
            DownloadTypes.OTR_DECODE: "OTR-Download mit Dekodieren",
            DownloadTypes.OTR_CUT: "OTR-Download mit Schneiden",
        }

        self.cellrenderer_pixbuf = Gtk.CellRendererPixbuf()
        self.cellrenderer_filename = Gtk.CellRendererText()
        self.cellrenderer_info = Gtk.CellRendererText()
        self.cellrenderer_progress = Gtk.CellRendererProgress()

    def on_get_size(self, widget, cell_area=None):
        complete_width, complete_height = 0, 0

        xoffset, yoffset, width, height = self.cellrenderer_filename.get_size(widget)
        complete_height += height
        xoffset, yoffset, width, height = self.cellrenderer_info.get_size(widget)
        complete_height += height
        xoffset, yoffset, width, height = self.cellrenderer_progress.get_size(widget)
        complete_height += height

        return 0, 0, complete_width, complete_height + 10

    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
        x, y, w, _ = cell_area.x, cell_area.y, cell_area.width, cell_area.height

        # area = Gdk.Rectangle(x, y, 16, 20)
        area = Gdk.Rectangle()
        area.x = x + 2
        area.y = y
        area.width = 16
        area.height = 20
        self.cellrenderer_pixbuf.render(window, widget, background_area, area, expose_area, flags)

        # area = Gdk.Rectangle(x + 20, y, w - 25, 16)
        area.x = x + 20
        area.y = y
        area.width = w - 25
        area.height = 16
        self.cellrenderer_filename.render(window, widget, background_area, area, expose_area, flags)

        # area = Gdk.Rectangle(x + 20, y + 22, w - 25, 16)
        area.x = x + 20
        area.y = y + 22
        area.width = w - 25
        area.height = 16
        self.cellrenderer_info.render(window, widget, background_area, area, expose_area, flags)

        # area = Gdk.Rectangle(x + 20, y + 45, w - 25, 18)
        area.x = x + 20
        area.y = y + 45
        area.width = w - 25
        area.height = 18
        self.cellrenderer_progress.render(window, widget, background_area, area, expose_area, flags)

    def on_activate(self, event, widget, path, background_area, cell_area, flags):
        pass

    def do_set_property(self, pspec, value):
        if pspec.name == "download":
            if value.filename:
                self.cellrenderer_filename.set_property("markup", value.filename)
            else:
                self.cellrenderer_filename.set_property("markup", "Dateiname nicht bekannt.")

            self.cellrenderer_progress.set_property("value", value.information["progress"])
            info_text, text = "", ""

            text = self.types[value.information["download_type"]]

            if value.information["status"] != -1:
                pixbuf = self.statuses[value.information["status"]]
                self.cellrenderer_pixbuf.set_property("pixbuf", pixbuf)

            if value.information["message_short"]:
                text += " - %s" % value.information["message_short"]

            infos = []
            if value.information["size"]:
                infos.append("Größe: %s" % self.humanize_size(value.information["size"]))
            if value.information["speed"]:
                infos.append("Geschwindigkeit: %s" % value.information["speed"])
            if value.information["est"]:
                infos.append("Verbleibende Zeit: %s" % value.information["est"])

            if value.information["download_type"] == DownloadTypes.TORRENT:
                if value.information["seeders"] is not None:
                    infos.append("%s Seeder" % value.information["seeders"])

            if infos:
                info_text += "<i>%s</i> - " % text + ", ".join(infos)
            else:
                info_text += "<i>%s</i>" % text

            self.cellrenderer_info.set_property("markup", info_text)

    def humanize_size(self, bytes):
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = "%.1f T" % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = "%.1f GB" % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = "%.1f MB" % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = "%.1f K" % kilobytes
        else:
            size = "%.1f b" % bytes
        return size

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)
