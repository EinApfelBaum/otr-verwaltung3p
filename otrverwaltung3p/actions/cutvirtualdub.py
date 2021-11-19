# -*- coding: utf-8 -*-
# BEGIN LICENSE
# Copyright (C) 2010 Benjamin Elbers <elbersb@gmail.com>
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
import shutil
import subprocess
import time

from gi import require_version

require_version("Gtk", "3.0")
from gi.repository import Gtk

from otrverwaltung3p import codec
from otrverwaltung3p import fileoperations
from otrverwaltung3p.actions.cut import Cut
from otrverwaltung3p.constants import Format


class CutVirtualdub(Cut):
    def __init__(self, app, gui):
        Cut.__init__(self, app, gui)
        self.update_list = True
        self.app = app
        self.config = app.config
        self.gui = gui

    def __del__(self):
        # clean up
        pass

    def cut_file_by_cutlist(self, filename, cutlist=None, program_config_value=None):
        return self.__cut_file_virtualdub(filename, program_config_value, cutlist.cuts_frames)

    def create_cutlist(self, filename, program_config_value):
        cut_video_is_none, error = self.__cut_file_virtualdub(filename, program_config_value, cuts=None, manually=True)

        if error is not None:
            return None, error
        vformat, ac3_file, bframe_delay, _, _ = self.get_format(filename)
        cuts_frames, cutlist_error = self.__create_cutlist_virtualdub(
            os.path.join(self.config.get("general", "folder_uncut_avis"), "cutlist.vcf"), vformat,
        )

        return cuts_frames, cutlist_error

    def __cut_file_virtualdub(self, filename, config_value, cuts=None, manually=False):
        vformat, ac3_file, bframe_delay, _, _ = self.get_format(filename)
        fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)
        if sar is None or dar is None:
            return None, error

        # find wine
        if shutil.which("wineconsole"):
            winecommand = shutil.which("wineconsole")
        elif shutil.which("wine"):
            winecommand = shutil.which("wine")
        else:
            return None, "Wine konnte nicht aufgerufen werden."

        if vformat == Format.HQ or vformat == Format.HQ0:
            if self.config.get("general", "h264_codec") == "ffdshow":
                if dar == "1.778":
                    comp_data = codec.get_comp_data_h264_169()
                else:
                    comp_data = codec.get_comp_data_h264_43()
                compression = "VirtualDub.video.SetCompression(0x53444646,0,10000,0);\n"
            elif self.config.get("general", "h264_codec") == "x264vfw":
                comp_data = codec.get_comp_data_x264vfw_dynamic(sar, self.config.get("general", "x264vfw_hq_string"))
                compression = "VirtualDub.video.SetCompression(0x34363278,0,10000,0);\n"
            elif self.config.get("general", "h264_codec") == "komisar":
                comp_data = codec.get_comp_data_komisar_dynamic(sar, self.config.get("general", "komisar_hq_string"))
                compression = "VirtualDub.video.SetCompression(0x34363278,0,10000,0);\n"
            else:
                return (
                    None,
                    "Codec nicht unterstützt. Nur ffdshow, x264vfw und komisar unterstützt.",
                )

        elif vformat == Format.HD0 or vformat == Format.HD or vformat == Format.HD2 or vformat == Format.HD3:
            if self.config.get("general", "h264_codec") == "ffdshow":
                if dar == "1.778":
                    comp_data = codec.get_comp_data_hd_169()
                else:
                    comp_data = codec.get_comp_data_hd_43()
                compression = "VirtualDub.video.SetCompression(0x53444646,0,10000,0);\n"
            elif self.config.get("general", "h264_codec") == "x264vfw":
                comp_data = codec.get_comp_data_x264vfw_dynamic(sar, self.config.get("general", "x264vfw_hd_string"))
                compression = "VirtualDub.video.SetCompression(0x34363278,0,10000,0);\n"
            elif self.config.get("general", "h264_codec") == "komisar":
                comp_data = codec.get_comp_data_komisar_dynamic(sar, self.config.get("general", "komisar_hd_string"))
                compression = "VirtualDub.video.SetCompression(0x34363278,0,10000,0);\n"
            else:
                return (
                    None,
                    "Codec nicht unterstützt. Nur ffdshow, x264vfw und komisar unterstützt.",
                )

        elif vformat == Format.MP4:
            if self.config.get("general", "h264_codec") == "komisar":
                comp_data = codec.get_comp_data_komisar_dynamic(sar, self.config.get("general", "komisar_mp4_string"))
                compression = "VirtualDub.video.SetCompression(0x34363278,0,10000,0);\n"
            else:
                comp_data = codec.get_comp_data_x264vfw_dynamic(sar, self.config.get("general", "x264vfw_mp4_string"))
                compression = "VirtualDub.video.SetCompression(0x34363278,0,10000,0);\n"
        elif vformat == Format.AVI:
            comp_data = codec.get_comp_data_dx50()
            compression = "VirtualDub.video.SetCompression(0x53444646,0,10000,0);\n"
        else:
            return (
                None,
                "Format nicht unterstützt (Nur Avi DX50, HQ H264 und HD sind möglich).",
            )

        # make file for virtualdub scripting engine
        if manually:
            curr_dir = os.getcwd()
            try:
                os.chdir(os.path.dirname(config_value))
            except (OSError, TypeError):
                return (
                    None,
                    "VirtualDub konnte nicht aufgerufen werden: " + config_value,
                )

        self.gui.main_window.set_tasks_progress(50)
        while Gtk.events_pending():
            Gtk.main_iteration()

        f = open("/tmp/tmp.vcf", "w")

        if not manually:
            f.write('VirtualDub.Open("%s");\n' % filename)

        if self.config.get("general", "smart"):
            f.writelines(
                [
                    "VirtualDub.video.SetMode(1);\n",
                    "VirtualDub.video.SetSmartRendering(1);\n",
                    compression,
                    "VirtualDub.video.SetCompData(%s);\n" % comp_data,
                ]
            )
        else:
            f.write("VirtualDub.video.SetMode(0);\n")

        f.write("VirtualDub.subset.Clear();\n")

        if not manually:
            keyframes, error = self.get_keyframes_from_file(filename)

            if keyframes is None:
                return None, "Keyframes konnten nicht ausgelesen werden."

            for frame_start, frames_duration in cuts:
                # interval does not begin with keyframe
                if frame_start not in keyframes and (
                    vformat == Format.HQ or vformat == Format.HD or vformat == Format.HD2
                ):
                    try:  # get next keyframe
                        frame_start_keyframe = self.get_keyframe_after_frame(keyframes, frame_start)
                    except ValueError:
                        frame_start_keyframe = -1

                    if frame_start + frames_duration > frame_start_keyframe:
                        # 'Smart Rendering Part mit anschließenden kopierten Part'
                        if frame_start_keyframe < 0:
                            # copy end of file
                            f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start + 2, frames_duration - 2))
                        else:
                            # smart rendering part  (duration -2 due to smart rendering bug)
                            f.write(
                                "VirtualDub.subset.AddRange(%i, %i);\n"
                                % (frame_start + 2, frame_start_keyframe - frame_start - 2,)
                            )
                            # vd smart rendering bug
                            if ac3_file is not None:
                                f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start_keyframe - 1, 1))
                                f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start_keyframe - 1, 1))
                                # copy part
                            f.write(
                                "VirtualDub.subset.AddRange(%i, %i);\n"
                                % (frame_start_keyframe, frames_duration - (frame_start_keyframe - frame_start),)
                            )
                    else:
                        print("reiner Smart Rendering Part")
                        try:  # get next keyframe after the interval
                            next_keyframe = self.get_keyframe_after_frame(keyframes, frame_start + frames_duration - 2)
                        except ValueError:
                            next_keyframe = -1
                        if next_keyframe - (frame_start + frames_duration) > 2:
                            f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start + 2, frames_duration))
                        else:
                            # workaround for smart rendering bug
                            f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start + 2, frames_duration - 2))
                            if ac3_file is not None:
                                f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (next_keyframe - 1, 1))
                                f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (next_keyframe - 1, 1))
                else:
                    if (frame_start + frames_duration) not in keyframes and (
                        vformat == Format.HQ or vformat == Format.HD or vformat == Format.HD2
                    ):
                        # 'Kopieren mit keinem Keyframe am Ende'
                        f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start, frames_duration - 2))
                        # we all love workarounds
                        if ac3_file:
                            f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start + frames_duration - 1, 1))
                            f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start + frames_duration - 1, 1))
                    else:
                        print("reines Kopieren")
                        f.write("VirtualDub.subset.AddRange(%i, %i);\n" % (frame_start, frames_duration))

            cut_video = self.generate_filename(filename, 1)

            f.writelines(['VirtualDub.SaveAVI("%s");\n' % cut_video, "VirtualDub.Close();"])

        f.close()

        # start vdub
        if not os.path.exists(config_value):
            return None, "VirtualDub konnte nicht aufgerufen werden: " + config_value

        if manually:
            win_filename = "Z:" + filename.replace(r"/", r"\\")
            command = 'VirtualDub.exe /s Z:\\\\tmp\\\\tmp.vcf "%s"' % win_filename
        else:
            command = "%s /s Z:\\\\tmp\\\\tmp.vcf /x" % config_value

        if "intern-VirtualDub" in config_value:
            command = "WINEPREFIX=" + os.path.dirname(config_value) + "/wine" + " " + winecommand + " " + command
        else:
            command = winecommand + " " + command

        try:
            vdub = subprocess.Popen(command, shell=True)
        except OSError:
            return None, "VirtualDub konnte nicht aufgerufen werden: " + config_value

        while vdub.poll() is None:
            time.sleep(1)

            while Gtk.events_pending():
                Gtk.main_iteration()

        fileoperations.remove_file("/tmp/tmp.vcf")

        if manually:
            os.chdir(curr_dir)
            return None, None

        return cut_video, None

    @staticmethod
    def __create_cutlist_virtualdub(self, filename, vformat):
        """ returns: cuts, error_message """

        try:
            f = open(filename, "r")
        except IOError:
            return (
                None,
                (
                    "Die VirtualDub-Projektdatei konnte nicht gelesen werden.\n"
                    f"Wurde das Projekt in VirtualDub nicht gespeichert?\n(Datei: {filename})."
                ),
            )

        cuts_frames = []  # (start, duration)

        for line in f.readlines():
            if "VirtualDub.subset.AddRange" in line:
                try:
                    start, duration = line[line.index("(") + 1 : line.index(")")].split(",")
                except (IndexError, ValueError) as message:
                    return (
                        None,
                        f"Konnte Schnitte nicht lesen, um Cutlist zu erstellen. ({message})",
                    )

                if vformat == Format.HQ or vformat == Format.HD or vformat == Format.HD2:
                    cuts_frames.append((int(start) - 2, int(duration)))
                else:
                    cuts_frames.append((int(start), int(duration)))

        if len(cuts_frames) == 0:
            return None, "Konnte keine Schnitte finden!"

        fileoperations.remove_file(filename)

        return cuts_frames, None
