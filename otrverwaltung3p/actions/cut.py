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
from decimal import Decimal
import bisect
import gc
import logging
import os
import re
import shlex
import subprocess
import sys

from gi import require_version

require_version("Gtk", "3.0")
require_version("Gst", "1.0")
from gi.repository import Gst, Gtk

from otrverwaltung3p import fileoperations
from otrverwaltung3p import path as otrvpath
from otrverwaltung3p.actions.baseaction import BaseAction
from otrverwaltung3p.constants import Format, Program
from otrverwaltung3p.libs.pymediainfo import MediaInfo

import psutil

Gst.init(None)


class Cut(BaseAction):
    format_dict = {
        "Baseline@L1.3": Format.MP4,
        "High@L3": Format.HQ,
        "High@L4": Format.HD,
        "High@L3.0": Format.HQ,
        "High@L3.1": Format.HQ,
        "High@L3.2": Format.HD,
        "Main@L3.2": Format.HD2,
        "Main@L4": Format.HD3,  # gcurse:HD3
        "Main@L3": Format.HD0,
        "Simple@L1": Format.AVI,
    }
    bframe_delays = {
        Format.AVI: 1,
        Format.HD: 2,
        Format.HD0: 1,
        Format.HD2: 0,
        Format.HQ: 2,
        Format.HQ0: 1,
        Format.MP4: 0,
        Format.MP40: 0,
        Format.HD3: 0,  # gcurse:HD3
    }

    def __init__(self, app, gui):
        self.log = logging.getLogger(self.__class__.__name__)
        BaseAction.__init__(self)
        self.update_list = True
        self.app = app
        self.config = app.config
        self.gui = gui
        self.media_info = None

    def cut_file_by_cutlist(self, filename, cutlist, program_config_value):
        raise Exception("Override this method!")

    def create_cutlist(self, filename, program_config_value):
        raise Exception("Override this method!")

    def get_codeccore(self, fname):
        if self.media_info.tracks[1].format_profile and ".HD." in fname:
            if self.media_info.tracks[1].format_profile in ["Main@L3.2", "Main@L4"]:  # New HD2/03 gcurse:HD3
                codeccore = 0
                return codeccore, self.format_dict[self.media_info.tracks[1].format_profile]  # gcurse:HD3

        if not self.media_info.tracks[1].writing_library:
            codeccore = -1
            return codeccore, None
        else:
            match = re.search(r"core [0-9]{2,3}", self.media_info.tracks[1].writing_library)
            if match is not None:
                codeccore = int(match.group(0).split(" ")[1])
            else:
                codeccore = -1
            # try:
            #     codeccore = int(self.media_info.tracks[1].writing_library.split(' ')[3])
            # except (ValueError, IndexError):
            #     try:
            #         codeccore = int(self.media_info.tracks[1].writing_library.split(' ')[2])
            #     except (ValueError, IndexError):
            #         codeccore = -1
            return codeccore, None

    def get_format(self, filename):
        self.log.debug("function start")
        root, extension = os.path.splitext(filename)

        if sys.platform == "win32":
            lib_file = self.config.get_program("mediainfo").replace(".exe", ".dll")
            self.media_info = MediaInfo.parse(filename, library_file=lib_file)
        else:
            self.media_info = MediaInfo.parse(filename)

        codec_core, vformat = self.get_codeccore(filename)  # gcurse:HD3

        self.log.debug(f"get_format:get_codeccore: {codec_core}")
        if self.media_info.tracks[1].width:
            video_width = self.media_info.tracks[1].width
        else:
            video_width = None

        if extension == ".avi":
            if os.path.splitext(root)[1] == ".HQ":
                if codec_core >= 125:
                    vformat = Format.HQ
                    self.log.debug(f"vformat = Format.HQ, value: {Format.HQ}")
                else:  # old OTR file
                    vformat = Format.HQ0
                    self.log.debug(f"vformat = Format.HQ0, value: {Format.HQ0}")
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            elif os.path.splitext(root)[1] == ".HD":
                if codec_core >= 125:
                    vformat = Format.HD
                    self.log.debug(f"vformat = Format.HD, value: {Format.HD}")
                elif codec_core == 0:  # new HD 2020
                    pass  # gcurse:HD3
                    # vformat = Format.HD2
                    # self.log.debug(f"vformat = Format.HD2, value: {Format.HD2}")
                else:  # old OTR file
                    vformat = Format.HD0  # old HD
                    self.log.debug(f"vformat = Format.HD0, value: {Format.HD0}")
                ac3name = root + ".ac3"
            elif os.path.splitext(root)[1] == ".test" and codec_core == 0:
                vformat = Format.HD2
                ac3name = os.path.splitext(root)[0] + ".ac3"
            else:
                vformat = Format.AVI
                ac3name = root + ".HD.ac3"
        elif extension == ".mp4":
            if os.path.splitext(root)[1] == ".HQ":
                vformat = Format.HQ
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            elif os.path.splitext(root)[1] == ".HD":
                vformat = Format.HD
                ac3name = root + ".ac3"
            else:
                if codec_core >= 125:
                    vformat = Format.MP4
                else:
                    vformat = Format.MP40  # old mp4
                ac3name = root + ".HD.ac3"
        elif extension == ".mkv":
            if os.path.splitext(root)[1] == ".HQ":
                if codec_core >= 125:
                    vformat = Format.HQ
                else:  # old OTR file
                    vformat = Format.HQ0
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            elif os.path.splitext(root)[1] == ".HD":
                if codec_core >= 125:
                    vformat = Format.HD
                elif codec_core == 0:
                    pass  # gcurse:HD3, vformat has been determined in get_codeccore()
                    # vformat = Format.HD2
                else:  # old OTR file
                    vformat = Format.HD0  # old HD
                ac3name = root + ".ac3"
            elif os.path.splitext(root)[1] == ".test":
                vformat = Format.HD2
                ac3name = os.path.splitext(root)[0] + ".HD.ac3"
            else:
                format_profile = self.media_info.tracks[1].format_profile
                if " / " in format_profile:
                    format_profile = format_profile.split(" / ")[0]
                try:
                    vformat = self.format_dict[format_profile]
                except KeyError as e:
                    self.log.warning(f"vformatKeyError: {e}")
                    return -1, None, None, None, f"cut.py:185 vformat KeyError: {e}"
                # The format profiles "Baseline@L1.3" and "Main@L3" are ambiguous:
                if vformat == Format.MP4:
                    if codec_core < 125:
                        vformat = Format.MP40
                elif vformat == Format.HD0:
                    if video_width is not None and video_width == 720:
                        vformat = Format.HQ0
                self.log.debug(f"Format: {vformat}")
                ac3name = root + ".HD.ac3"
        elif extension == ".ac3":
            vformat = Format.AC3
            ac3name = root
        else:
            return -1, None, None, None, ""
        if os.path.isfile(ac3name):
            return vformat, ac3name, self.bframe_delays[vformat], codec_core, ""
        else:
            return vformat, None, self.bframe_delays[vformat], codec_core, ""

    def get_program(self, filename, manually=False):
        if manually:
            programs = {
                Format.AVI: self.config.get("general", "cut_avis_man_by"),
                Format.HD0: self.config.get("general", "cut_hqs_man_by"),
                Format.HD2: self.config.get("general", "cut_hd2_man_by"),
                Format.HD3: self.config.get("general", "cut_hd2_man_by"),
                Format.HD: self.config.get("general", "cut_hqs_man_by"),
                Format.HQ0: self.config.get("general", "cut_hqs_man_by"),
                Format.HQ: self.config.get("general", "cut_hqs_man_by"),
                Format.MP4: self.config.get("general", "cut_mp4s_man_by"),
                Format.MP40: self.config.get("general", "cut_mp4s_man_by"),
            }
        else:
            programs = {
                Format.AVI: self.config.get("general", "cut_avis_by"),
                Format.HD0: self.config.get("general", "cut_hqs_by"),
                Format.HD2: self.config.get("general", "cut_hd2_by"),
                Format.HD3: self.config.get("general", "cut_hd2_by"),
                Format.HD: self.config.get("general", "cut_hqs_by"),
                Format.HQ0: self.config.get("general", "cut_hqs_by"),
                Format.HQ: self.config.get("general", "cut_hqs_by"),
                Format.MP4: self.config.get("general", "cut_mp4s_by"),
                Format.MP40: self.config.get("general", "cut_mp4s_by"),
            }

        vformat, ac3, bframe_delay, _, verror = self.get_format(filename)

        if vformat < 0:
            return (
                -1,
                f"Format konnte nicht bestimmt werden/wird (noch) nicht unterstützt.\n {verror}",
                False,
            )

        if vformat == Format.AC3:
            return (
                -1,
                "AC3 wird automatisch mit der HD.avi verarbeitet und nicht einzeln geschnitten.",
                False,
            )

        config_value = programs[vformat]

        if sys.platform == "linux":
            vdub = otrvpath.get_internal_virtualdub_path("vdub.exe")
        elif sys.platform == "win32":
            vdub = self.app.config.get_program("vdub")
            if not (os.path.exists(vdub) and vdub.endswith(vdub.exe)):
                vdub = None
        else:
            vdub = None

        if "avidemux" in config_value:
            return Program.AVIDEMUX, config_value, ac3
        elif "intern-VirtualDub" in config_value:
            return (
                Program.VIRTUALDUB,
                otrvpath.get_internal_virtualdub_path("VirtualDub.exe"),
                ac3,
            )
        elif "intern-vdub" in config_value:
            if vdub is None:
                return (
                    -2,
                    "vdub wurde nicht gefunden. Das Paket 'otr-verwaltung3p-vdub' scheint nicht installiert zu sein",
                    False,
                )
            else:
                return Program.VIRTUALDUB, vdub, ac3
        elif "vdub" in config_value or "VirtualDub" in config_value:
            if vdub is None:
                return (
                    -2,
                    (
                        "'vdub.exe' konnte nicht gefunden werden. Bitte prüfen Sie den Pfad unter "
                        "Einstellungen->Programme->vdub.exe"
                    ),
                    False,
                )
            else:
                return Program.VIRTUALDUB, config_value, ac3
        elif "CutInterface" in config_value and manually:
            return Program.CUT_INTERFACE, config_value, ac3
        elif "SmartMKVmerge" in config_value:
            return Program.SMART_MKVMERGE, config_value, ac3
        else:
            return (
                -2,
                f"Programm '{config_value}' konnte nicht bestimmt werden. " "Es wird nur VirtualDub unterstützt.",
                False,
            )

    def generate_filename(self, filename, forceavi=0):
        """generate filename for a cut video file."""
        root, extension = os.path.splitext(os.path.basename(filename))
        if forceavi == 1:
            extension = ".avi"
        new_name = root + "-cut" + extension
        cut_video = os.path.join(self.config.get("general", "folder_cut_avis"), new_name)
        return cut_video

    def mux_ac3(self, filename, cut_video, ac3_file, cutlist):
        # cuts the ac3 and muxes it with the avi into an mkv
        mkvmerge = self.config.get_program("mkvmerge")
        root, extension = os.path.splitext(filename)
        mkv_file = os.path.splitext(cut_video)[0] + ".mkv"
        # env
        my_env = os.environ.copy()
        my_env["LANG"] = "C"

        # creates the timecodes string for splitting the .ac3 with mkvmerge
        timecodes = ",".join(
            [
                self.seconds_to_hms(start) + "," + self.seconds_to_hms(start + duration)
                for start, duration in cutlist.cuts_seconds
            ]
        )
        # splitting .ac3. Every second fragment will be used.
        # return_value = subprocess.call(
        #     [mkvmerge, "--split", "timecodes:" + timecodes, "-o", root + "-%03d.mka", ac3_file]
        # )
        try:
            blocking_process = subprocess.Popen(
                [
                    mkvmerge,
                    "--ui-language",
                    "en_US",
                    "--split",
                    "timecodes:" + timecodes,
                    "-o",
                    root + "-%03d.mka",
                    ac3_file,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env=my_env,
            )
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
            command[len(command) :] = [
                "+" + root + "-%03d.mka" % (2 * n) for n in range(2, len(cutlist.cuts_seconds) + 1)
            ]
            #            return_value = subprocess.call(command)
            try:
                blocking_process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=my_env,
                )
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
                    # return_value = subprocess.call([mkvmerge, "-o", mkv_file, cut_video, root + ".mka"])
        try:
            blocking_process = subprocess.Popen(
                [mkvmerge, "-o", mkv_file, cut_video, root + ".mka"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env=my_env,
            )
        except OSError as e:
            return None, e.strerror + ": " + mkvmerge
        return_value = blocking_process.wait()
        if return_value != 0 and return_value != 1:
            return None, None, str(return_value)

        fileoperations.remove_file(root + ".mka")  # Delete remaining temporary files
        fileoperations.remove_file(cut_video)
        return mkv_file, ac3_file, None

    @staticmethod
    def seconds_to_hms(seconds, display=False):
        # converts the seconds into a timecode-format that mkvmerge understands
        minute, second = divmod(int(seconds), 60)  # discards milliseconds
        hour, minute = divmod(minute, 60)
        second = seconds - minute * 60 - hour * 3600  # for the milliseconds

        return f"{hour:02d}:{minute:02d}:{second:09.6f}"

    # def analyse_mediafile_old(self, filename):
    #     """Gets fps, dar, sar, number of frames and id of the ac3_stream of a movie using ffmpeg.
    #     Returns without error:
    #         fps, dar, sar, max_frames, ac3_stream, None
    #     with error:
    #         None, None, None, None, None, error_message
    #     """
    #     try:
    #         process = subprocess.Popen(
    #             [self.config.get_program("ffmpeg"), "-hide_banner", "-i", filename],
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.STDOUT,
    #             errors="replace",
    #             universal_newlines=True,
    #         )
    #     except OSError as e:
    #         self.log.warning(f"ffmpeg OSError: {e}")
    #         return (
    #             None,
    #             None,
    #             None,
    #             None,
    #             None,
    #             f"FFMPEG (static) konnte nicht ausgeführt werden!\n(cut.py:426 OSError: {e})",
    #         )
    #
    #     log = process.communicate()[0]
    #
    #     regex_video_infos = (
    #         r".*(Duration).*(\d{1,}):(\d{1,}):(\d{1,}.\d{1,}).*|.*(SAR) "
    #         r"(\d{1,}:\d{1,}) DAR (\d{1,}:\d{1,}).*\, (\d{2,}\.{0,}\d{0,}) "
    #         r"tbr.*|.*(Stream).*(\d{1,}:\d{1,}).*Audio.*ac3.*"
    #     )
    #     video_infos_match = re.compile(regex_video_infos)
    #     seconds = 0
    #     ac3_stream = fps = dar = sar = None
    #
    #     m = None
    #     for line in log.split("\n"):
    #         self.log.debug(line)
    #         m = re.search(video_infos_match, line)
    #
    #         if m:
    #             if "Duration" == m.group(1):
    #                 try:
    #                     seconds = float(m.group(2)) * 3600 + float(m.group(3)) * 60 + float(m.group(4))
    #                 except ValueError:
    #                     self.log.debug("Leave function")
    #                     error = "Dauer des Film konnte nicht ausgelesen werden."
    #                     return None, None, None, None, error
    #             elif "SAR" == m.group(5):
    #                 try:
    #                     sar = m.group(6)
    #                     dar = m.group(7)
    #                     fps = float(m.group(8))
    #                     self.log.debug(f"FPS: {fps}")
    #                 except ValueError:
    #                     self.log.debug("Leave function")
    #                     error = "Video Stream Informationen konnten nicht ausgelesen werden."
    #                     return None, None, None, None, error
    #             elif "Stream" == m.group(9):
    #                 ac3_stream = m.group(10)
    #         else:
    #             pass
    #
    #     if seconds != 0 and fps is not None and sar is not None and dar is not None:
    #         max_frames = round(seconds * fps)
    #         self.log.debug(f"fps: {fps}, dar: {dar}, sar: {sar}, max_frames: {max_frames}, ac3_stream: {ac3_stream}, ")
    #         return fps, dar, sar, max_frames, ac3_stream, None
    #
    #     error = "Es konnten keine Video Infos der zu bearbeitenden Datei ausgelesen werden."
    #     return None, None, None, None, None, error

    def analyse_mediafile(self, filename):
        if not self.media_info:
            _, _, _, _, _ = self.get_format(filename)
        error2 = ""
        duration = 0
        ac3_stream = fps = dar = sar = max_frames = None
        for track in self.media_info.tracks:
            if track.track_type == "Video":
                if int(track.count_of_stream_of_this_kind) > 1:
                    error2 = "\nDie Datei enthält mehr als eine Videospur!"
                    break
                duration = track.duration
                sar = track.pixel_aspect_ratio
                dar = track.display_aspect_ratio
                fps = float(track.frame_rate)
                max_frames = track.frame_count
            elif track.track_type == "Audio":
                if track.format == "AC-3":
                    ac3_stream = f"0:{track.streamorder}"

        if float(duration) > 0 and fps and sar and dar:
            self.log.debug(f"fps: {fps}, dar: {dar}, sar: {sar}, max_frames: {max_frames}, ac3_stream: {ac3_stream}, ")
            return fps, dar, sar, max_frames, ac3_stream, None

        error = ("Fehler beim Auslesen der Videoinformationen." "\n(cut.py:analyze_mediafile:510)") + error2
        return None, None, None, None, None, error

    def get_keyframes_from_file(self, filename, vformat=None):
        """returns keyframe list - in frame numbers"""

        if not os.path.isfile(filename + ".ffindex_track00.kf.txt"):
            try:
                command = [self.config.get_program("ffmsindex"), "-f", "-k", filename]
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, errors="replace", universal_newlines=True
                )
                self.show_indexing_progress(process)
            except OSError:
                return None, "ffmsindex konnte nicht aufgerufen werden."

        if os.path.isfile(filename + ".ffindex_track00.kf.txt"):
            filename_keyframes = filename + ".ffindex_track00.kf.txt"
        elif os.path.isfile(filename + ".ffindex_track01.kf.txt"):
            filename_keyframes = filename + ".ffindex_track01.kf.txt"
        elif os.path.isfile(filename + ".ffindex_track02.kf.txt"):
            filename_keyframes = filename + ".ffindex_track02.kf.txt"
        else:
            filename_keyframes = None

        try:
            index = open(filename_keyframes, "r")
        except (IOError, TypeError) as e:
            self.log.debug(f"{e}")
            return None, f"Keyframe-Datei von ffmsindex konnte nicht geöffnet werden.\n(cut.py:514 {e})"

        index.readline()  # Skip the first line, it is a comment
        index.readline()  # Skip the second line, it is 'fps 0'
        try:
            keyframes_list = [int(i) for i in index.read().splitlines()]
            # with open("/tmp/otrv_kf.txt", "w") as file_:
            #     c = 1
            #     for item in keyframes_list:
            #         file_.write(f"{item}\n")
            #         c += 1
            #         if c == 50:
            #             break
        except ValueError:
            return None, "Keyframes konnten nicht ermittelt werden."
        finally:
            index.close()
        if os.path.isfile(filename + ".ffindex"):
            fileoperations.remove_file(filename + ".ffindex")

        return keyframes_list, None

    def get_timecodes_from_file(self, filename):
        """returns frame->timecode and timecode->frame dict"""

        if not os.path.isfile(filename + ".ffindex_track00.tc.txt"):
            try:
                command = [
                    self.config.get_program("ffmsindex"),
                    "-f",
                    "-c",
                    "-k",
                    filename,
                ]
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, errors="replace", universal_newlines=True
                )
                self.show_indexing_progress(process)
            except OSError:
                return None, "ffmsindex konnte nicht aufgerufen werden."

        if os.path.isfile(filename + ".ffindex_track00.tc.txt"):
            filename_timecodes = filename + ".ffindex_track00.tc.txt"
        elif os.path.isfile(filename + ".ffindex_track01.tc.txt"):
            filename_timecodes = filename + ".ffindex_track01.tc.txt"
        elif os.path.isfile(filename + ".ffindex_track02.tc.txt"):
            filename_timecodes = filename + ".ffindex_track02.tc.txt"
        else:
            filename_timecodes = None

        try:
            index = open(filename_timecodes, "r")
        except (IOError, TypeError) as e:
            self.log.debug(f"{e}")
            return (
                None,
                None,
                "Timecode Datei von ffmsindex konnte nicht geöffnet werden.",
            )
        index.readline()  # Skip the first line, it is a comment
        try:
            frame_timecode = {}
            for line_num, line in enumerate(index):
                frame_timecode[line_num] = int(round(float(line.replace("\n", "").strip()), 2) / 1000 * Gst.SECOND)
            # with open("/tmp/otrv_frame_tc.txt", "w") as file_:
            #     for k, v in frame_timecode.items():
            #         file_.write(f"{k}: {v}\n")
            #         if k == 1000:
            #             break
        except ValueError:
            return None, None, "Timecodes konnten nicht ermittelt werden."
        finally:
            index.close()
            gc.collect()  # MEMORYLEAK
        # DEBUG
        # for index in range(0, 9):
        #     print(f"frame_timcode index: {index}: {frame_timecode[index]}")

        # Generate reverse dict
        timecode_frame = {v: k for k, v in frame_timecode.items()}
        # DEBUG
        # with open("/tmp/otrv_tc_frame.txt", "w") as file_:
        #     for k, v in timecode_frame.items():
        #         file_.write(f"{k} : {v}\n")
        #         if v == 1000:
        #             break
        if os.path.isfile(filename + ".ffindex"):
            fileoperations.remove_file(filename + ".ffindex")

        self.log.debug(f"Number of frames (frame_timecode dict): {list(frame_timecode.keys())[-1] + 1}")
        return frame_timecode, timecode_frame, None

    def show_indexing_progress(self, process):
        """Shows the progress of keyframe/timecode indexing in main_window"""
        self.log.debug("Function start")
        first_run = True
        while process.poll() is None:
            for line in iter(process.stdout.readline, ""):
                if not line or "done" in line:
                    break
                else:
                    dline = line.strip("\n")
                    self.log.debug(f"ffmsindex: {dline}")

                try:
                    if first_run and "Indexing" in line:
                        first_run = False
                        self.app.gui.main_window.set_tasks_text("Datei wird indiziert")

                    if len(line) > 25 and line[25].isdigit():
                        progress = int(line[25:].replace("%", ""))
                        # update progress
                        self.app.gui.main_window.set_tasks_progress(progress)

                    while Gtk.events_pending():
                        Gtk.main_iteration()
                except ValueError:
                    pass

        self.app.gui.main_window.set_tasks_text("")
        self.app.gui.main_window.set_tasks_progress(0)
        return

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
        """

        bt709 = [
            "--videoformat",
            "pal",
            "--colorprim",
            "bt709",
            "--transfer",
            "bt709",
            "--colormatrix",
            "bt709",
        ]
        bt470bg = [
            "--videoformat",
            "pal",
            "--colorprim",
            "bt470bg",
            "--transfer",
            "bt470bg",
            "--colormatrix",
            "bt470bg",
        ]
        try:

            if self.media_info.tracks[1].color_primaries:
                if "709" in self.media_info.tracks[1].color_primaries:
                    x264_opts.extend(bt709)
                elif "470" in self.media_info.tracks[1].color_primaries:
                    x264_opts.extend(bt470bg)
            elif self.media_info.tracks[1].transfer_characteristics:
                if "709" in self.media_info.tracks[1].transfer_characteristics:
                    x264_opts.extend(bt709)
                elif "470" in self.media_info.tracks[1].transfer_characteristics:
                    x264_opts.extend(bt470bg)
            elif self.media_info.tracks[1].matrix_coefficients:
                if "709" in self.media_info.tracks[1].matrix_coefficients:
                    x264_opts.extend(bt709)
                elif "470" in self.media_info.tracks[1].matrix_coefficients:
                    x264_opts.extend(bt470bg)
            elif ".HD." in filename or ".HQ." in filename:
                x264_opts.extend(bt709)

            profile = [
                "--profile",
                self.media_info.tracks[1].format_profile.split("@L")[0].lower(),
            ]
            x264_opts.extend(profile)

            level = ["--level", self.media_info.tracks[1].format_profile.split("@L")[1]]
            x264_opts.extend(level)

            fps = ["--fps", self.media_info.tracks[1].frame_rate.split(" ")[0]]
            x264_opts.extend(fps)
        except IndexError:
            self.log.debug("Mediainfo IndexError. Using old method.")
            try:
                blocking_process = subprocess.Popen(
                    [self.config.get_program("mediainfo"), filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
            except OSError as e:
                return None, f"Fehler: {e.errno}: {e.strerror} Filename: {e.filename}"
            except ValueError as e:
                return None, f"Falscher Wert: {e}"

            while True:
                line = blocking_process.stdout.readline()

                if line != "":
                    if "x264 core" in line:
                        self.log.info(line)
                        try:
                            x264_core = int(line.strip().split(" ")[30])
                        except (ValueError, IndexError):
                            continue
                    elif "Color primaries" in line and "709" in line:
                        x264_opts.extend(bt709)
                    elif "Color primaries" in line and "470" in line:
                        x264_opts.extend(bt470bg)
                    elif "Format profile" in line and "@L" in line:
                        try:
                            level = [
                                "--level",
                                str(float(line.strip().split("L")[1])),
                            ]  # test for float
                            profile = [
                                "--profile",
                                line.strip().split("@L")[0].split(":")[1].lower().lstrip(),
                            ]
                        except (ValueError, IndexError) as e:
                            self.log.debug(f"{e}")
                            continue

                        x264_opts.extend(profile)
                        x264_opts.extend(level)
                    elif "Frame rate" in line:
                        try:
                            fps = ["--fps", str(float(line.strip().split(" ")[3]))]
                            self.log.debug("FPS: {}".format(fps))
                        except (ValueError, IndexError) as e:
                            self.log.debug(f"{e}")
                            continue
                        x264_opts.extend(fps)
                else:
                    break
        return x264_opts

    def complete_ffmpeg_opts(self, ffmpeg_codec_options, filename, quality=None, vformat=None):
        fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)
        codec = None
        ffmpeg_commandline = []
        bt709 = "videoformat=pal:colorprim=bt709:transfer=bt709:colormatrix=bt709"
        bt470bg = "videoformat=pal:colorprim=bt470bg:transfer=bt470bg:colormatrix=bt470bg"

        try:
            if self.media_info.tracks[1].format == "AVC":
                codec = "libx264"
            if self.media_info.tracks[1].color_primaries:
                if "709" in self.media_info.tracks[1].color_primaries:
                    ffmpeg_codec_options += f":{bt709}"
                elif "470" in self.media_info.tracks[1].color_primaries:
                    ffmpeg_codec_options += f":{bt470bg}"
            elif self.media_info.tracks[1].transfer_characteristics:
                if "709" in self.media_info.tracks[1].transfer_characteristics:
                    ffmpeg_codec_options += f":{bt709}"
                elif "470" in self.media_info.tracks[1].transfer_characteristics:
                    ffmpeg_codec_options += f":{bt470bg}"
            elif self.media_info.tracks[1].matrix_coefficients:
                if "709" in self.media_info.tracks[1].matrix_coefficients:
                    ffmpeg_codec_options += f":{bt709}"
                elif "470" in self.media_info.tracks[1].matrix_coefficients:
                    ffmpeg_codec_options += f":{bt470bg}"
            elif ".HD." in filename or ".HQ." in filename:
                ffmpeg_codec_options += f":{bt709}"

            profile = [
                "-profile:v",
                self.media_info.tracks[1].format_profile.split("@L")[0].lower(),
            ]
            ffmpeg_commandline.extend(profile)

            level = [
                "-level",
                self.media_info.tracks[1].format_profile.split("@L")[1].replace(".", ""),
            ]
            ffmpeg_commandline.extend(level)
        except IndexError:
            self.log.debug("Mediainfo IndexError. Using old method.")
            try:
                blocking_process = subprocess.Popen(
                    [self.config.get_program("mediainfo"), filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
            except OSError as e:
                return (
                    None,
                    f"Fehler: {e.errno} Filename: {e.filename} Error: {e.strerror}",
                )
            except ValueError as e:
                return None, f"Falscher Wert: {e}"
            while True:
                line = blocking_process.stdout.readline()

                if line != "":
                    if "x264 core" in line:
                        codec = "libx264"
                        try:
                            codec_core = int(line.strip().split(" ")[30])
                        except (ValueError, IndexError) as e:
                            self.log.debug(f"{e}")
                            continue
                    elif "Matrix coefficients" in line and "709" in line:
                        ffmpeg_codec_options.extend(bt709)
                    elif "Matrix coefficients" in line and "470" in line:
                        ffmpeg_codec_options.extend(bt470bg)
                    elif "Format profile" in line and "@L" in line:
                        try:
                            level = [
                                "-level",
                                str(float(line.strip().split("L")[1])),
                            ]  # test for float
                            profile = [
                                "-profile:v",
                                line.strip().split("@L")[0].split(":")[1].lower().lstrip(),
                            ]
                        except (ValueError, IndexError) as e:
                            self.log.debug(f"{e}")
                            continue
                        ffmpeg_commandline.extend(profile)
                        ffmpeg_commandline.extend(level)
                else:
                    break

        if codec == "libx264":
            # x264opts = ":".join([option for option in ffmpeg_codec_options])
            # x264opts = x264opts.lstrip(":")
            ffmpeg_commandline.extend(["-aspect", dar, "-vcodec", "libx264"])
            ffmpeg_commandline.extend(shlex.split(ffmpeg_codec_options))
            # if vformat and vformat == Format.MP4:
            #     ffmpeg_commandline.extend(
            #         [
            #             "-preset",
            #             "veryfast",
            #             "-x264opts",
            #             x264opts,
            #         ]
            #     )
            # elif vformat and vformat == Format.MP40:
            #     ffmpeg_commandline.extend(
            #         [
            #             "-preset",
            #             "medium",
            #             "-x264opts",
            #             x264opts,
            #         ]
            #     )
            # elif vformat and vformat == Format.HD2:
            #     ffmpeg_commandline.extend(
            #         [
            #             "-preset",
            #             "veryfast",
            #             "-tune",
            #             "film",
            #             "-x264opts",
            #             x264opts,
            #         ]
            #     )
            # elif vformat and vformat == Format.HQ0:
            #     ffmpeg_commandline.extend(
            #         [
            #             "-x264opts",
            #             x264opts,
            #         ]
            #     )
            # else:
            #     ffmpeg_commandline.extend(
            #         [
            #             "-preset",
            #             "medium",
            #             "-tune",
            #             "film",
            #             "-x264opts",
            #             x264opts,
            #         ]
            #     )

        return ffmpeg_commandline

    def show_progress(self, blocking_process):
        # progress_match = re.compile(r".*(?<=\[|\ )(\d{1,}).*%.*")
        progress_match = re.compile(r".*(?<=\[| )(\d+).*%.*")
        time_match = re.compile(r".*(\d+):(\d+):(\d+.\d+).*")
        mp4box_match = re.compile(r".*\((\d{2,})/\d{2,}\).*")
        errors = ""

        max_sec = 0.0

        while True:
            try:
                line = blocking_process.stdout.readline()
                self.log.debug(line.rstrip("\n"))
                if line == "":
                    break
                # elif "error" in line.lower() or "invalid" in line.lower() or "unrecognized" in line.lower():
                elif any(x in line.lower() for x in ["error", "invalid", "unrecognized"]):
                    errors += line  # + "\n"
                # elif "ffms [info]" in line or "Output #0, matroska, to '/tmp/video_encode" in line:
                elif any(x in line.lower() for x in ["ffms [info]", "Output #0, matroska, to '/tmp/video_encode"]):
                    self.app.gui.main_window.set_tasks_text("Kodiere Video")
                    self.app.gui.main_window.set_tasks_progress(0)
                elif "x264 [info]" in line:
                    continue
                elif "time=" in line:
                    m = re.search(time_match, line)
                    if m:
                        sec = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
                        if max_sec >= 1.0:
                            self.app.gui.main_window.set_tasks_progress(int(sec / max_sec * 100))
                elif "%" in line:
                    m = re.search(progress_match, line)
                    if m:
                        self.app.gui.main_window.set_tasks_progress(int(m.group(1)))
                elif "Importing" in line:
                    m = re.search(mp4box_match, line)
                    if m:
                        self.app.gui.main_window.set_tasks_text("Importiere Stream")
                        self.app.gui.main_window.set_tasks_progress(int(m.group(1)))
                elif "ISO File Writing" in line:
                    m = re.search(mp4box_match, line)
                    if m:
                        self.app.gui.main_window.set_tasks_text("Schreibe MP4")
                        self.app.gui.main_window.set_tasks_progress(int(m.group(1)))
                elif "Duration" in line:
                    m = re.search(time_match, line)
                    if m:
                        max_sec = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
                # elif "video_copy" in line and ".mkv' has been opened for writing" in line:
                elif all(x in line.lower() for x in ["video_copy", ".mkv' has been opened for writing"]):
                    self.app.gui.main_window.set_tasks_text("Splitte Video")
                    self.app.gui.main_window.set_tasks_progress(0)
                elif "audio_copy.mkv' has been opened for writing" in line:
                    self.app.gui.main_window.set_tasks_text("Schneide Audio")
                    self.app.gui.main_window.set_tasks_progress(0)
                elif ".mkv' has been opened for writing." in line:
                    self.app.gui.main_window.set_tasks_text("Muxe MKV")
                    self.app.gui.main_window.set_tasks_progress(0)
                elif "ffmpeg version" in line:
                    self.app.gui.main_window.set_tasks_text("Kodiere Audio")
                    self.app.gui.main_window.set_tasks_progress(0)
                else:
                    continue

            except UnicodeDecodeError as e:
                self.log.debug("Execption: {}".format(e))

            while Gtk.events_pending():
                Gtk.main_iteration()
        return errors

    def get_norm_volume(self, filename, stream):
        """Gets the volume correction of a movie using ffprobe.
        Returns without error:
                    norm_vol, None
                with error:
                    1.0, error_message"""

        self.app.gui.main_window.set_tasks_text("Berechne den Normalisierungswert")
        self.app.gui.main_window.set_tasks_progress(0)
        try:
            process1 = subprocess.Popen(
                [
                    self.config.get_program("ffprobe"),
                    "-v",
                    "error",
                    "-of",
                    "compact=p=0:nk=1",
                    "-drc_scale",
                    "1.0",
                    "-show_entries",
                    "frame_tags=lavfi.r128.I",
                    "-f",
                    "lavfi",
                    "amovie=" + filename + ":si=" + stream + ",ebur128=metadata=1",
                ],
                stdout=subprocess.PIPE,
            )
        except OSError:
            return "1.0", "FFPROBE wurde nicht gefunden!"

        log = process1.communicate()[0]
        adjust = None
        loudness = ref = -23
        for line in log.splitlines():
            sline = line.rstrip()
            if sline:
                loudness = sline
                adjust = ref - float(loudness)
        self.app.gui.main_window.set_tasks_progress(100)
        if adjust:
            return str(adjust) + "dB", None
        else:
            return "1.0", "Volume konnte nicht bestimmt werden."

    @staticmethod
    def available_cpu_count():
        """Number of available virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program
        """

        # cpuset may restrict the number of *available* processors
        try:
            m = re.search(r"(?m)^Cpus_allowed:\s*(.*)$", open("/proc/self/status").read())
            if m:
                res = bin(int(m.group(1).replace(",", ""), 16)).count("1")
                if res > 0:
                    return res
        except IOError:
            pass

        try:
            return psutil.cpu_count()
        except AttributeError:
            return 1

    @staticmethod
    def meminfo():
        """return meminfo dict"""

        return psutil.virtual_memory()
