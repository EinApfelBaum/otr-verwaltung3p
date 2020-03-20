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

import os

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import subprocess
import re
import os

from otrverwaltung3p.GeneratorTask import GeneratorTask
from otrverwaltung3p.pluginsystem import Plugin
from otrverwaltung3p import fileoperations
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.constants import Section
from otrverwaltung3p.actions.cut import Cut


class Mkv(Plugin):
    Name = "MKV"
    Desc = "Wandelt Media-Dateien mit Hilfe von mkvmerge in mkv-Dateien um."
    Author = "Benjamin Elbers, monarc99"
    Configurable = True
    Config = {
        'DumpAVIs': True,
        'DumpAVIs_delete': False,
        'EncodeAudioToAAC': False,
        'EncodeOnlyFirstAudioToAAC': True,
        'NormalizeAudio': False,
        'DownMixStereo': True,
        'RemoveOtherAudioStreamsThanAC3': False
    }

    def enable(self):
        self.toolbutton = self.gui.main_window.add_toolbutton(Gtk.Image.new_from_file(
                                                    self.get_path('mkv.png')), 'In Mkv umwandeln',
                                                    [Section.VIDEO_CUT, Section.ARCHIVE,
                                                    Section.VIDEO_UNCUT])
        self.toolbutton.connect('clicked', self.on_mkv_clicked)

    def disable(self):
        self.gui.main_window.remove_toolbutton(self.toolbutton)

    def configurate(self, dialog):
        margin = 30
        dialog.vbox.set_spacing(4)

        # checkbutton callback
        def on_checkbutton_toggled(widget, data=None):
            self.Config[data] = widget.get_active()
            if data == 'EncodeAudioToAAC':
                checkbutton_encode_only_first_audio.set_sensitive(self.Config['EncodeAudioToAAC'])
                checkbutton_downmix_stereo.set_sensitive(self.Config['EncodeAudioToAAC'])
                checkbutton_normalize_audio.set_sensitive(self.Config['EncodeAudioToAAC'])


        # checkbutton for dumping media files
        checkbutton_dump_avis = Gtk.CheckButton("Originaldatei automatisch in Mülleimer verschieben?")
        dialog.vbox.pack_start(checkbutton_dump_avis, expand=False, fill=False, padding=0)
        checkbutton_dump_avis.connect('toggled', on_checkbutton_toggled, 'DumpAVIs')

        # checkbutton for eraseing media file
        checkbutton_dump_avis_delete = Gtk.CheckButton("Originaldatei im Mülleimer gleich für immer löschen?")
        dialog.vbox.pack_start(checkbutton_dump_avis_delete, expand=False, fill=False, padding=0)
        checkbutton_dump_avis_delete.connect('toggled', on_checkbutton_toggled, 'DumpAVIs_delete')

        # checkbutton encode audio aac
        checkbutton_encode_audio = Gtk.CheckButton("Audiospuren zu AAC umwandeln?")
        dialog.vbox.pack_start(checkbutton_encode_audio, expand=False, fill=False, padding=0)
        checkbutton_encode_audio.connect('toggled', on_checkbutton_toggled, 'EncodeAudioToAAC')

        # checkbutton encode first audio only
        checkbutton_encode_only_first_audio = Gtk.CheckButton("AAC: nur erste Audiospur kodieren?")
        checkbutton_encode_only_first_audio.set_margin_left(margin)
        dialog.vbox.pack_start(checkbutton_encode_only_first_audio, expand=False, fill=False, padding=0)
        checkbutton_encode_only_first_audio.connect('toggled', on_checkbutton_toggled, 'EncodeOnlyFirstAudioToAAC')

        # checkbutton down mix first audio stream
        checkbutton_downmix_stereo = Gtk.CheckButton("AAC: erste Audiospur automatisch auf Stereo downmixen?")
        checkbutton_downmix_stereo.set_margin_left(margin)
        dialog.vbox.pack_start(checkbutton_downmix_stereo, expand=False, fill=False, padding=0)
        checkbutton_downmix_stereo.connect('toggled', on_checkbutton_toggled, 'DownMixStereo')

        # checkbutton encode normalize aac
        checkbutton_normalize_audio = Gtk.CheckButton("AAC: Audio bei Konvertierung normalisieren?")
        checkbutton_normalize_audio.set_margin_left(margin)
        dialog.vbox.pack_start(checkbutton_normalize_audio, expand=False, fill=False, padding=0)
        checkbutton_normalize_audio.connect('toggled', on_checkbutton_toggled, 'NormalizeAudio')

        # checkbutton remove other audio streams than ac3_stream
        checkbutton_remove_other_audio_streams_than_ac3 = Gtk.CheckButton(
            "Falls AC3 gefunden wurde, alle Audiospuren außer AC3 entfernen? \n"
            "Die AC3 wird somit erste Spur und wird gegebenenfalls nach AAC konvertiert "
            "und downgemixt, wenn oben angewählt.")
        dialog.vbox.pack_start(checkbutton_remove_other_audio_streams_than_ac3, expand=False, fill=False, padding=0)
        checkbutton_remove_other_audio_streams_than_ac3.connect('toggled', on_checkbutton_toggled,
                                                                'RemoveOtherAudioStreamsThanAC3')

        # current config
        checkbutton_dump_avis.set_active(self.Config['DumpAVIs'])
        checkbutton_dump_avis_delete.set_active(self.Config['DumpAVIs_delete'])
        checkbutton_encode_audio.set_active(self.Config['EncodeAudioToAAC'])
        checkbutton_encode_only_first_audio.set_active(self.Config['EncodeOnlyFirstAudioToAAC'])
        checkbutton_encode_only_first_audio.set_sensitive(self.Config['EncodeAudioToAAC'])
        checkbutton_downmix_stereo.set_active(self.Config['DownMixStereo'])
        checkbutton_downmix_stereo.set_sensitive(self.Config['EncodeAudioToAAC'])
        checkbutton_normalize_audio.set_active(self.Config['NormalizeAudio'])
        checkbutton_normalize_audio.set_sensitive(self.Config['EncodeAudioToAAC'])
        checkbutton_remove_other_audio_streams_than_ac3.set_active(self.Config['RemoveOtherAudioStreamsThanAC3'])

        return dialog

    def on_mkv_clicked(self, widget, data=None):
        filenames = self.gui.main_window.get_selected_filenames()

        if len(filenames) == 0:
            self.gui.message_error_box("Es muss eine Datei markiert sein.")
            return

        self.toolbutton.set_sensitive(False)
        self.gui.main_window.set_tasks_visible(True)
        self.success = 0
        self.errors = {}

        def mkvmerge():
            # env
            my_env = os.environ.copy()
            my_env["LANG"] = "C"

            for count, filename in enumerate(filenames):
                yield 0, count
                yield 3, 0
                self.progress = 0

                # analyse file
                cutter = Cut(self.app, self.gui)
                fps, dar, sar, max_frames, ac3_stream, error = cutter.analyse_mediafile(filename)
                if fps == None:
                    self.errors[filename] = error
                    continue

                # encode aac with ffmpeg
                if self.Config['EncodeAudioToAAC']:
                    # norm volume ausrechnen
                    yield 5, count
                    if self.Config['NormalizeAudio'] and self.Config['EncodeAudioToAAC']:
                        vol, error = self.get_norm_volume(filename)
                    else:
                        vol = 1.0

                    # ffmpeg pass
                    yield 1, count
                    self.progress = 0
                    ffmpegpass_file = fileoperations.make_unique_filename(os.path.splitext(
                                                                    filename)[0] + "_remux.mkv")

                    # convert first audio stream to aac
                    if self.Config['EncodeOnlyFirstAudioToAAC']:
                        aacaudiostreams = '-c:a:0'
                    else:
                        aacaudiostreams = '-c:a'

                    # convert first audio stream to aac
                    ffmpeg = self.app.config.get_program('ffmpeg')
                    if 'nonfree' in ffmpeg:
                        # nonfree ffmpeg version with fdk support available
                        audiocodec = ['-c:a', 'copy', aacaudiostreams, 'libfdk_aac', '-flags', '+qscale',
                                      '-profile:a:0', 'aac_low', '-global_quality', '5', '-afterburner', '1']
                    else:
                        # only gpl version of ffmpeg available -> use standard aac codec
                        audiocodec = ['-c:a', 'copy', aacaudiostreams, 'aac', '-strict', '-2', '-profile:a:0',
                                      'aac_low', '-ab', '192k', '-cutoff', '18000']

                    if self.Config['DownMixStereo'] and self.Config['EncodeAudioToAAC']:
                        audiocodec.extend(['-ac:0', '2'])

                    if ac3_stream == None:
                        # no ac3 stream found - all streams are muxed
                        map = ['-map', '0']
                    else:
                        if self.Config['RemoveOtherAudioStreamsThanAC3']:
                            # mux only video and ac3 stream
                            map = ['-map', '0:v', '-map', ac3_stream]
                        else:
                            map = ['-map', '0']

                    args = [ffmpeg, "-loglevel", "info", "-y", "-drc_scale", "1.0", "-i", filename, "-vn", '-af',
                            'volume=volume=' + str(vol), "-vsync", "1", '-async', '1000', "-dts_delta_threshold", "100",
                            "-vf", "fps=" + str(fps), '-threads', '0', ffmpegpass_file]
                    map.extend(audiocodec)
                    args[8:8] = map

                    try:
                        p = subprocess.Popen(args, stderr=subprocess.PIPE, universal_newlines=True)
                    except OSError:
                        self.errors[filename] = "FFMPEG (intern) wurde nicht gefunden!"
                        continue

                    yield 4, 0
                    line = ""
                    infos_match = re.compile(r"time=(\d{2,}):(\d{2,}):(\d{2,}.\d{2,})")

                    while p.poll() == None:
                        line = p.stderr.readline()
                        m = re.search(infos_match, line)
                        if m and max_frames != 0:
                            frame = (float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))) * fps
                            next = float(frame / float(max_frames)) * 100
                            if next > self.progress:
                                self.progress = next
                                yield 4, self.progress
                        else:
                            pass

                    exit_code = p.poll()

                    if exit_code == 0:
                        pass
                    else:
                        self.errors[filename] = "Fehler beim Erzeugen der MP4 Datei durch FFMPEG"
                        if os.path.exists(ffmpegpass_file):
                            fileoperations.remove_file(ffmpegpass_file)
                        continue

                # mkvmerge pass
                yield 2, count
                self.progress = 0

                # find Umlaute and rename files
                # ~ umlaute = ["ö", "Ö", "ä", "Ä", "ü", "Ü"]
                # ~ umlaute2 = ["oe", "OE", "ae", "AE", "ue", "UE"]
                # ~ for umlaut in umlaute:
                    # ~ if umlaut in filename:
                        # ~ filenameOld = filename
                        # ~ filename = filename.replace(umlaut, umlaute2[umlaute.index(umlaut)])
                        # ~ os.rename(filenameOld, filename)

                mkvpass_file = fileoperations.make_unique_filename(os.path.splitext(filename)[0] + ".mkv")

                if self.Config['EncodeAudioToAAC']:
                    args = [self.app.config.get_program('mkvmerge'), '--engage', 'no_cue_duration', '--engage',
                            'no_cue_relative_position', '--ui-language', 'en_US', "-o", mkvpass_file, '-A', filename,
                            '-D', ffmpegpass_file]
                else:
                    if self.Config['RemoveOtherAudioStreamsThanAC3'] and ac3_stream:
                        args = [self.app.config.get_program('mkvmerge'), '--engage', 'no_cue_duration', '--engage',
                                'no_cue_relative_position', '--ui-language', 'en_US', "-o", mkvpass_file, '-a',
                                ac3_stream[2], filename]
                    else:
                        args = [self.app.config.get_program('mkvmerge'), '--engage', 'no_cue_duration', '--engage',
                                'no_cue_relative_position', '--ui-language', 'en_US', "-o", mkvpass_file, filename]

                p = subprocess.Popen(args, stdout=subprocess.PIPE, env=my_env)
                p.stdout.readline()

                line = ""
                while p.poll() == None:
                    # read progress from stdout
                    char = p.stdout.read(1)
                    line += char.decode('utf-8')

                    progress = ''
                    if line.find('Progress:') != -1:
                        line = ''
                        if "Error" in line or "Warning" in line:
                            break

                        for i in range(6):
                            if char.decode('utf-8') == '%':
                                break
                            char = p.stdout.read(1)
                            progress += char.decode('utf-8')
                        try:
                            print(progress.strip('%'))
                            self.progress = int(progress.strip(' %'))
                            yield 3, self.progress
                        except ValueError:
                            pass

                exit_code = p.poll()

                if exit_code == 0 or exit_code == 1:
                    self.success += 1

                    # find Umlaute and rename files
                    # ~ umlaute = ["ö", "Ö", "ä", "Ä", "ü", "Ü"]
                    # ~ umlaute2 = ["oe", "OE", "ae", "AE", "ue", "UE"]
                    # ~ for umlaut in umlaute2:
                        # ~ if umlaut in mkvpass_file:
                            # ~ mkvpass_fileOld = mkvpass_file
                            # ~ mkvpass_file = mkvpass_file.replace(umlaut, umlaute[umlaute2.index(umlaut)])
                            # ~ os.rename(mkvpass_fileOld, mkvpass_file)

                    if self.Config['EncodeAudioToAAC']:
                        fileoperations.remove_file(ffmpegpass_file)
                    if self.Config['DumpAVIs']:
                        if self.Config['DumpAVIs_delete']:
                            fileoperations.remove_file(filename)
                        else:
                            new_filename = os.path.join(self.app.config.get('general', 'folder_trash_avis'),
                                                        os.path.basename(filename))
                            if os.path.exists(new_filename):
                                fileoperations.remove_file(new_filename)
                            fileoperations.move_file(filename, self.app.config.get('general', 'folder_trash_avis'))
                else:
                    error = p.stdout.readline().decode()
                    try:
                        error = error.split(":")[1]
                    except IndexError:
                        pass

                    if "unknown type" in error:
                        error = "Datei konnte nicht gelesen werden."
                    self.errors[filename] = error

        def loop(state, argument):
            if state == 0:
                self.gui.main_window.set_tasks_text(
                    "Analysiere Datei ... %s/%s" % (str(argument + 1), str(len(filenames))))
            elif state == 1:
                self.gui.main_window.set_tasks_text(
                    "Audiospur in AAC wandeln ... %s/%s" % (str(argument + 1), str(len(filenames))))
            elif state == 2:
                self.gui.main_window.set_tasks_text(
                    "MKV erstellen ...  %s/%s" % (str(argument + 1), str(len(filenames))))
            elif state == 5:
                self.gui.main_window.set_tasks_text(
                    "Normalisierungswert berechnen ... %s/%s" % (str(argument + 1), str(len(filenames))))
            else:
                self.gui.main_window.set_tasks_progress(argument)

        def complete():
            if len(self.errors) == 0:
                self.gui.main_window.change_status(0, "Erfolgreich %s/%s Dateien umgewandelt." % (
                str(self.success), str(len(filenames))))

            else:
                self.gui.main_window.change_status(0, "Erfolgreich %s/%s Dateien umgewandelt. (Fehler: %s)" % (
                str(self.success), str(len(filenames)), " ".join(self.errors.values())))

            self.gui.main_window.set_tasks_visible(False)
            if self.success > 0:
                self.app.show_section(self.app.section)
            self.toolbutton.set_sensitive(True)

        GeneratorTask(mkvmerge, loop, complete).start()

    def get_norm_volume(self, filename):
        """ Gets the volume correction of a movie using ffmpeg and sox.
            Returns without error:
                        norm_vol, None
                    with error:
                        1.0, error_message """

        try:
            process1 = subprocess.Popen(
                [otrvpath.get_tools_path('intern-ffmpeg'), '-loglevel', 'quiet', '-i', filename, '-f', 'sox', '-'],
                stdout=subprocess.PIPE)
        except OSError:
            return "1.0", "FFMPEG wurde nicht gefunden!"

        try:
            process2 = subprocess.Popen([otrvpath.get_tools_path('intern-sox'), '-p', '--null', 'stat', '-v'],
                                        stdin=process1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError:
            return "1.0", "SOX wurde nicht gefunden!"

        log = process2.communicate()[0]

        for line in log.split('\n'):
            try:
                return line, None
            except:
                return "1.0", "Volume konnte nicht bestimmt werden " + line

        return None, "Volume konnte nicht bestimmt werden."
