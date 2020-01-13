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
from gi.repository import Gtk, Gdk, GObject


class SidebarButton(Gtk.Button):
    __gsignals__ = {
        'element-clicked': (GObject.SIGNAL_RUN_FIRST, None, (int,))
    }

    def __init__(self, title, id, padding):
        Gtk.Button.__init__(self)

        self.title = title
        self.active = False
        self.id = id
        self.search = None

        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_property('can_focus', False)  # why?

        # HBox
        #   - [ Alignment(Label) | (image) ]

        self.box = Gtk.HBox()

        self.label = Gtk.Label()
        self.label.set_halign(Gtk.Align.START)
        self.label.set_margin_left(padding)
        self.label.set_text(self.title)

        self.box.add(self.label)
        self.add(self.box)

        def on_clicked(button):
            self.emit('element-clicked', self.id)

        self.connect('clicked', on_clicked)

    def add_widget(self, widget):
        self.box.pack_end(widget, False, False, 0)

    def update_text(self):
        if self.active:
            markup = '<b>%s</b>' % self.title
        else:
            markup = self.title

        if self.search is not None:
            markup += ' <b>(%i)</b>' % self.search

        self.label.set_markup(markup)

    def set_search(self, search):
        self.search = search
        self.update_text()

    def set_active(self, active_state):
        self.active = active_state
        self.update_text()


class Sidebar(Gtk.EventBox):
    __gsignals__ = {
        'element-clicked': (GObject.SIGNAL_RUN_FIRST, None, (int,))
    }

    def __init__(self):
        Gtk.EventBox.__init__(self)
        self.set_size_request(200, -1)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.set_border_width(5)
        # self.vbox.show()
        self.add(self.vbox)

        self.elements = []

        style = self.get_style()
        self.color = Gdk.color_parse('#AFAFAF')
        self.modify_bg(Gtk.StateFlags.NORMAL, self.color)

    def on_element_clicked(self, element, id):
        self.set_active(id)
        self.emit('element-clicked', id)

    # public
    def set_active(self, id):
        for element in self.elements:
            if id == element.id:
                element.set_active(True)
                element.set_relief(Gtk.ReliefStyle.NORMAL)
            else:
                element.set_active(False)
                element.set_relief(Gtk.ReliefStyle.NONE)

    def set_search(self, search_values):
        if search_values:
            for element in self.elements:
                key = element.id
                if key in search_values.keys():
                    element.set_search(search_values[key])
        else:
            for element in self.elements:
                element.set_search(None)

    def add_section(self, title):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_margin_left(10)
        label.set_margin_top(10)
        label.set_margin_bottom(5)
        label.set_markup('<span color="#6D6D6D"><b>%s</b></span>' % title)

        self.vbox.pack_start(label, False, False, 0)

    def add_element(self, id, title, indent=True, extra=0):
        if indent:
            element = SidebarButton(title, id, 20 + extra)
        else:
            element = SidebarButton(title, id, 10)

        self.elements.append(element)
        element.connect('element-clicked', self.on_element_clicked)

        self.vbox.pack_start(element, False, False, 0)

        return element
