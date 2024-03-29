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

import gc
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


from otrverwaltung3p import cutlists as cutlists_management
from otrverwaltung3p import fileoperations
from otrverwaltung3p.GeneratorTask import GeneratorTask
from otrverwaltung3p.actions.cut import Cut
from otrverwaltung3p.actions.cutavidemux import CutAvidemux
from otrverwaltung3p.actions.cutsmartmkvmerge import CutSmartMkvmerge
from otrverwaltung3p.actions.cutvirtualdub import CutVirtualdub
from otrverwaltung3p.conclusions import FileConclusion
from otrverwaltung3p.constants import Action, CutAction, Program, Status
from otrverwaltung3p.gui import CutinterfaceDialog, LoadCutDialog


class DecodeOrCut(Cut):
    def __init__(self, app, gui):
        super().__init__(app, gui)
        self.log = logging.getLogger(self.__class__.__name__)
        self.app = app
        self.config = app.config
        self.cutlists_error = False
        self.download_error = False
        self.download_first_try = True
        self.rename_by_schema = self.app.rename_by_schema
        self.update_list = True

    def do(self, action, filenames, cut_action=None):

        decode, cut = False, False

        # prepare tasks
        if action == Action.DECODE:
            self.app.gui.main_window.set_tasks_text("Dekodieren")
            decode = True
        elif action == Action.CUT:
            self.app.gui.main_window.set_tasks_text("Schneiden")
            cut = True
        else:  # decode and cut
            self.app.gui.main_window.set_tasks_text("Dekodieren/Schneiden")
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
            if not self.decode(file_conclusions):
                return

        # cut files
        if cut:
            if not self.cut(file_conclusions, action, default_cut_action=cut_action):
                return

        self.app.gui.main_window.block_gui(False)

        # no more need for tasks view
        self.app.gui.main_window.set_tasks_visible(False)

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
                self.app.gui.main_window.change_status(
                    0, "%i Datei(en) erfolgreich dekodiert" % len(file_conclusions), permanent=True,
                )

        # Decode and cut - always show
        else:
            show_conclusions = True

        if show_conclusions:
            self.app.conclusions_manager.add_conclusions(*file_conclusions)

    def decode(self, file_conclusions):
        self.log.debug(f"Decoder: {self.config.get('programs', 'decoder')}")
        verify = self.config.get("general", "verify_decoded")
        # no decoder
        # --> otrtool
        if not any(i in self.config.get("programs", "decoder") for i in ["decode", "otrtool"]):
            # no decoder specified
            self.app.gui.message_error_box("Es ist kein korrekter Dekoder angegeben!")
            return False
        elif self.config.get_program("decoder") == "otrtool" and not shutil.which("otrtool"):
            # otrtool not found in path
            self.app.gui.message_error_box("Der Dekoder otrtool ist ausgewählt, wurde aber nicht im Pfad gefunden!")
            return False
        elif "/" in self.config.get_program("decoder"):  # It's an external program
            if not shutil.which(self.config.get_program("decoder")):  # File doen't exist or is not executable
                self.app.gui.message_error_box("Der externe Dekoder wurde nicht gefunden oder ist nicht ausführbar.")
                return False
        # <-- otrtool

        # retrieve email and password
        email = self.config.get("general", "email")
        password = self.config.get("general", "password")

        if not email or not password:
            self.app.gui.dialog_email_password.set_email_password(email, password)

            # let the user type in his data through a dialog
            response = self.app.gui.dialog_email_password.run()
            self.app.gui.dialog_email_password.hide()

            if response == Gtk.ResponseType.OK:
                (email, password, store_passwd, config,) = self.app.gui.dialog_email_password.get_email_password()
                if store_passwd:
                    config.set("general", "password", password)
            else:  # user pressed cancel
                return False

        # now this method may not return "False"
        self.app.gui.main_window.set_tasks_visible(True)
        self.app.gui.main_window.block_gui(True)

        # decode each file
        for count, file_conclusion in enumerate(file_conclusions):
            # update progress
            self.app.gui.main_window.set_tasks_text(f"Datei {count + 1}/{len(file_conclusions)} dekodieren")

            # --> otrtool
            if "otrtool" in self.config.get_program("decoder"):
                command = [
                    Path(self.config.get_program("decoder")),
                    "-x",
                    "-g",
                    "-e",
                    email,
                    "-p",
                    password,
                    # "-O",
                    # Path(self.config.get("general", "folder_uncut_avis")) / Path(file_conclusion.otrkey).stem,
                    "-D",
                    self.config.get("general", "folder_uncut_avis"),
                    file_conclusion.otrkey,
                ]
            else:
                command = [
                    Path(self.config.get_program("decoder")),
                    "-e",
                    email,
                    "-p",
                    password,
                    "-o",
                    self.config.get("general", "folder_uncut_avis"),
                    "-i",
                    file_conclusion.otrkey,
                ]
                if not verify:
                    command.insert(7, "-q")
                self.log.debug(f"decoder command: {command}")
            # <-- otrtool

            try:
                process = subprocess.Popen(
                    # command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, errors="replace",
                    # universal_newlines=True,
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    errors="replace",
                    universal_newlines=True,
                )
            except OSError:
                file_conclusion.decode.status = Status.ERROR
                file_conclusion.decode.message = "Dekoder wurde nicht gefunden."
                continue

            # --> otrtool
            if "otrtool" in self.config.get_program("decoder"):
                error_message = ""
                file_count = count + 1, len(file_conclusions)
                # list of non error strings
                nonerror = [
                    "OK",
                    "gui",
                    "OTR-Tool, ",
                    "Keyphrase from",
                    "Keyphrase:",
                    "Decrypting",
                    "Trying to contact",
                    "Server responded",
                    "info:",
                    "warning:",
                ]
                while process.poll() is None:
                    for line in iter(process.stderr.readline, ""):
                        if not line:
                            break
                        else:
                            dline = line.strip("\n")
                            self.log.debug(f"otrtool: {dline}")
                        # Gathering errors
                        if not any(x in line for x in nonerror):
                            error_message += line.strip() + "\n"

                        if "Decrypting" in line:
                            self.app.gui.main_window.set_tasks_text(
                                f"Datei {file_count[0]}/{file_count[1]} dekodieren und prüfen"
                            )

                        if ("gui" in line) and not ("Finished" in line):
                            progress = int(line[5:])
                            # update progress
                            self.app.gui.main_window.set_tasks_progress(progress)

                        while Gtk.events_pending():
                            Gtk.main_iteration()
            # <-- otrtool
            else:
                # while True:
                while process.poll() is None:
                    for line in iter(process.stdout.readline, ""):
                        # line = ""
                        # while True:
                        #     c = process.stdout.read(1)
                        #     if c == "\r" or c == "\n":
                        #         break
                        #     line += c
                        if not line:
                            break
                        else:
                            dline = line.strip("\n")
                            self.log.debug(f"decoder: {dline}")

                        try:
                            if verify:
                                file_count = count + 1, len(file_conclusions)

                                if "input" in line:
                                    self.app.gui.main_window.set_tasks_text(
                                        f"Eingabedatei {file_count[0]}/{file_count[1]} kontrollieren"
                                    )
                                elif "output" in line:
                                    self.app.gui.main_window.set_tasks_text(
                                        f"Ausgabedatei {file_count[0]}/{file_count[1]} kontrollieren"
                                    )
                                elif "Decoding" in line:
                                    self.app.gui.main_window.set_tasks_text(
                                        f"Datei {file_count[0]}/{file_count[1]} dekodieren"
                                    )

                            if len(line) > 13 and line[12].isdigit():
                                progress = int(line[10:13])
                                # update progress
                                self.app.gui.main_window.set_tasks_progress(progress)

                            while Gtk.events_pending():
                                Gtk.main_iteration()
                        except ValueError:
                            pass

                # errors?
                errors = process.stderr.readlines()
                error_message = ""
                for error in errors:
                    if "libmediaclient" not in error:
                        error_message += error.strip() + "\n"

            self.log.debug(f"Decoder returncode: {process.returncode}")
            if process.returncode != 0:
                if process.returncode == -11:
                    error_message += f"Dekoder Returncode: Segmentation fault ({process.returncode})"
                else:
                    error_message += f"Dekoder Returncode: {process.returncode}"
            if error_message == "":  # dekodieren erfolgreich
                file_conclusion.decode.status = Status.OK
                file_conclusion.uncut_video = str(
                    Path(self.config.get("general", "folder_uncut_avis")) / Path(file_conclusion.otrkey).stem
                )

                # move otrkey to trash
                if self.config.get("general", "move_otrkey_to_trash_after_decode"):
                    target = self.config.get("general", "folder_trash_otrkeys")
                    fileoperations.move_file(file_conclusion.otrkey, target)
            else:
                file_conclusion.decode.status = Status.ERROR
                # try:
                #     str(error_message)
                # except UnicodeDecodeError:
                #     error_message = str(error_message, "iso-8859-1")
                file_conclusion.decode.message = error_message

        return True

    def cut(self, file_conclusions, action, default_cut_action=None):
        # now this method may not return "False"
        self.app.gui.main_window.set_tasks_visible(True)
        self.app.gui.main_window.block_gui(True)

        if default_cut_action is None:
            default_cut_action = self.config.get("general", "cut_action")

        for count, file_conclusion in enumerate(file_conclusions):
            self.app.gui.main_window.set_tasks_text(f"Cutlist {count + 1}/{len(file_conclusions)} wählen")
            self.app.gui.main_window.set_tasks_progress((count + 1) / float(len(file_conclusions)) * 100)

            # file correctly decoded?
            if action == Action.DECODEANDCUT:
                if file_conclusion.decode.status != Status.OK:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Datei wurde nicht dekodiert."
                    continue

            file_conclusion.cut.cut_action = default_cut_action

            if default_cut_action in [CutAction.ASK, CutAction.CHOOSE_CUTLIST]:
                # show dialog
                self.app.gui.dialog_cut.setup(
                    file_conclusion.uncut_video,
                    self.config.get("general", "folder_cut_avis"),
                    default_cut_action == CutAction.ASK,
                )

                cutlists = []

                def error_cb(error):
                    if error == "Keine Cutlists gefunden" and self.download_first_try:
                        self.download_first_try = False
                        self.app.gui.dialog_cut.builder.get_object("label_status").set_markup(
                            "<b>%s</b>" % error + ". Versuche es mit allen Qualitäten"
                        )
                        download_generator(True)
                    else:
                        self.app.gui.dialog_cut.builder.get_object("label_status").set_markup("")
                        self.app.gui.dialog_cut.builder.get_object("label_status").set_markup(
                            "<b>%s</b>" % error + " (Es wurde nach allen Qualitäten gesucht)"
                        )
                        self.cutlists_error = True
                        self.download_first_try = True

                def cutlist_found_cb(cutlist):
                    self.app.gui.dialog_cut.add_cutlist(cutlist)
                    cutlists.append(cutlist)

                def completed():
                    if not self.cutlists_error:
                        self.app.gui.dialog_cut.builder.get_object("label_status").set_markup("")

                def download_generator(get_all_qualities):
                    self.download_error = False

                    GeneratorTask(cutlists_management.download_cutlists, None, completed).start(
                        file_conclusion.uncut_video,
                        self.config.get("general", "server"),
                        self.config.get("general", "choose_cutlists_by"),
                        self.config.get("general", "cutlist_mp4_as_hq"),
                        error_cb,
                        cutlist_found_cb,
                        get_all_qualities,
                    )

                download_generator(False)
                # Run the dialog_cut
                response = self.app.gui.dialog_cut.run()
                self.app.gui.dialog_cut.hide()

                if response < 0:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Abgebrochen."
                else:  # change cut_action accordingly
                    file_conclusion.cut.cut_action = response

            if file_conclusion.cut.cut_action == CutAction.MANUALLY:  # MANUALLY
                error_message, cutlist = self.cut_file_manually(file_conclusion.uncut_video)

                if not error_message:
                    file_conclusion.cut.create_cutlist = True
                    file_conclusion.cut.upload_cutlist = True
                    file_conclusion.cut.cutlist = cutlist
                else:
                    self.log.debug(f"Error message: {error_message}")
                    file_conclusion.cut.message = error_message
                    if error_message == "Keine Schnitte angegeben":
                        self.log.info(f"Error message CutinterfaceDialog: {error_message}")
                        file_conclusion.cut.status = Status.NOT_DONE
                    else:
                        file_conclusion.cut.status = Status.ERROR
                        file_conclusion.cut.message = error_message

            elif file_conclusion.cut.cut_action == CutAction.BEST_CUTLIST:
                error, cutlists = cutlists_management.download_cutlists(
                    file_conclusion.uncut_video,
                    self.config.get("general", "server"),
                    self.config.get("general", "choose_cutlists_by"),
                    self.config.get("general", "cutlist_mp4_as_hq"),
                )

                if error:
                    file_conclusion.cut.status = Status.ERROR
                    file_conclusion.cut.message = error
                    continue

                if len(cutlists) == 0:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Keine Cutlist gefunden."
                    continue

                file_conclusion.cut.cutlist = cutlists_management.get_best_cutlist(cutlists)

            elif file_conclusion.cut.cut_action == CutAction.CHOOSE_CUTLIST:
                if self.app.gui.dialog_cut.chosen_cutlist is not None:
                    file_conclusion.cut.cutlist = self.app.gui.dialog_cut.chosen_cutlist
                else:
                    file_conclusion.cut.status = Status.NOT_DONE
                    file_conclusion.cut.message = "Keine Cutlist gefunden."

            elif file_conclusion.cut.cut_action == CutAction.LOCAL_CUTLIST:
                file_conclusion.cut.cutlist.local_filename = file_conclusion.uncut_video + ".cutlist"
                if not Path(file_conclusion.cut.cutlist.local_filename).is_file():
                    file_conclusion.cut.status = Status.ERROR
                    file_conclusion.cut.message = "Keine lokale Cutlist gefunden."
                else:
                    file_conclusion.cut.cutlist.read_from_file()

            elif file_conclusion.cut.cut_action == CutAction.ASK:
                file_conclusion.cut.status = Status.NOT_DONE
                file_conclusion.cut.message = "Keine Cutlist gefunden."

        # and finally cut the file
        for count, file_conclusion in enumerate(file_conclusions):
            if file_conclusion.cut.status in [Status.NOT_DONE, Status.ERROR]:
                try:
                    self.app.filenames_locked.remove(file_conclusion.uncut_video)
                except ValueError:
                    pass

                continue

            self.log.info(f"[Decodeandcut] Datei {file_conclusion.uncut_video} wird geschnitten")
            self.app.gui.main_window.set_tasks_text(f"Datei {count + 1}/{len(file_conclusions)} schneiden")
            self.app.gui.main_window.set_tasks_progress(0)
            while Gtk.events_pending():
                Gtk.main_iteration()

            # download cutlist
            if file_conclusion.cut.cut_action in [
                CutAction.BEST_CUTLIST,
                CutAction.CHOOSE_CUTLIST,
            ]:
                file_conclusion.cut.cutlist.download(self.config.get("general", "server"), file_conclusion.uncut_video)

            cut_video, ac3_file, error = self.cut_file_by_cutlist(
                file_conclusion.uncut_video, file_conclusion.cut.cutlist, None
            )

            if cut_video is None:
                file_conclusion.cut.status = Status.ERROR
                file_conclusion.cut.message = error
                file_conclusion.cut.upload_cutlist = False
            else:
                file_conclusion.cut.status = Status.OK
                file_conclusion.cut_video = cut_video
                file_conclusion.ac3_file = ac3_file

                if self.config.get("general", "rename_cut"):
                    # rename after cut video, extension could have changed
                    file_conclusion.cut.rename = self.rename_by_schema(Path(file_conclusion.cut_video).name)
                else:
                    file_conclusion.cut.rename = Path(cut_video).name

        return True

    def cut_file_manually(self, filename):
        """ Cuts a file manually with the CutInterface.
            returns: error_message, cutlist """

        cutlist_error, cuts_frames = None, None
        program, config_value, ac3file = self.get_program(filename, manually=True)
        _, ac3_file, _, _, _ = self.get_format(filename)
        fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)

        if error:
            if Path(filename + ".mkv").is_file():
                fileoperations.remove_file(filename + ".mkv")
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
            self.app.gui.main_window.set_tasks_text("")
            self.app.gui.main_window.set_tasks_progress(0)
            self.app.file_to_recut = None
            # looking for latest cutlist, if any
            filename = Path(filename)
            cutregex = re.compile("^" + filename.name + r"\.?(.*).cutlist$")
            files = [e for e in filename.parent.iterdir() if e.is_file()]
            number = res_num = -1
            local_cutlist = None  # use fallback name in conclusions if there are no local cutlists
            for f in files:
                match = cutregex.match(f.name)
                if match:
                    try:
                        if match.group(1) == "":
                            res_num = 0
                        else:
                            res_num = int(match.group(1))
                    except Exception as e:
                        self.log.error(f"Presumably found cutlist with invalid name. Ignoring.({e})")
                        break

                    if res_num > number:
                        number = res_num
                        local_cutlist = str(f)

            self.log.debug(f"local cutlist: {local_cutlist}")

            self.app.gui.ci_instance = CutinterfaceDialog.new()
            self.app.gui.ci_instance.set_transient_for(self.app.gui.main_window)
            self.app.gui.ci_instance.set_modal(True)
            self.app.gui.main_window.get_window().set_cursor(self.app.gui.cursor_wait)
            cutlist = self.app.gui.ci_instance.run_(filename, local_cutlist, self.app)
            self.app.gui.ci_instance.destroy()
            self.app.gui.main_window.get_window().set_cursor(None)
            # MEMORYLEAK
            del self.app.gui.ci_instance
            gc.collect()

            if cutlist.cuts_frames is None or len(cutlist.cuts_frames) == 0:
                cutlist_error = "Keine Schnitte angegeben"
            else:
                cutlist_error = None

        else:  # complete cutlist for Avidemux & VirtualDub

            # create cutlist data
            if cutlist_error is None:
                cutlist.cuts_frames = cuts_frames
                cutlist.intended_app = Path(config_value).name
                cutlist.usercomment = f"Mit {self.app.app_name} geschnitten"
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

        if (cutlist.cuts_frames and cutlist.filename_original != Path(filename).name) or (
            not cutlist.cuts_frames and cutlist.cuts_seconds
        ):
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
            if not error and ac3file is not None and self.config.get("general", "merge_ac3s"):
                return self.mux_ac3(filename, cut_video, ac3file, cutlist)

        elif program == Program.SMART_MKVMERGE:
            self.app.gui.main_window.get_window().set_cursor(self.app.gui.cursor_wait)
            cutter = CutSmartMkvmerge(self.app, self.gui)
            cut_video, error = cutter.cut_file_by_cutlist(filename, cutlist)
            self.app.gui.main_window.get_window().set_cursor(None)
            if not error and ac3file is not None:
                return cut_video, ac3file, None

        elif program == Program.VIRTUALDUB:  # VIRTUALDUB
            self.app.gui.main_window.get_window().set_cursor(self.app.gui.cursor_wait)
            cutter = CutVirtualdub(self.app, self.gui)
            cut_video, error = cutter.cut_file_by_cutlist(filename, cutlist, program_config_value)
            self.app.gui.main_window.get_window().set_cursor(None)
            if not error and ac3file is not None and self.config.get("general", "merge_ac3s"):
                return self.mux_ac3(filename, cut_video, ac3file, cutlist)

        else:
            return None, None, "Schnittprogramm wird nicht unterstützt"

        if error:
            return None, None, error
        else:
            return cut_video, "", None
