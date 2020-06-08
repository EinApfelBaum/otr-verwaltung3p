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

from otrverwaltung3p.constants import Action
import os.path
import logging

from otrverwaltung3p.cutlists import Cutlist
from otrverwaltung3p.constants import Action, Status
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p import fileoperations
from otrverwaltung3p.GeneratorTask import GeneratorTask


class Decode:
    def __init__(self):
        self.status = -1
        self.message = ""


class Cut:
    def __init__(self):
        self.status = -1
        self.message = ""

        self.cut_action = -1  # manually, best cutlist ...
        self.cutlist = Cutlist()  # cutlist class instance

        # filled in by dialog_conclusion
        self.my_rating = -1  # rating, when cut by cutlist
        self.rename = ""  # renamed filename
        self.archive_to = None  # directory, where the file should be archived
        self.create_cutlist = False  # create a cutlist?
        self.upload_cutlist = False  # upload the cutlist?
        self.delete_uncut = True  # delete the uncut video after cut?


class FileConclusion:
    def __init__(self, action, otrkey="", uncut_video=""):
        self.action = action

        if action == Action.DECODE or action == Action.DECODEANDCUT:
            self.otrkey = otrkey
            self.decode = Decode()

        self.uncut_video = uncut_video

        if action == Action.CUT or action == Action.DECODEANDCUT:
            self.cut_video = ""
            self.ac3_file = ""
            self.cut = Cut()

    def get_extension(self):
        if self.cut_video == "":  # prefer the extension of the cut video
            return os.path.splitext(self.uncut_video)[1]
        else:
            return os.path.splitext(self.cut_video)[1]


class ConclusionsManager:
    def __init__(self, app):
        self.log = logging.getLogger(self.__class__.__name__)
        self.app = app
        self.conclusions = []

    def add_conclusions(self, *args):
        for conclusion in args:
            self.conclusions.append(conclusion)

        if len(self.conclusions) == 1:
            text = "Eine geschnittene Datei anzeigen."
        else:
            text = f"{len(self.conclusions)} geschnittene Dateien anzeigen."

        if self.app.config.get('general', 'show_conclusiondialog_after_cutting'):
            self.show_conclusions()
        else:
            self.app.gui.main_window.builder.get_object('button_show_conclusion').set_label(text)
            self.app.gui.main_window.builder.get_object('box_conclusion').show()

    def show_conclusions(self):
        conclusions = self.app.gui.dialog_conclusion.run_(self.conclusions, self.app.rename_by_schema,
                                                          self.app.config.get('general', 'folder_archive'))
        self.app.gui.main_window.builder.get_object('box_conclusion').hide()
        self.conclusions = []

        # create cutlists
        cutlists = []

        for conclusion in conclusions:
            if conclusion.action == Action.DECODE:
                continue

            self.log.debug("for file ".format(conclusion.uncut_video))

            # rename
            if conclusion.cut.rename:
                self.log.debug("conclusion.cut.rename = true")
                extension = os.path.splitext(conclusion.cut_video)[1]
                if not conclusion.cut.rename.endswith(extension):
                    conclusion.cut.rename += extension

                new_filename = os.path.join(self.app.config.get('general', 'folder_cut_avis'),
                                            conclusion.cut.rename.replace('/', '_'))
                new_filename = fileoperations.make_unique_filename(new_filename)

                if conclusion.cut_video != new_filename:
                    conclusion.cut_video = fileoperations.rename_file(conclusion.cut_video, new_filename)

            # move cut video to archive
            self.log.debug("Move to archive?")
            if conclusion.cut.status == Status.OK and conclusion.cut.archive_to:
                self.log.debug("conclusion.cut.archive_to = true")
                fileoperations.move_file(conclusion.cut_video, conclusion.cut.archive_to)

            # move uncut video to trash if it's ok
            self.log.debug("Move to trash?")
            if conclusion.cut.status == Status.OK and conclusion.cut.delete_uncut:
                self.log.debug("true")
                if os.path.exists(conclusion.uncut_video):
                    # move to trash
                    target = self.app.config.get('general', 'folder_trash_avis')
                    conclusion.uncut_video = fileoperations.move_file(conclusion.uncut_video, target)
                    if os.path.exists(conclusion.ac3_file):
                        target = self.app.config.get('general', 'folder_trash_avis')
                        fileoperations.move_file(conclusion.ac3_file, target)

                # remove local cutlists
                self.log.debug("Remove local cutlist?")
                if self.app.config.get('general', 'delete_cutlists'):
                    self.log.debug("true")
                    if conclusion.cut.cutlist.local_filename:
                        if os.path.exists(conclusion.cut.cutlist.local_filename):
                            fileoperations.remove_file(conclusion.cut.cutlist.local_filename)

            self.log.debug("Create cutlist?")
            if conclusion.cut.create_cutlist:
                self.log.debug("true")
                if "VirtualDub" in conclusion.cut.cutlist.intended_app:
                    intended_app_name = "VirtualDub"
                else:
                    intended_app_name = "Avidemux"

                if not conclusion.cut.cutlist.local_filename:
                    path_uncut_avis = self.app.config.get('general', 'folder_uncut_avis')
                    conclusion.cut.cutlist.local_filename = \
                        os.path.join(path_uncut_avis, os.path.basename(conclusion.uncut_video) + ".cutlist")

                conclusion.cut.cutlist.author = self.app.config.get('general', 'cutlist_username')
                conclusion.cut.cutlist.intended_version = open(otrvpath.getdatapath("VERSION"), 'r').read().strip()
                conclusion.cut.cutlist.smart = self.app.config.get('general', 'smart')

                conclusion.cut.cutlist.write_local_cutlist(conclusion.uncut_video, intended_app_name,
                                                           conclusion.cut.my_rating)

                if conclusion.cut.upload_cutlist:
                    cutlists.append(conclusion.cut.cutlist)

        # upload cutlists:
        def upload():
            error_messages = []

            count = len(cutlists)
            # ~ counter = 0
            for cutlist in cutlists:
                # ~ counter += 1
                error_message = cutlist.upload(self.app.config.get('general', 'server'),
                                               self.app.config.get('general', 'cutlist_hash'))
                if error_message:
                    error_messages.append(error_message)
                else:
                    if self.app.config.get('general', 'delete_cutlists'):
                        fileoperations.remove_file(cutlist.local_filename)
                # ~ self.log.debug("Counter: {}, Count: {}".format(counter, count))
                # ~ if counter < count:
                    # ~ self.log.debug("Multiple cutlists: Next upload delayed.")
                    # ~ time.sleep(1.1)

            message = "Es wurden %s/%s Cutlisten hochgeladen!" % (str(count - len(error_messages)), str(count))
            if len(error_messages) > 0:
                message += " (" + ", ".join(error_messages) + ")"

            yield message

        if len(cutlists) > 0:
            self.log.debug("Upload cutlists")
            if self.app.gui.question_box("Soll(en) %s Cutlist(en) hochgeladen werden?" % len(cutlists)):
                def change_status(message):
                    self.app.gui.main_window.change_status(0, message)

                GeneratorTask(upload, change_status).start()

        # rate cutlists
        def rate():
            yield 0  # fake generator
            messages = []
            count = 0
            for conclusion in conclusions:
                if conclusion.action == Action.DECODE:
                    continue

                if conclusion.cut.my_rating > -1:
                    self.log.debug("Rate with ", conclusion.cut.my_rating)
                    success, message = conclusion.cut.cutlist.rate(conclusion.cut.my_rating,
                                                                   self.app.config.get('general', 'server'))
                    if success:
                        count += 1
                    else:
                        messages += [message]

            if count > 0 or len(messages) > 0:
                if count == 0:
                    text = "Es wurde keine Cutlist bewertet!"
                if count == 1:
                    text = "Es wurde 1 Cutlist bewertet!"
                else:
                    text = "Es wurden %s Cutlisten bewertet!" % count

                if len(messages) > 0:
                    text += " (Fehler: %s)" % ", ".join(messages)

                self.app.gui.main_window.change_status(0, text)

        self.log.debug("Rate cutlists")
        GeneratorTask(rate).start()
