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

from os import mkdir
from os.path import dirname, join, isdir, splitext
import re

from otrverwaltung3p import fileoperations
from otrverwaltung3p.actions.baseaction import BaseAction


class Delete(BaseAction):
    def __init__(self, app, gui):
        BaseAction.__init__(self)
        self.update_list = False
        self.__app = app
        self.__gui = gui

    def do(self, filenames, cut_action=None):
        if len(filenames) == 1:
            message = "Es ist eine Datei ausgewählt. Soll diese Datei "
        else:
            message = "Es sind %s Dateien ausgewählt. Sollen diese Dateien " % len(filenames)

        if self.__gui.question_box(message + "in den Müll verschoben werden?"):
            self.update_list = True
            for f in filenames:
                if f.endswith("otrkey"):
                    fileoperations.move_file(f, self.__app.config.get('general', 'folder_trash_otrkeys'))
                else:
                    fileoperations.move_file(f, self.__app.config.get('general', 'folder_trash_avis'))
        self.__app.filenames_locked = []


class RealDelete(BaseAction):
    def __init__(self, app, gui):
        BaseAction.__init__(self)
        self.update_list = True
        self.__gui = gui

    def do(self, filenames, cut_action=None):
        if len(filenames) == 1:
            message = "Es ist eine Datei ausgewählt. Soll diese Datei "
        else:
            message = "Es sind %s Dateien ausgewählt. Sollen diese Dateien " % len(filenames)

        if self.__gui.question_box(message + "endgültig gelöscht werden?"):
            for f in filenames:
                fileoperations.remove_file(f)
        self.__app.filenames_locked = []


class Restore(BaseAction):
    def __init__(self, app, gui):
        BaseAction.__init__(self)
        self.update_list = True
        self.__app = app
        self.__gui = gui

    def do(self, filenames, cut_action=None):
        for f in filenames:
            if f.endswith("otrkey"):
                fileoperations.move_file(f, self.__app.config.get('general', 'folder_new_otrkeys'))
            elif f.endswith("ac3"):
                fileoperations.move_file(f, self.__app.config.get('general', 'folder_uncut_avis'))
            elif self.__app.regex_uncut_video.match(f):
                fileoperations.move_file(f, self.__app.config.get('general', 'folder_uncut_avis'))
            else:
                fileoperations.move_file(f, self.__app.config.get('general', 'folder_cut_avis'))


class Rename(BaseAction):
    def __init__(self, app, gui):
        BaseAction.__init__(self)
        self.update_list = True
        self.__gui = gui

    def do(self, filenames, cut_action=None):
        response, new_names = self.__gui.dialog_rename.init_and_run("Umbenennen", filenames)

        if response:
            for f in filenames:
                extension = splitext(f)[1]

                new_name = new_names[f]
                new_name = join(dirname(f), new_name.replace('/', '_'))

                if f.endswith(extension) and not new_name.endswith(extension):
                    new_name += extension

                fileoperations.rename_file(f, new_name)
        else:
            self.update_list = False
        self.__app.filenames_locked = []


class NewFolder(BaseAction):
    def __init__(self, app, gui):
        BaseAction.__init__(self)
        self.update_list = False
        self.__gui = gui

    def do(self, filename, cut_action=None):
        if isdir(filename):
            path = filename
        else:
            path = dirname(filename)

        response, new_names = self.__gui.dialog_rename.init_and_run("Neuer Ordner", ["Neuer Ordner"])

        if response and new_names["Neuer Ordner"] != "":
            self.update_list = True
            mkdir(join(path, new_names["Neuer Ordner"]))
