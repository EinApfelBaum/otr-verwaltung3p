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
from gi.repository import Gtk
from os.path import basename, join, exists
import base64
import subprocess
import os, re, shutil
import logging
import gc

from otrverwaltung3p import fileoperations
from otrverwaltung3p.conclusions import FileConclusion
from otrverwaltung3p.constants import Action, Cut_action, Status, Program
from otrverwaltung3p import cutlists as cutlists_management
from otrverwaltung3p.GeneratorTask import GeneratorTask
from otrverwaltung3p.gui import CutinterfaceDialog
from otrverwaltung3p.actions.cut import Cut
from otrverwaltung3p.actions.cutsmartmkvmerge import CutSmartMkvmerge
from otrverwaltung3p.actions.cutvirtualdub import CutVirtualdub
from otrverwaltung3p.actions.cutavidemux import CutAvidemux
from otrverwaltung3p import bcode


class DecodeOrCut(Cut):
    def __init__(self, app, gui):
        super().__init__(app, gui)
        self.log = logging.getLogger(self.__class__.__name__)
        self.update_list = True
        self.app = app
        self.config = app.config
        self.gui = gui
        self.download_error = False
        self.download_first_try = True

    def do(self, action, filenames, cut_action=None):
        self.rename_by_schema = self.app.rename_by_schema

        decode, cut = False, False

        # prepare tasks
        if action == Action.DECODE:
            self.gui.main_window.set_tasks_text('Dekodieren')
            decode = True
        elif action == Action.CUT:
            self.gui.main_window.set_tasks_text('Schneiden')
            cut = True
        else:  # decode and cut
            self.gui.main_window.set_tasks_text('Dekodieren/Schneiden')
            decode, cut = True, True

        file_conclusions = []

        if decode:
            for otrkey in filenames:
                file_conclusions.append(FileConclusion(action, otrkey=otrkey))

        if cut and not decode:  # dont add twice
            for uncut_video in filenames:
                file_conclusions.append(FileConclusion(action, uncut_video=uncut_video))

        # decode files
        if decode:
            if self.decode(file_conclusions) == False:
                return

        # cut files
        if cut:
            if self.cut(file_conclusions, action, cut_action) == False:
                return

        self.gui.main_window.block_gui(False)

        # no more need for tasks view
        self.gui.main_window.set_tasks_visible(False)

        show_conclusions = False
        # Only cut - don't show conclusions if all were cancelled
        if action == Action.CUT:
            for conclusion in file_conclusions:
                if conclusion.cut.status != Status.NOT_DONE:
                    show_conclusions = True
                    break

        # Only decode - don't show if everything is OK
        elif action == Action.DECODE:
            for conclusion in file_conclusions:
                if conclusion.decode.status != Status.OK:
                    show_conclusions = True

            if not show_conclusions:
                self.app.gui.main_window.change_status(0, "%i Datei(en) erfolgreich dekodiert" % len(file_conclusions),
                                                       permanent=True)

        # Decode and cut - always show
        else:
            show_conclusions = True

        if show_conclusions:
            self.app.conclusions_manager.add_conclusions(*file_conclusions)

    def decode(self, file_conclusions):
        self.log.debug("Decoder: {}".format(self.config.get('programs', 'decoder')))
        otrtool = shutil.which("otrtool")
        # no decoder
        # --> otrtool
        if not "decode" and not "otrtool" in self.config.get('programs', 'decoder'):
            # no decoder specified
            self.gui.message_error_box("Es ist kein korrekter Dekoder angegeben!")
            return False
        elif self.config.get_program('decoder') == 'otrtool' and not otrtool:
            # otrtool not found in path
            self.gui.message_error_box("Der Dekoder otrtool ist ausgewählt, wurde aber nicht im \
                                                                                Pfad gefunden!")
            return False
        elif '/' in self.config.get_program('decoder'):  # It's an external program
            isexe = os.path.isfile(self.config.get_program('decoder')) and os.access(
                                                    self.config.get_program('decoder'), os.X_OK)
            if not isexe:  # File doen't exist or is not executable
                self.gui.message_error_box("Der externe Dekoder wurde nicht gefunden oder ist \
                                                                                nicht ausführbar.")
                return False
        # <-- otrtool

        # retrieve email and password
        email = self.config.get('general', 'email')
        password = self.config.get('general', 'password')

        if not email or not password:
            self.gui.dialog_email_password.set_email_password(email, password)

            # let the user type in his data through a dialog
            response = self.gui.dialog_email_password.run()
            self.gui.dialog_email_password.hide()

            if response == Gtk.ResponseType.OK:
                email, password, store_passwd, config = self.gui.dialog_email_password.\
                                                                            get_email_password()
                if store_passwd:
                    config.set('general', 'password', password)
            else:  # user pressed cancel
                return False

        # now this method may not return "False"
        self.gui.main_window.set_tasks_visible(True)
        self.gui.main_window.block_gui(True)

        # decode each file
        for count, file_conclusion in enumerate(file_conclusions):
            # update progress
            self.gui.main_window.set_tasks_text("Datei %s/%s dekodieren" % (count + 1,
                                                                            len(file_conclusions)))

            # --> otrtool
            if 'otrtool' in self.config.get_program('decoder'):
                command = [self.config.get_program('decoder'), "-x", "-g", "-e", email, "-p",
                           password, "-O", self.config.get('general', 'folder_uncut_avis') + "/" +
                           basename(file_conclusion.otrkey[0:len(file_conclusion.otrkey)-7]),
                           file_conclusion.otrkey]
            else:
                verify = True
                command = [self.config.get_program('decoder'), "-i", file_conclusion.otrkey, "-e",
                    email, "-p", password, "-o", self.config.get('general', 'folder_uncut_avis')]
                if not self.config.get('general', 'verify_decoded'):
                    verify = False
                    command += ["-q"]
            # <-- otrtool

            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except OSError:
                file_conclusion.decode.status = Status.ERROR
                file_conclusion.decode.message = "Dekoder wurde nicht gefunden."
                continue

            # --> otrtool
            if 'otrtool' in self.config.get_program('decoder'):
                error_message = ""
                file_count = count + 1, len(file_conclusions)
                # list of non error strings
                nonerror = ["OK", "gui", "OTR-Tool, ", "Keyphrase from", "Keyphrase:",
                            "Decrypting", "Trying to contact", "Server responded", "info:",
                            "warning:"]
                for line in iter(process.stderr.readline,''):
                    line = line.decode("utf-8")
                    if not line:
                        break
                    # Gathering errors
                    if not any(x in line for x in nonerror):
                        error_message += line.strip()

                    if "Decrypting" in line:
                        self.gui.main_window.set_tasks_text("Datei %s/%s dekodieren und prüfen" % file_count)

                    if ("gui" in line) and not ("Finished" in line):
                        progress = int(line[5:])
                        # update progress
                        self.gui.main_window.set_tasks_progress(progress)

                    while Gtk.events_pending():
                            Gtk.main_iteration()
            # <-- otrtool
            else:
                while True:
                    l = ""
                    while True:
                        c = process.stdout.read(1).decode('utf-8')
                        if c == "\r" or c == "\n":
                            break
                        l += c

                    if not l:
                        break

                    try:
                        if verify:
                            file_count = count + 1, len(file_conclusions)

                            if "input" in l:
                                self.gui.main_window.set_tasks_text("Eingabedatei %s/%s kontrollieren" % file_count)
                            elif "output" in l:
                                self.gui.main_window.set_tasks_text("Ausgabedatei %s/%s kontrollieren" % file_count)
                            elif "Decoding" in l:
                                self.gui.main_window.set_tasks_text("Datei %s/%s dekodieren" % file_count)

                        if len(l) > 13 and l[12].isdigit():
                            progress = int(l[10:13])
                            # update progress
                            self.gui.main_window.set_tasks_progress(progress)

                        while Gtk.events_pending():
                            Gtk.main_iteration()
                    except ValueError:
                        pass

                # errors?
                errors = process.stderr.readlines()
                error_message = ""
                for error in errors:
                    error = error.decode('ISO-8859-1')
                    if not 'libmediaclient' in error:
                        error_message += error.strip()

            if error_message == "":  # dekodieren erfolgreich
                file_conclusion.decode.status = Status.OK

                file_conclusion.uncut_video = join(self.config.get('general', 'folder_uncut_avis'),
                            basename(file_conclusion.otrkey[0:len(file_conclusion.otrkey) - 7]))

                # move otrkey to trash
                if self.config.get('general', 'move_otrkey_to_trash_after_decode'):
                    target = self.config.get('general', 'folder_trash_otrkeys')
                    fileoperations.move_file(file_conclusion.otrkey, target)
            else:
                file_conclusion.decode.status = Status.ERROR

                try:
                    str(error_message)
                except UnicodeDecodeError:
                    error_message = str(error_message, 'iso-8859-1')

                file_conclusion.decode.message = error_message

        return True

    def cut(self, file_conclusions, action, default_cut_action=None):
        # now this method may not return "False"
        self.gui.main_window.set_tasks_visible(True)
        self.gui.main_window.block_gui(True)

        if not default_cut_action:
            default_cut_action = self.config.get('general', 'cut_action')

        for count, file_conclusion in enumerate(file_conclusions):
            self.gui.main_window.set_tasks_text("Cutlist %s/%s wählen" % (count + 1,
                                                                            len(file_conclusions)))
            self.gui.main_window.set_tasks_progress((count + 1) / float(
                                                                    len(file_conclusions)) * 100)

            # file correctly decoded?
            if action == Action.DECODEANDCUT:
                if file_conclusion.decode.status != Status.OK:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Datei wurde nicht dekodiert."
                    continue

            file_conclusion.cut.cut_action = default_cut_action

            if default_cut_action in [Cut_action.ASK, Cut_action.CHOOSE_CUTLIST]:
                # show dialog
                self.gui.dialog_cut.setup(
                    file_conclusion.uncut_video,
                    self.config.get('general', 'folder_cut_avis'),
                    default_cut_action == Cut_action.ASK)

                cutlists = []
                self.cutlists_error = False

                def error_cb(error):
                    if error == "Keine Cutlists gefunden" and self.download_first_try:
                        self.download_first_try = False
                        self.gui.dialog_cut.builder.get_object('label_status').set_markup(
                                        "<b>%s</b>" % error + ". Versuche es mit allen Qualitäten")
                        download_generator(True)
                    else:
                        self.gui.dialog_cut.builder.get_object('label_status').set_markup("")
                        self.gui.dialog_cut.builder.get_object('label_status').set_markup(
                                                    "<b>%s</b>" % error +
                                                    " (Es wurde nach allen Qualitäten gesucht)")
                        self.cutlists_error = True
                        self.download_first_try = True

                def cutlist_found_cb(cutlist):
                    self.gui.dialog_cut.add_cutlist(cutlist)
                    cutlists.append(cutlist)

                def completed():
                    if not self.cutlists_error:
                        self.gui.dialog_cut.builder.get_object('label_status').set_markup("")

                def download_generator(get_all_qualities):
                    self.download_error = False

                    # Empty the list for reuse
                    cutlists = []
                    GeneratorTask(cutlists_management.download_cutlists, None, completed).\
                                            start(file_conclusion.uncut_video,
                                                self.config.get('general', 'server'),
                                                self.config.get('general', 'choose_cutlists_by'),
                                                self.config.get('general', 'cutlist_mp4_as_hq'),
                                                error_cb, cutlist_found_cb, get_all_qualities)

                download_generator(False)
                # Run the dialog_cut
                response = self.gui.dialog_cut.run()
                self.gui.dialog_cut.hide()

                if response < 0:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Abgebrochen."
                else:  # change cut_action accordingly
                    file_conclusion.cut.cut_action = response

            if file_conclusion.cut.cut_action == Cut_action.MANUALLY:  # MANUALLY
                error_message, cutlist = self.cut_file_manually(file_conclusion.uncut_video)

                if not error_message:
                    file_conclusion.cut.create_cutlist = True
                    file_conclusion.cut.upload_cutlist = True
                    file_conclusion.cut.cutlist = cutlist
                else:
                    self.log.debug("Error message: {}".format(error_message))
                    file_conclusion.cut.message = error_message
                    if error_message == "Keine Schnitte angegeben":
                        self.log.info("Error message CutinterfaceDialog: {}".format(error_message))
                        file_conclusion.cut.status = Status.NOT_DONE
                    else:
                        file_conclusion.cut.status = Status.ERROR
                        file_conclusion.cut.message = error_message

            elif file_conclusion.cut.cut_action == Cut_action.BEST_CUTLIST:
                error, cutlists = cutlists_management.download_cutlists(
                                                file_conclusion.uncut_video,
                                                self.config.get('general', 'server'),
                                                self.config.get('general','choose_cutlists_by'),
                                                self.config.get('general', 'cutlist_mp4_as_hq'))

                if error:
                    file_conclusion.cut.status = Status.ERROR
                    file_conclusion.cut.message = error
                    continue

                if len(cutlists) == 0:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Keine Cutlist gefunden."
                    continue

                file_conclusion.cut.cutlist = cutlists_management.get_best_cutlist(cutlists)

            elif file_conclusion.cut.cut_action == Cut_action.CHOOSE_CUTLIST:
                if self.gui.dialog_cut.chosen_cutlist is not None:
                    file_conclusion.cut.cutlist = self.gui.dialog_cut.chosen_cutlist
                else:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Keine Cutlist gefunden."

            elif file_conclusion.cut.cut_action == Cut_action.LOCAL_CUTLIST:
                file_conclusion.cut.cutlist.local_filename = file_conclusion.uncut_video + ".cutlist"

                if not exists(file_conclusion.cut.cutlist.local_filename):
                    file_conclusion.cut.status = Status.ERROR
                    file_conclusion.cut.message = "Keine lokale Cutlist gefunden."

            elif file_conclusion.cut.cut_action == Cut_action.ASK:
                file_conclusion.cut.status = Status.NOT_DONE
                file_conclusion.cut.message = "Keine Cutlist gefunden."

        # and finally cut the file
        for count, file_conclusion in enumerate(file_conclusions):

            if file_conclusion.cut.status in [Status.NOT_DONE, Status.ERROR]:
                continue

            self.log.info("[Decodeandcut] Datei %s wird geschnitten" % file_conclusion.uncut_video)
            self.gui.main_window.set_tasks_text("Datei %s/%s schneiden" % (count + 1, len(file_conclusions)))
            self.gui.main_window.set_tasks_progress(0)
            while Gtk.events_pending():
                Gtk.main_iteration()

            # download cutlist
            if file_conclusion.cut.cut_action in [Cut_action.BEST_CUTLIST, Cut_action.CHOOSE_CUTLIST]:
                file_conclusion.cut.cutlist.download(self.config.get('general', 'server'), file_conclusion.uncut_video)

            cut_video, ac3_file, error = self.cut_file_by_cutlist(file_conclusion.uncut_video,
                                                                  file_conclusion.cut.cutlist, None)

            if cut_video is None:
                file_conclusion.cut.status = Status.ERROR
                file_conclusion.cut.message = error
                file_conclusion.cut.upload_cutlist = False
            else:
                file_conclusion.cut.status = Status.OK
                file_conclusion.cut_video = cut_video
                file_conclusion.ac3_file = ac3_file

                if self.config.get('general', 'rename_cut'):
                    # rename after cut video, extension could have changed
                    file_conclusion.cut.rename = self.rename_by_schema(
                        basename(file_conclusion.cut_video))
                else:
                    file_conclusion.cut.rename = basename(cut_video)

                if os.path.isfile(file_conclusion.uncut_video + '.ffindex_track00.kf.txt'):
                    os.remove(file_conclusion.uncut_video + '.ffindex_track00.kf.txt')

                if os.path.isfile(file_conclusion.uncut_video + '.ffindex_track00.tc.txt'):
                    os.remove(file_conclusion.uncut_video + '.ffindex_track00.tc.txt')

        return True

    def cut_file_manually(self, filename):
        """ Cuts a file manually with the CutInterface.
            returns: error_message, cutlist """

        global cutlist_error, cuts_frames
        program, config_value, ac3file = self.get_program(filename, manually=True)
        format, ac3_file, bframe_delay,_ = self.get_format(filename)
        fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)

        if error:
            if exists(filename + '.mkv'):
                fileoperations.remove_file(filename + '.mkv')
            return "Konnte FPS nicht bestimmen: " + error, None

        if program < 0:
            return config_value, None

        cutlist = cutlists_management.Cutlist()

        if program == Program.AVIDEMUX:

            cutter = CutAvidemux(self.app, self.gui)
            cuts_frames, cutlist_error = cutter.create_cutlist(filename, config_value)

        elif program == Program.VIRTUALDUB:  # VIRTUALDUB

            cutter = CutVirtualdub(self.app, self.gui)
            cuts_frames, cutlist_error = cutter.create_cutlist(filename, config_value)

        if program == Program.CUT_INTERFACE:
            # looking for latest cutlist, if any
            p, video_file = os.path.split(filename)
            cutregex = re.compile("^" + video_file + "\.?(.*).cutlist$")
            files = os.listdir(p)
            number = -1
            local_cutlist = None  # use fallback name in conclusions if there are no local cutlists
            for f in files:
                match = cutregex.match(f)
                if match:
                    self.log.debug("Found local cutlist {}".format(match.group()))
                    if match.group(1) == '' or match.group(1) == 'mkv':
                        res_num = 0
                    elif "." in match.group(1):
                        res_num = int(match.group(1).split('.')[1])
                    elif type(eval(match.group(1))) == type(1):  # It's a number
                        res_num = int(match.group(1))
                    else:
                        res_num = 0

                    self.log.debug("local cutlist res_num: {}".format(match.group(1)))
                    if res_num > number:
                        res_num = number
                        local_cutlist = p + "/" + match.group()

            ci = CutinterfaceDialog.NewCutinterfaceDialog(self.gui)
            ci.set_transient_for(self.gui.main_window)
            ci.set_modal(True)
            cutlist = ci._run(filename, local_cutlist, self.app)
            ci.destroy()
            # MEMORYLEAK
            # ~ print(f"dir(Cutinterface): {dir(ci)}")
            del ci
            gc.collect()


            if cutlist.cuts_frames is None or len(cutlist.cuts_frames) == 0:
                cutlist_error = "Keine Schnitte angegeben"
            else:
                cutlist_error = None

        else:  # complete cutlist for Avidemux & VirtualDub

            # create cutlist data
            if cutlist_error is None:
                cutlist.cuts_frames = cuts_frames
                cutlist.intended_app = basename(config_value)
                cutlist.usercomment = 'Mit %s geschnitten' % self.app.app_name
                cutlist.fps = fps

                # calculate seconds
                for start_frame, duration_frames in cuts_frames:
                    cutlist.cuts_seconds.append((start_frame / fps, duration_frames / fps))

        if cutlist_error:
            return cutlist_error, None
        else:
            return None, cutlist

    def cut_file_by_cutlist(self, filename, cutlist, program_config_value):
        """ Returns: cut_video, ac3file, error """

        program, program_config_value, ac3file = self.get_program(filename)
        if program < 0:
            return None, None, program_config_value

        # get list of cuts
        error = cutlist.read_cuts()
        if error:
            return None, None, error

        if (cutlist.cuts_frames and cutlist.filename_original != os.path.basename(filename)) \
                                            or (not cutlist.cuts_frames and cutlist.cuts_seconds):
            cutlist.cuts_frames = []
            fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)
            if not error:
                cutlist.fps = fps
            else:
                return None, None, "Konnte FPS nicht bestimmen: " + error
            self.log.info("Calculate frame values from seconds.")
            for start, duration in cutlist.cuts_seconds:
                    cutlist.cuts_frames.append((round(start * cutlist.fps), round(duration * cutlist.fps)))

        if program == Program.AVIDEMUX:
            cutter = CutAvidemux(self.app, self.gui)
            cut_video, error = cutter.cut_file_by_cutlist(filename, cutlist, program_config_value)
            if not error and ac3file is not None and self.config.get('general', 'merge_ac3s'):
                return self.mux_ac3(filename, cut_video, ac3file, cutlist)

        elif program == Program.SMART_MKVMERGE:
            cutter = CutSmartMkvmerge(self.app, self.gui)
            cut_video, error = cutter.cut_file_by_cutlist(filename, cutlist)
            if not error and ac3file is not None:
                return cut_video, ac3file, None

        elif program == Program.VIRTUALDUB:  # VIRTUALDUB
            cutter = CutVirtualdub(self.app, self.gui)
            cut_video, error = cutter.cut_file_by_cutlist(filename, cutlist, program_config_value)
            if not error and ac3file is not None and self.config.get('general', 'merge_ac3s'):
                return self.mux_ac3(filename, cut_video, ac3file, cutlist)

        else:
            return None, None, "Schnittprogramm wird nicht unterstützt"

        if error:
            return None, None, error
        else:
            return cut_video, "", None
