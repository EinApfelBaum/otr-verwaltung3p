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
from gi.repository import Gtk, GdkPixbuf

from otrverwaltung3p import path


class PluginsDialog(Gtk.Dialog, Gtk.Buildable):
    __gtype_name__ = "PluginsDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        pass

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

        self.builder.get_object('treeview_plugins').get_selection().connect('changed', self._on_selection_changed)

    def _run(self):
        self.builder.get_object('liststore_plugins').clear()

        for name, plugin in self.gui.app.plugin_system.plugins.items():
            enabled = (name in self.gui.app.plugin_system.enabled_plugins)
            self.builder.get_object('liststore_plugins').append([enabled, plugin.Name, plugin.Desc, name])

        if len(self.builder.get_object('liststore_plugins')) > 0:
            self.builder.get_object('treeview_plugins').get_selection().select_path((0,))

        self.run()
        self.hide()

    def _on_cellrenderer_enabled_toggled(self, widget, path, data=None):
        store = self.builder.get_object('liststore_plugins')

        iter = store.get_iter(path)
        store.set_value(iter, 0, not store.get_value(iter, 0))

        if store.get_value(iter, 0):  # enable or disable plugin
            self.gui.app.plugin_system.enable(store.get_value(iter, 3))
        else:
            self.gui.app.plugin_system.disable(store.get_value(iter, 3))

    def _on_selection_changed(self, selection, data=None):
        store, iter = selection.get_selected()
        if not iter: return

        self.builder.get_object('label_name').set_markup("<b>%s</b>" % store.get_value(iter, 1))
        self.builder.get_object('label_desc').set_markup("<b>Beschreibung: </b>\n%s" % store.get_value(iter, 2))
        name = store.get_value(iter, 3)
        self.builder.get_object('label_author').set_markup(
            "<b>Autor: </b>\n%s" % self.gui.app.plugin_system.plugins[name].Author)
        self.builder.get_object('button_config').set_sensitive(self.gui.app.plugin_system.plugins[name].Configurable)

    def _on_button_config_clicked(self, widget, data=None):
        store, iter = self.builder.get_object('treeview_plugins').get_selection().get_selected()
        name = store.get_value(iter, 3)

        dialog = Gtk.Dialog(store.get_value(iter, 1) + " - Einstellungen", parent=self, flags=Gtk.DialogFlags.MODAL,
                            buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        dialog.set_border_width(2)
        dialog.set_icon(GdkPixbuf.Pixbuf.new_from_file(path.get_image_path('icon.png')))

        dialog = self.gui.app.plugin_system.plugins[name].configurate(dialog)

        dialog.show_all()
        dialog.run()
        dialog.hide()


def NewPluginsDialog(gui):
    glade_filename = path.getdatapath('ui', 'PluginsDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("plugins_dialog")
    dialog.gui = gui

    return dialog
