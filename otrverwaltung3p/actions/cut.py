# -*- coding: utf-8 -*-
# BEGIN LICENSE
# Copyright (C) 2013 Markus Liebl <lieblm@web.de>
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
import sys
import re
import subprocess
import bisect
import logging
import psutil
import gc

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst

from otrverwaltung3p.libs.pymediainfo import MediaInfo
from otrverwaltung3p.actions.baseaction import BaseAction
from otrverwaltung3p.constants import Format, Program
from otrverwaltung3p import fileoperations
from otrverwaltung3p import path as otrvpath

Gst.init(None)


class Cut(BaseAction):
    def __init__(self, app, gui):
        self.log = logging.getLogger(self.__class__.__name__)
        BaseAction.__init__(self)
        self.update_list = True
        self.app = app
        self.config = app.config
        self.gui = gui
        self.media_info = None
        self.format_dict = {"High@L4": Format.HD, "High@L3.2": Format.HD, "High@L3.1": Format.HQ,
                            "High@L3.0": Format.HQ, "High@L3": Format.HQ, "Simple@L1": Format.AVI,
                            "Baseline@L1.3": Format.MP4}

    def cut_file_by_cutlist(self, filename, cutlist, program_config_value):
        raise Exception("Override this method!")

    def create_cutlist(self, filename, program_config_value):
        raise Exception("Override this method!")

    def get_codeccore(self):
        try:
            if not "core" in self.media_info.tracks[1].writing_library:
                codeccore = -1
            else:
                try:
                    codeccore = int(self.media_info.tracks[1].writing_library.split(' ')[3])
                except ValueError:
                    try:
                        codeccore = int(self.media_info.tracks[1].writing_library.split(' ')[2])
                    except ValueError:
                        codeccore = -1

            self.log.debug("self.media_info.tracks[1].writing_library: {}".format(
                                                    self.media_info.tracks[1].writing_library))
        except TypeError:
            codeccore = -1
        return codeccore

    def get_format(self, filename):
        self.log.debug("function start")
        global bframe_delay
        root, extension = os.path.splitext(filename)

        if sys.platform == 'win32':
            lib_file = self.config.get_program('mediainfo').replace('.exe', '.dll')
            self.media_info = MediaInfo.parse(filename, library_file=lib_file)
        else:
            self.media_info = MediaInfo.parse(filename)

        codec_core = self.get_codeccore()

        if extension == '.avi':
            bframe_delay = 2
            if os.path.splitext(root)[1] == '.HQ':
                format = Format.HQ
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            elif os.path.splitext(root)[1] == '.HD':
                format = Format.HD
                ac3name = root + ".ac3"
            else:
                format = Format.AVI
                ac3name = root + ".HD.ac3"
        elif extension == '.mp4':
            bframe_delay = 0
            if os.path.splitext(root)[1] == '.HQ':
                format = Format.HQ
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            elif os.path.splitext(root)[1] == '.HD':
                format = Format.HD
                ac3name = root + ".ac3"
            else:
                format = Format.MP4
                ac3name = root + ".HD.ac3"
        elif extension == '.mkv':
            bframe_delay = 2
            if os.path.splitext(root)[1] == '.HQ':
                format = Format.HQ
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            elif os.path.splitext(root)[1] == '.HD':
                format = Format.HD
                ac3name = root + ".ac3"
            else:
                format = self.format_dict[self.media_info.tracks[1].format_profile]
                self.log.debug("Format: {}".format(format))
                ac3name = root + ".HD.ac3"
        elif extension == '.ac3':
            format = Format.AC3
            ac3name = root
        else:
            return -1, None

        if os.path.isfile(ac3name):
            return format, ac3name, bframe_delay, codec_core
        else:
            return format, None, bframe_delay, codec_core

    def get_program(self, filename, manually=False):
        if manually:
            programs = {Format.AVI: self.config.get('general', 'cut_avis_man_by'),
                        Format.HQ: self.config.get('general', 'cut_hqs_man_by'),
                        Format.HD: self.config.get('general', 'cut_hqs_man_by'),
                        Format.MP4: self.config.get('general', 'cut_mp4s_man_by')}
        else:
            programs = {Format.AVI: self.config.get('general', 'cut_avis_by'),
                        Format.HQ: self.config.get('general', 'cut_hqs_by'),
                        Format.HD: self.config.get('general', 'cut_hqs_by'),
                        Format.MP4: self.config.get('general', 'cut_mp4s_by')}

        format, ac3, bframe_delay, _ = self.get_format(filename)

        if format < 0:
            return -1, "Format konnte nicht bestimmt werden/wird (noch) nicht unterstützt.", False

        if format == Format.AC3:
            return -1, "AC3 wird automatisch mit der HD.avi verarbeitet und nicht einzeln geschnitten.", False

        config_value = programs[format]

        _, _, _, codec_core = self.get_format(filename)
        vdub = otrvpath.get_internal_virtualdub_path('vdub.exe')
        x264_codec = self.config.get('general', 'h264_codec')
        if 'avidemux' in config_value:
            return Program.AVIDEMUX, config_value, ac3
        elif 'intern-VirtualDub' in config_value:
            return Program.VIRTUALDUB, otrvpath.get_internal_virtualdub_path('VirtualDub.exe'), ac3
        elif 'intern-vdub' in config_value:
            return Program.VIRTUALDUB, otrvpath.get_internal_virtualdub_path('vdub.exe'), ac3
        elif 'vdub' in config_value or 'VirtualDub' in config_value:
            return Program.VIRTUALDUB, config_value, ac3
        elif 'CutInterface' in config_value and manually:
            return Program.CUT_INTERFACE, config_value, ac3
        elif 'SmartMKVmerge' in config_value:
            if codec_core >= 125 or codec_core == -1 or vdub is None or not x264_codec == 'ffdshow':
                return Program.SMART_MKVMERGE, config_value, ac3
            else:
                return Program.VIRTUALDUB, vdub, ac3
        else:
            return -2, "Programm '%s' konnte nicht bestimmt werden. Es wird nur VirtualDub unterstützt." % config_value, False

    def generate_filename(self, filename, forceavi=0):
        """ generate filename for a cut video file. """

        root, extension = os.path.splitext(os.path.basename(filename))
        if forceavi == 1:
            extension = '.avi'
        new_name = root + "-cut" + extension

        cut_video = os.path.join(self.config.get('general', 'folder_cut_avis'), new_name)

        return cut_video

    def mux_ac3(self, filename, cut_video, ac3_file, cutlist):
        # cuts the ac3 and muxes it with the avi into an mkv
        mkvmerge = self.config.get_program('mkvmerge')
        root, extension = os.path.splitext(filename)
        mkv_file = os.path.splitext(cut_video)[0] + ".mkv"
        # env
        my_env = os.environ.copy()
        my_env["LANG"] = "C"

        # creates the timecodes string for splitting the .ac3 with mkvmerge
        timecodes = (','.join(
            [self.get_timecode(start) + ',' + self.get_timecode(start + duration) for start, duration in
             cutlist.cuts_seconds]))
        # splitting .ac3. Every second fragment will be used.
        # return_value = subprocess.call([mkvmerge, "--split", "timecodes:" + timecodes, "-o",
        #                                                           root + "-%03d.mka", ac3_file])
        try:
            blocking_process = subprocess.Popen(
                [mkvmerge, '--ui-language', 'en_US', "--split", "timecodes:" + timecodes, "-o", root + "-%03d.mka",
                 ac3_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=my_env)
        except OSError as e:
            return None, e.strerror + ": " + mkvmerge
        return_value = blocking_process.wait()
        # return_value=0 is OK, return_value=1 means a warning. Most probably non-ac3-data that
        # has been omitted.
        # TODO: Is there some way to pass this warning to the conclusion dialog?
        if return_value != 0 and return_value != 1:
            return None, None, str(return_value)

        if len(cutlist.cuts_seconds) == 1:  # Only the second fragment is needed. Delete the rest.
            fileoperations.rename_file(root + "-002.mka", root + ".mka")
            fileoperations.remove_file(root + "-001.mka")
            if os.path.isfile(root + "-003.mka"):
                fileoperations.remove_file(root + "-003.mka")

        else:  # Concatenating every second fragment.
            command = [mkvmerge, "-o", root + ".mka", root + "-002.mka"]
            command[len(command):] = ["+" + root + "-%03d.mka" % (2 * n) for n in
                                      range(2, len(cutlist.cuts_seconds) + 1)]
            #            return_value = subprocess.call(command)
            try:
                blocking_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                    universal_newlines=True, env=my_env)
            except OSError as e:
                return None, e.strerror + ": " + mkvmerge
            return_value = blocking_process.wait()
            if return_value != 0:  # There should be no warnings here
                return None, None, str(return_value)

            for n in range(1, 2 * len(cutlist.cuts_seconds) + 2):  # Delete all temporary audio fragments
                if os.path.isfile(root + "-%03d.mka" % n):
                    fileoperations.remove_file(root + "-%03d.mka" % n)

                    # Mux the cut .avi with the resulting audio-file into mkv_file
                    # TODO: Is there some way to pass possible warnings to the conclusion dialog?
                #        return_value = subprocess.call([mkvmerge, "-o", mkv_file, cut_video, root + ".mka"])
        try:
            blocking_process = subprocess.Popen([mkvmerge, "-o", mkv_file, cut_video, root + ".mka"],
                                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, env=my_env)
        except OSError as e:
            return None, e.strerror + ": " + mkvmerge
        return_value = blocking_process.wait()
        if return_value != 0 and return_value != 1:
            return None, None, str(return_value)

        fileoperations.remove_file(root + ".mka")  # Delete remaining temporary files
        fileoperations.remove_file(cut_video)
        return mkv_file, ac3_file, None

    def get_timecode(self, time):
        # converts the seconds into a timecode-format that mkvmerge understands
        minute, second = divmod(int(time), 60)  # discards milliseconds
        hour, minute = divmod(minute, 60)
        second = time - minute * 60 - hour * 3600  # for the milliseconds
        return "%02i:%02i:%f" % (hour, minute, second)

    def analyse_mediafile(self, filename):
        # TODO: gCurse Also get file format through mediainfos "format profile" or ffmpeg.
        """ Gets fps, dar, sar, number of frames and id of the ac3_stream of a movie using ffmpeg.
            Returns without error:
                fps, dar, sar, max_frames, ac3_stream, None
            with error:
                None, None, None, None, None, error_message
        """

        try:
            process = subprocess.Popen([self.config.get_program('ffmpeg'), "-i", filename],
                                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError:
            self.log.debug("Leave function")
            return None, None, None, None, None, "FFMPEG (static) konnte nicht ausgeführt werden!"

        log = process.communicate()[0]

        regex_video_infos = (r".*(Duration).*(\d{1,}):(\d{1,}):(\d{1,}.\d{1,}).*|.*(SAR) "
                             r"(\d{1,}:\d{1,}) DAR (\d{1,}:\d{1,}).*\, (\d{2,}\.{0,}\d{0,}) "
                             r"tbr.*|.*(Stream).*(\d{1,}:\d{1,}).*Audio.*ac3.*")
        video_infos_match = re.compile(regex_video_infos)
        seconds = 0
        ac3_stream = fps = dar = sar = None

        for line in log.split('\n'.encode()):
            #TODO remove try catch
            try:
                m = re.search(video_infos_match, line.decode())
            except UnicodeDecodeError:
                try:
                    m = re.search(video_infos_match, line.decode('latin-1'))
                except UnicodeDecodeError as ex:
                    self.log.error("Exeption: {}".format(ex))

            if m:
                if "Duration" == m.group(1):
                    try:
                        seconds = float(m.group(2)) * 3600 + float(m.group(3)) * 60 + float(m.group(4))
                    except ValueError:
                        self.log.debug("Leave function")
                        error = "Dauer des Film konnte nicht ausgelesen werden."
                        return None, None, None, None, error
                elif "SAR" == m.group(5):
                    try:
                        sar = m.group(6)
                        dar = m.group(7)
                        fps = float(m.group(8))
                        self.log.debug("FPS: {}".format(fps))
                    except ValueError:
                        self.log.debug("Leave function")
                        error = "Video Stream Informationen konnte nicht ausgelesen werden."
                        return None, None, None, None, error
                elif "Stream" == m.group(9):
                    ac3_stream = m.group(10)
            else:
                pass

        self.log.debug("Seconds: {0}, fps: {1}, sar: {2}, dar: {3}".format(seconds, fps, sar, dar))
        if seconds != 0 and fps != None and sar != None and dar != None:
            max_frames = seconds * fps
            self.log.debug("Leave function")
            return fps, dar, sar, max_frames, ac3_stream, None

        self.log.debug("Leave function")
        error = "Es konnten keine Video Infos der zu bearbeitenden Datei ausgelesen werden."
        return None, None, None, None, None, error

    def get_keyframes_from_file(self, filename):
        """ returns keyframe list - in frame numbers"""

        if not os.path.isfile(filename + '.ffindex_track00.kf.txt'):
            try:
                command = [self.config.get_program('ffmsindex'), '-f', '-k', filename]
                process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE)
                self.show_indexing_progress(process)
            except OSError:
                return None, "ffmsindex konnte nicht aufgerufen werden."

        if os.path.isfile(filename + '.ffindex_track00.kf.txt'):
            filename_keyframes = filename + '.ffindex_track00.kf.txt'
        elif os.path.isfile(filename + '.ffindex_track01.kf.txt'):
            filename_keyframes = filename + '.ffindex_track01.kf.txt'
        elif os.path.isfile(filename + '.ffindex_track02.kf.txt'):
            filename_keyframes = filename + '.ffindex_track02.kf.txt'
        else:
            filename_keyframes = None

        try:
            index = open(filename_keyframes, 'r')
        except (IOError, TypeError) as e:
            return None, "Keyframe File von ffmsindex konnte nicht geöffnet werden."

        index.readline()  # Skip the first line, it is a comment
        index.readline()  # Skip the second line, it is 'fps 0'
        try:
            keyframes_list = [int(i) for i in index.read().splitlines()]
        except ValueError:
            return None, "Keyframes konnten nicht ermittelt werden."
        finally:
            index.close()
        if os.path.isfile(filename + '.ffindex'):
            fileoperations.remove_file(filename + '.ffindex')

        return keyframes_list, None

    def get_timecodes_from_file(self, filename):  # TESTING
        """ returns frame->timecode and timecode->frame dict"""

        if not os.path.isfile(filename + '.ffindex_track00.tc.txt'):
            try:
                command = [self.config.get_program('ffmsindex'), '-f', '-c', '-k', filename]
                process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE)
                self.show_indexing_progress(process)
            except OSError:
                return None, "ffmsindex konnte nicht aufgerufen werden."

        if os.path.isfile(filename + '.ffindex_track00.tc.txt'):
            filename_timecodes = filename + '.ffindex_track00.tc.txt'
        elif os.path.isfile(filename + '.ffindex_track01.tc.txt'):
            filename_timecodes = filename + '.ffindex_track01.tc.txt'
        elif os.path.isfile(filename + '.ffindex_track02.tc.txt'):
            filename_timecodes = filename + '.ffindex_track02.tc.txt'
        else:
            filename_timecodes = None

        try:
            index = open(filename_timecodes, 'r')
        except (IOError, TypeError) as e:
            return None, None, "Timecode Datei von ffmsindex konnte nicht geöffnet werden."
        index.readline()
        try:
            frame_timecode = {}
            for line_num, line in enumerate(index, start=0):
                frame_timecode[line_num] = int(round(float(line.replace('\n', '').strip()), 2) / 1000 * Gst.SECOND)
        except ValueError:
            return None, None, "Timecodes konnten nicht ermittelt werden."
        finally:
            index.close()
            gc.collect()  # MEMORYLEAK

        # Generate reverse dict
        timecode_frame = {v: k for k, v in frame_timecode.items()}

        if os.path.isfile(filename + '.ffindex'):
            fileoperations.remove_file(filename + '.ffindex')

        self.log.debug(f"Number of frames (frame_timecode dict): {list(frame_timecode.keys())[-1] + 1}")
        return frame_timecode, timecode_frame, None

    def show_indexing_progress(self, process):
        """ Shows the progress of keyframe/timecode indexing in main_window """
        self.log.debug("Function start")
        first_run = True
        while True:
            l = ""
            while True:
                c = process.stdout.read(1).decode('utf-8')
                if c == "\r" or c == "\n":
                    break
                l += c

            if not l or "done" in l:
                self.log.debug("Outer while break")
                break

            try:
                if first_run and "Indexing" in l:
                    first_run = False
                    self.app.gui.main_window.set_tasks_text("Datei wird indiziert")

                if len(l) > 25 and l[25].isdigit():
                    progress = int(l[25:].replace('%', ''))
                    # update progress
                    self.app.gui.main_window.set_tasks_progress(progress)

                while Gtk.events_pending():
                    Gtk.main_iteration()
            except ValueError:
                pass

        return

    def time_to_frame(self, nanoseconds):  # TESTING
        """
            Searches in dict self.timecode_frame for the nearest timecode
            for the variable 'position' (in nanoseconds) and returns the frame number.
        """
        if nanoseconds in self.timecode_frame:
            return self.timecode_frame[nanoseconds]
        else:
            nearest_position = self.find_closest(self.timecode_frame, nanoseconds)
            # self.log.debug("nearest_position: {}".format(nearest_position))
            return self.timecode_frame[nearest_position]

    def frame_to_time(self, frame_number):  # TESTING
        """
            Returns the time (nanoseconds) for frame_number.
        """
        if frame_number in self.frame_timecode:
            return self.frame_timecode[frame_number]
        else:
            return self.videolength

        return self.timecode_frame[nearest_position]

    def find_closest(self, find_in, position):  # TESTING
        """ Assumes find_in (key_list) is sorted. Returns closest value to position.
            If two numbers are equally close, return the smaller one."""
        key_list = list(find_in.keys())
        pos = bisect.bisect_left(key_list, position)
        if pos == 0:
            return key_list[0]
        if pos == len(key_list):
            return key_list[-1]
        before = key_list[pos - 1]
        after = key_list[pos]
        if after - position < position - before:
           return after
        else:
           return before

    def get_keyframe_in_front_of_frame(self, keyframes, frame):
        """Find keyframe less-than to frame."""

        if frame == 0:
            self.log.debug("Restricting! No keyframe before this position")
            return keyframes[0]
        else:
            i = bisect.bisect_left(keyframes, frame)
            if i:
                return keyframes[i - 1]
            else:
                raise ValueError

    def get_keyframe_after_frame(self, keyframes, frame):
        """Find keyframe greater-than to frame."""

        if frame >= keyframes[-1]:
            self.log.debug("Restricting! No keyframe after this position")
            return keyframes[-1]
        else:
            i = bisect.bisect_right(keyframes, frame)
            if i != len(keyframes):
                return keyframes[i]
            else:
                raise ValueError

    def complete_x264_opts(self, x264_opts, filename):
        """Analyse filename and complete the x264 options
        returns
          x264_opts  x264 options
          x264_core  x264 core version
        """

        global x264_core
        bt709 = ['--videoformat', 'pal', '--colorprim', 'bt709', '--transfer', 'bt709', '--colormatrix', 'bt709']
        bt470bg = ['--videoformat', 'pal', '--colorprim', 'bt470bg', '--transfer', 'bt470bg', '--colormatrix',
                   'bt470bg']

        try:
            x264_core = self.get_codeccore()
            self.log.debug("x264_core: {}".format(x264_core))

            try:
                if '709' in self.media_info.tracks[1].color_primaries:
                    x264_opts.extend(bt709)
                elif '470' in self.media_info.tracks[1].color_primaries:
                    x264_opts.extend(bt470bg)
            except TypeError:
                pass

            level = ['--level', self.media_info.tracks[1].format_profile.split('@L')[1]]
            x264_opts.extend(level)

            profile = ['--profile', self.media_info.tracks[1].format_profile.split('@L')[0].lower()]
            x264_opts.extend(profile)

            fps = ['--fps', self.media_info.tracks[1].frame_rate.split(' ')[0]]
            x264_opts.extend(fps)
        except IndexError:
            self.log.debug("Mediainfo IndexError. Using old method.")
            try:
                blocking_process = subprocess.Popen([self.config.get_program('mediainfo'), filename],
                                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            except OSError as e:
                return None, "Fehler: %s Filename: %s Error: %s" % str(e.errno), str(e.filename), str(e.strerror)
            except ValueError as e:
                return None, "Falscher Wert: %s" % str(e)

            while True:
                line = blocking_process.stdout.readline()

                if line != '':
                    if 'x264 core' in line:
                        self.log.info(line)
                        try:
                            x264_core = int(line.strip().split(' ')[30])
                        except ValueError as e:
                            continue
                        except IndexError as e:
                            continue
                    elif 'Color primaries' in line and '709' in line:
                        x264_opts.extend(bt709)
                    elif 'Color primaries' in line and '470' in line:
                        x264_opts.extend(bt470bg)
                    elif 'Format profile' in line and '@L' in line:
                        try:
                            level = ['--level', str(float(line.strip().split('L')[1]))]  # test for float
                            profile = ['--profile', line.strip().split('@L')[0].split(':')[1].lower().lstrip()]
                        except ValueError as e:
                            continue
                        except IndexError as e:
                            continue
                        x264_opts.extend(profile)
                        x264_opts.extend(level)
                    elif 'Frame rate' in line:
                        try:
                            fps = ['--fps', str(float(line.strip().split(' ')[3]))]
                            self.log.debug("FPS: {}".format(fps))
                        except ValueError as e:
                            continue
                        except IndexError as e:
                            continue
                        x264_opts.extend(fps)
                else:
                    break
        return x264_opts, x264_core

    def ffmpeg_codec_options(self, ffmpeg_codec_options, filename, quality=None):
        fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)
        codec = None
        codec_core = None
        ffmpeg_commandline = []
        bt709 = ['videoformat=pal:colorprim=bt709:transfer=bt709:colormatrix=bt709']
        bt470bg = ['videoformat=pal:colorprim=bt470bg:transfer=bt470bg:colormatrix=bt470bg']

        try:
            codec_core = self.get_codeccore()

            if 'x264' in self.media_info.tracks[1].writing_library:
                codec = 'libx264'
            try:
                if self.media_info.tracks[1].color_primaries:
                    if '709' in self.media_info.tracks[1].color_primaries:
                        ffmpeg_codec_options.extend(bt709)
                    elif '470' in self.media_info.tracks[1].color_primaries:
                        ffmpeg_codec_options.extend(bt470bg)
                elif self.media_info.tracks[1].transfer_characteristics:
                    if '709' in self.media_info.tracks[1].transfer_characteristics:
                        ffmpeg_codec_options.extend(bt709)
                    elif '470' in self.media_info.tracks[1].transfer_characteristics:
                        ffmpeg_codec_options.extend(bt470bg)
                elif self.media_info.tracks[1].matrix_coefficients:
                    if '709' in self.media_info.tracks[1].matrix_coefficients:
                        ffmpeg_codec_options.extend(bt709)
                    elif '470' in self.media_info.tracks[1].matrix_coefficients:
                        ffmpeg_codec_options.extend(bt470bg)
            except TypeError:
                pass
            profile = ['-profile:v', self.media_info.tracks[1].format_profile.split('@L')[0].lower()]
            ffmpeg_commandline.extend(profile)

            level = ['-level', self.media_info.tracks[1].format_profile.split('@L')[1]]
            ffmpeg_commandline.extend(level)
        except IndexError:
            self.log.debug("Mediainfo IndexError. Using old method.")
            try:
                blocking_process = subprocess.Popen([self.config.get_program('mediainfo'), filename],
                                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            except OSError as e:
                return None, "Fehler: %s Filename: %s Error: %s" % str(e.errno), str(e.filename), str(e.strerror)
            except ValueError as e:
                return None, "Falscher Wert: %s" % str(e)
            while True:
                line = blocking_process.stdout.readline()

                if line != '':
                    if 'x264 core' in line:
                        codec = 'libx264'
                        try:
                            codec_core = int(line.strip().split(' ')[30])
                        except ValueError as e:
                            continue
                        except IndexError as e:
                            continue
                    elif 'Matrix coefficients' in line and '709' in line:
                        ffmpeg_codec_options.extend(bt709)
                    elif 'Matrix coefficients' in line and '470' in line:
                        ffmpeg_codec_options.extend(bt470bg)
                    elif 'Format profile' in line and '@L' in line:
                        try:
                            level = ['-level', str(float(line.strip().split('L')[1]))]  # test for float
                            profile = ['-profile:v', line.strip().split('@L')[0].split(':')[1].lower().lstrip()]
                        except ValueError as e:
                            continue
                        except IndexError as e:
                            continue
                        ffmpeg_commandline.extend(profile)
                        ffmpeg_commandline.extend(level)
                else:
                    break

        if codec == 'libx264':
            x264opts = (':'.join([option for option in ffmpeg_codec_options])) + ':force_cfr'
            x264opts = x264opts.lstrip(':')
            if quality and quality == 'MP4':
                ffmpeg_commandline.extend(['-aspect', dar, '-vcodec', 'libx264', '-preset', 'veryfast', '-x264opts', x264opts])
            ## --fade-compensate is no longer available in newer x264 encoders
            else:
                ffmpeg_commandline.extend(['-aspect', dar, '-vcodec', 'libx264', '-preset', 'medium', '-tune', 'film', '-x264opts', x264opts])

        return ffmpeg_commandline, codec_core

    def show_progress(self, blocking_process):
        # progress_match = re.compile(r".*(?<=\[|\ )(\d{1,}).*%.*")
        progress_match = re.compile(r".*(?<=\[| )(\d{1,}).*%.*")
        time_match = re.compile(r".*(\d{1,}):(\d{1,}):(\d{1,}.\d{1,}).*")
        mp4box_match = re.compile(r".*\((\d{2,})\/\d{2,}\).*")

        max_sec = 0.0

        while True:
            try:
                line = blocking_process.stdout.readline()
                logging.debug(line)
                if line == '':
                    break
                elif 'x264 [info]: started' in line:
                    self.app.gui.main_window.set_tasks_text('Kodiere Video')
                    self.app.gui.main_window.set_tasks_progress(0)
                elif 'x264 [info]' in line:
                    continue
                elif 'time=' in line:
                    m = re.search(time_match, line)
                    if m:
                        sec = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
                        if max_sec >= 1.0:
                            self.app.gui.main_window.set_tasks_progress(int(sec / max_sec * 100))
                elif '%' in line:
                    m = re.search(progress_match, line)
                    if m:
                        self.app.gui.main_window.set_tasks_progress(int(m.group(1)))
                elif 'Importing' in line:
                    m = re.search(mp4box_match, line)
                    if m:
                        self.app.gui.main_window.set_tasks_text('Importiere Stream')
                        self.app.gui.main_window.set_tasks_progress(int(m.group(1)))
                elif 'ISO File Writing' in line:
                    m = re.search(mp4box_match, line)
                    if m:
                        self.app.gui.main_window.set_tasks_text('Schreibe MP4')
                        self.app.gui.main_window.set_tasks_progress(int(m.group(1)))
                elif 'Duration' in line:
                    m = re.search(time_match, line)
                    if m:
                        max_sec = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
                elif 'video_copy' in line and '.mkv\' has been opened for writing' in line:
                    self.app.gui.main_window.set_tasks_text('Splitte Video')
                    self.app.gui.main_window.set_tasks_progress(0)
                elif 'audio_copy' in line and '.mkv\' has been opened for writing' in line:
                    self.app.gui.main_window.set_tasks_text('Schneide Audio')
                    self.app.gui.main_window.set_tasks_progress(0)
                elif '.mkv\' has been opened for writing.' in line:
                    self.app.gui.main_window.set_tasks_text('Muxe MKV')
                    self.app.gui.main_window.set_tasks_progress(0)
                elif 'ffmpeg version' in line:
                    self.app.gui.main_window.set_tasks_text('Kodiere Audio')
                    self.app.gui.main_window.set_tasks_progress(0)
                else:
                    continue

            except UnicodeDecodeError as e:
                self.log.debug("Execption: {}".format(e))

            while Gtk.events_pending():
                Gtk.main_iteration()

    def get_norm_volume(self, filename, stream):
        """ Gets the volume correction of a movie using ffprobe.
            Returns without error:
                        norm_vol, None
                    with error:
                        1.0, error_message """

        global adjust
        self.app.gui.main_window.set_tasks_text('Berechne den Normalisierungswert')
        self.app.gui.main_window.set_tasks_progress(0)
        try:
            process1 = subprocess.Popen(
                [otrvpath.get_tools_path('intern-ffprobe'), '-v', 'error', '-of', 'compact=p=0:nk=1', '-drc_scale', '1.0',
                 '-show_entries', 'frame_tags=lavfi.r128.I', '-f', 'lavfi',
                 'amovie=' + filename + ':si=' + stream + ',ebur128=metadata=1'], stdout=subprocess.PIPE)
        except OSError:
            return "1.0", "FFMPEG wurde nicht gefunden!"

        log = process1.communicate()[0]

        loudness = ref = -23
        for line in log.splitlines():
            sline = line.rstrip()
            if sline:
                loudness = sline
                adjust = ref - float(loudness)
        self.app.gui.main_window.set_tasks_progress(100)
        if adjust:
            return str(adjust) + 'dB', None
        else:
            return "1.0", "Volume konnte nicht bestimmt werden."

    def available_cpu_count(self):
        """ Number of available virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program"""

        # cpuset may restrict the number of *available* processors
        try:
            m = re.search(r'(?m)^Cpus_allowed:\s*(.*)$',
                          open('/proc/self/status').read())
            if m:
                res = bin(int(m.group(1).replace(',', ''), 16)).count('1')
                if res > 0:
                    return res
        except IOError:
            pass

        try:
            return psutil.cpu_count()
        except AttributeError:
            return 1

    def meminfo(self):
        """ return meminfo dict """

        return psutil.virtual_memory()
