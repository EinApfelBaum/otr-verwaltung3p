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

import logging
from pathlib import Path
import os
import subprocess
import sys
import tempfile

from gi import require_version
require_version('Gst', '1.0')
from gi.repository import Gst

from otrverwaltung3p.actions.cut import Cut
from otrverwaltung3p.constants import Format


class CutSmartMkvmerge(Cut):
    def __init__(self, app, gui):
        super().__init__(app, gui)
        self.log = logging.getLogger(self.__class__.__name__)
        self.update_list = True
        self.app = app
        self.config = app.config
        self.gui = gui
        self.encode_nr = 0  # index for encoded video parts - for the smart rendering simulation
        self.copy_nr = 0  # index for copied video parts - for the smart rendering simulation
        if not os.path.isdir(self.config.get('smartmkvmerge', 'workingdir').rstrip(os.sep)):
            tmpdir = tempfile.gettempdir()
            self.gui.message_info_box(f"Das in Einstellungen:Schneiden:SmartMKVmerge angegebene "
                                      f"Arbeitsverzeichnis ist nicht gültig.\n"
                                      f"Es wird \"{tmpdir}\" benutzt.")
            self.config.set('smartmkvmerge', 'workingdir', tmpdir)
        self.workingdir = self.config.get('smartmkvmerge', 'workingdir')
        self.video_files = []  # temporary video files
        self.audio_files = []  # temporary audio files
        self.rawstreams = {}  # temporary eac3to files

    # def __del__(self):
    #     # clean up
    #     try:
    #         if os.path.isfile(self.workingdir + '/audio_copy.mkv'):
    #             os.remove(self.workingdir + '/audio_copy.mkv')
    #         if os.path.isfile(self.workingdir + '/x264.index'):
    #             os.remove(self.workingdir + '/x264.index')
    #         if os.path.isfile(self.workingdir + '/video_copy.mkv'):
    #             os.rename(self.workingdir + '/video_copy.mkv', self.workingdir + '/video_copy-001.mkv')
    #         if os.path.isfile(self.workingdir + '/mediainfo.xml'):
    #             os.remove(self.workingdir + '/mediainfo.xml')
    #         for n in self.video_files + self.audio_files:
    #             if os.path.isfile(n.lstrip('+')):
    #                 os.remove(n.lstrip('+'))
    #         if os.path.isfile(self.workingdir + '/audio_encode.mkv'):
    #             os.remove(self.workingdir + '/audio_encode.mkv')
    #         for index in sorted(self.rawstreams.keys()):
    #             if os.path.isfile(self.workingdir + '/' + self.rawstreams[index]):
    #                 os.remove(self.workingdir + '/' + self.rawstreams[index])
    #     except:
    #         pass

    def cut_file_by_cutlist(self, filename, cutlist=None, program_config_value=None):
        """ Cuts a otr file with x264 and mkvmerge frame accurate.
            returns: name of cut video, error_message """
        # configuration
        videolist = []  # result list for smart rendering simulation
        # otr files which have audio streams and needs to be cutted (e.g. OTR avi and ac3)
        audio_import_files = [filename]
        process_list = []  # list of started processes
        mkvmerge_list = []  # list of started mkvmerge processes
        video_splitframes = ''  # mkvmerge split string for cutting the video at keyframes
        audio_timecodes = ''  # mkvmerge split timecodes for cutting the audio
        ac3_file = None  # AC3 source file
        warning_msg = None
        processing_errors = "\n"
        mkvmerge = self.config.get_program('mkvmerge')
        x264 = self.config.get_program('x264')
        ffmpeg = self.config.get_program('ffmpeg')
        encoder_engine = self.config.get('smartmkvmerge', 'encoder_engine')
        # env
        my_env = os.environ.copy()
        my_env["LANG"] = "C"
        my_env["LC_COLLATE"] = "C"
        my_env["LC_ALL"] = "C"

        # analyse file
        fps, dar, sar, max_frames, ac3_stream, error = self.analyse_mediafile(filename)
        if error:
            return None, "Analyse der Datei schlug fehl: " + error

        cutlist.fps = fps
        if not cutlist.cuts_frames:
            for start, duration in cutlist.cuts_seconds:
                cutlist.cuts_frames.append((int(start * cutlist.fps), int(duration * cutlist.fps)))
        elif not cutlist.cuts_seconds:
            for start, duration in cutlist.cuts_frames:
                cutlist.cuts_seconds.append((float(start) / cutlist.fps), (float(duration) / cutlist.fps))
        self.log.debug(f"cutlist.cuts_frames: {cutlist.cuts_frames}")
        self.log.debug(f"cutlist.cuts_seconds: {cutlist.cuts_seconds}")

        # codec configuration string
        _, extension = os.path.splitext(filename)
        hd_offset = [0, 0]
        codec_core = -1
        vformat, ac3_file, bframe_delay, _ = self.get_format(filename)

        if vformat == Format.HQ:
            self.log.debug(f"vformat: HQ")
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(
                    self.config.get('smartmkvmerge', 'x264_hq_string').split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_hq_x264_options').split(' '), filename)
        elif vformat == Format.HQ0:  # HQ 2011/2012 and older
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(
                    self.config.get('smartmkvmerge', 'x264_hq0_string').split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_hq0_x264_options').split(' '), filename, vformat=vformat)
            codec_core = 125  # Fake
        elif vformat == Format.HD:
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(
                    self.config.get('smartmkvmerge', 'x264_hd_string').split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_hd_x264_options').split(' '), filename)
        elif vformat == Format.HD0:
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(
                    self.config.get('smartmkvmerge', 'x264_hd0_string').split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_hd_x264_options').split(' '), filename)
        elif vformat == Format.HD2:
            if extension == '.mkv':
                hd_offset = [0, -1]
            else:
                pass
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(self.config.get('smartmkvmerge', 'x264_hd2_string')
                                                            .split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_hd2_x264_options').split(' '), filename, vformat=vformat)
        elif vformat == Format.MP4:
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(
                    self.config.get('smartmkvmerge', 'x264_mp4_string').split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_mp4_x264_options').split(' '), filename, quality='MP4')
        elif vformat == Format.MP40:
            if encoder_engine == 'x264':
                codec, codec_core = self.complete_x264_opts(
                    self.config.get('smartmkvmerge', 'x264_mp40_string').split(' '), filename)
            elif encoder_engine == 'ffmpeg':
                codec, codec_core = self.complete_ffmpeg_opts(
                    self.config.get('smartmkvmerge', 'ffmpeg_mp4_x264_options').split(' '), filename, quality='MP4')
            codec_core = 125  # Fake
        elif vformat == Format.AVI:
            encoder_engine = 'ffmpeg'
            codec = self.config.get('smartmkvmerge', 'ffmpeg_avi_mpeg4_options').split(' ')
            codec_core = 125  # Fake
        else:
            return None, f"Format nicht unterstützt (Nur MP4 H264, HQ H264 und HD H264 sind möglich)."

        if codec_core == -1:
            warning_msg = "TODO Die Datei kann nicht geschnitten werden, da die Kodiermethode unbekannt ist."
            return None, warning_msg

        # test workingdir
        if os.access(self.config.get('smartmkvmerge', 'workingdir').rstrip(os.sep), os.W_OK):
            self.workingdir = os.path.abspath(self.config.get('smartmkvmerge', 'workingdir')).rstrip('/')
        else:
            return None, "Ungültiges Temp Verzeichnis. Schreiben nicht möglich."

        # threads
        flag_singlethread = self.config.get('smartmkvmerge', 'single_threaded')

        if self.config.get('smartmkvmerge', 'single_threaded_automatic'):
            try:
                memory = self.meminfo()
                if self.available_cpu_count() > 1 and memory.free > os.stat(filename).st_size:
                    flag_singlethread = True
                else:
                    flag_singlethread = False
            except Exception as e:
                flag_singlethread = self.config.get('smartmkvmerge', 'single_threaded')

        self.log.debug(f"flag_singlethread: {flag_singlethread}")

        # audio part 1 - cut audio
        if ac3_file:
            audio_import_files.append(ac3_file)

        audio_timecodes = (',+'.join([self.seconds_to_hms(start) + '-' + self.seconds_to_hms(start + duration)
                                      for start, duration in cutlist.cuts_seconds]))
        audio_timecodes = audio_timecodes.lstrip(',+')

        command = [mkvmerge, '-D', '--split', 'parts:' + audio_timecodes, '-o',
                   self.workingdir + '/audio_copy.mkv'] + audio_import_files
        self.log.debug(f"Command: {command}")
        try:
            blocking_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, env=my_env)
        except OSError as e:
            return None, e.strerror + ": " + mkvmerge
        mkvmerge_list.append(blocking_process)
        if flag_singlethread:
            processing_errors += self.show_progress(blocking_process)

        # video part 1 - read keyframes
        keyframes, error = self.get_keyframes_from_file(filename)
        if keyframes is None:
            return None, "Keyframes konnten nicht ausgelesen werden." + "\n" + error

        # video part 2 - simulate smart rendering process
        for frame_start, frames_duration in cutlist.cuts_frames:
            result = self.__simulate_smart_mkvmerge(int(frame_start), int(frames_duration), keyframes)
            if result is not None:
                videolist += result
            else:
                return None, ('Cutlist oder zu schneidende Datei passen nicht zusammen oder sind fehlerhaft.'
                              'cutsmartmkvmerge:230:Result of __simulate_smart_mkvmerge is None')
        self.log.debug(f"video part 2:Videolist: {videolist}")

        # video part 3 - encode small parts - smart rendering part (1/2)
        for encode, start, duration, video_part_filename in videolist:
            self.video_files.append('+' + self.workingdir + '/' + video_part_filename)
            if encoder_engine == 'x264':
                command = [x264] + codec + ['--demuxer', 'ffms', '--index', self.workingdir + '/x264.index',
                                            '--seek', str(start + hd_offset[0]), '--frames', str(duration + hd_offset[1]),
                                            '--output', self.workingdir + '/' + video_part_filename, filename]
            elif encoder_engine == 'ffmpeg':
                command = [ffmpeg, '-hide_banner', '-ss', str(self.seconds_to_hms((start + bframe_delay) / fps)),
                           '-i', filename, '-vframes', str(duration), '-vf', 'setsar=' + str(sar),
                           '-threads', '0', '-an', '-sn', '-dn', '-y', self.workingdir + '/' + video_part_filename]
                command[6:6] = codec  # insert list 'codec' at position 6, i.e. after 'filename'
            else:
                return None, "Keine unterstützte Render-Engine zum Kodieren eingestellt"
            self.log.debug(f"Command: {command}")
            if encode:
                try:
                    non_blocking_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                            universal_newlines=True)
                except OSError as e:
                    return None, e.strerror + ": " + 'Render Engine nicht vorhanden'
                process_list.append(non_blocking_process)
                if flag_singlethread:
                    processing_errors += self.show_progress(non_blocking_process)
            else:
                video_splitframes += ',' + str(start) + '-' + str(duration)
                self.log.debug(f"video_splitframes: {video_splitframes}")

        self.video_files[0] = self.video_files[0].lstrip('+')
        video_splitframes = video_splitframes.lstrip(',')

        # video part 4 - cut the big parts out the file (keyframe accurate)
        # smart rendering part (2/2)
        if video_splitframes:
            command = [mkvmerge, '-A', '--split', 'parts-frames:' + video_splitframes, '-o', self.workingdir +
                       '/video_copy.mkv', filename]
            self.log.debug(f"Command: {command}")
            try:
                non_blocking_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                        universal_newlines=True, env=my_env)
            except OSError as e:
                return None, e.strerror + ": " + mkvmerge
            mkvmerge_list.append(non_blocking_process)
            if flag_singlethread:
                processing_errors += self.show_progress(non_blocking_process)

        # audio part 2 - encode audio to AAC
        mp3copy = 'MP3 Spur kopieren' in self.config.get('smartmkvmerge', 'first_audio_stream')
        ac3copy = 'AC3 Spur kopieren' in self.config.get('smartmkvmerge', 'second_audio_stream')
        if mp3copy and ac3copy:
            self.audio_files.append(self.workingdir + '/audio_copy.mkv')
        else:
            processing_errors += self.show_progress(blocking_process)
            blocking_process.wait()
            ffmpeginput_file = self.workingdir + '/audio_copy.mkv'
            ffmpegoutput_file = self.workingdir + '/audio_encode.mkv'

            audiofilter = []
            # convert first audio stream to aac
            if 'AAC' in self.config.get('smartmkvmerge', 'first_audio_stream') and 'AAC' in self.config.get(
                    'smartmkvmerge', 'second_audio_stream'):
                aacaudiostreams = '-c:a'
                if self.config.get('smartmkvmerge', 'normalize_audio'):
                    vol0, error = self.get_norm_volume(ffmpeginput_file, '0')
                    vol1, error = self.get_norm_volume(ffmpeginput_file, '1')
                    audiofilter = ['-af:0', 'volume=volume=' + vol0, '-af:1', 'volume=volume=' + vol1]
            elif 'AAC' in self.config.get('smartmkvmerge', 'second_audio_stream') and 'MP3' in self.config.get(
                    'smartmkvmerge', 'first_audio_stream'):
                aacaudiostreams = '-c:a:1'
                if self.config.get('smartmkvmerge', 'normalize_audio'):
                    vol, error = self.get_norm_volume(ffmpeginput_file, '1')
                    audiofilter = ['-af:1', 'volume=volume=' + vol]
            elif 'AAC' in self.config.get('smartmkvmerge', 'first_audio_stream'):
                aacaudiostreams = '-c:a:0'
                if self.config.get('smartmkvmerge', 'normalize_audio'):
                    vol, error = self.get_norm_volume(ffmpeginput_file, '0')
                    audiofilter = ['-af:0', 'volume=volume=' + vol]
            else:
                aacaudiostreams = '-c:a:2'

            if 'nonfree' in ffmpeg:
                # nonfree ffmpeg version with fdk support available
                audiocodec = ['-c:a', 'copy', aacaudiostreams, 'libfdk_aac', '-flags', '+qscale', '-profile:a',
                              'aac_low', '-global_quality', '5', '-afterburner', '1']
            else:
                # only gpl version of ffmpeg available -> use standard aac codec
                audiocodec = ['-c:a', 'copy', aacaudiostreams, 'aac', '-strict', '-2', '-profile:a', 'aac_low', '-ab',
                              '192k', '-cutoff', '18000']

            if '2-Kanal' in self.config.get('smartmkvmerge', 'first_audio_stream'):
                audiocodec.extend(['-ac:0', '2'])

            if ac3_file is None:
                # no ac3 stream found - all streams are muxed
                map = ['-map', '0']
            else:
                if 'AC3' in self.config.get('smartmkvmerge', 'first_audio_stream'):
                    map = ['-map', '0:a:1']
                else:
                    map = ['-map', '0:a:0']
                if not 'AC3 Spur entfernen' in self.config.get('smartmkvmerge', 'second_audio_stream'):
                    map.extend(['-map', '0:a:1'])

            args = [ffmpeg, "-loglevel", "info", "-y", "-drc_scale", "1.0", "-i", ffmpeginput_file, "-vn", "-vsync",
                    "1", '-async', '200000', "-dts_delta_threshold", "100", '-threads', '0', ffmpegoutput_file]
            map.extend(audiocodec)
            map.extend(audiofilter)
            args[8:8] = map
            self.log.debug(f"Args: {args}")
            try:
                non_blocking_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                        universal_newlines=True)
            except OSError as e:
                return None, e.strerror + ": " + ffmpeg
            process_list.append(non_blocking_process)
            self.audio_files.append(self.workingdir + '/audio_encode.mkv')
            if flag_singlethread:
                processing_errors += self.show_progress(non_blocking_process)

        # wait until all threads are terminated
        for blocking_process in mkvmerge_list + process_list:
            processing_errors += self.show_progress(blocking_process)

        # check all processes
        for blocking_process in mkvmerge_list:
            returncode = blocking_process.wait()
            if returncode != 0 and returncode != 1:
                return None, 'beim Schneiden der Originaldatei...' + processing_errors
        for blocking_process in process_list:
            returncode = blocking_process.wait()
            if returncode != 0:
                return None, 'beim Kodieren ...' + processing_errors

        # clean up
        if os.path.isfile(self.workingdir + '/video_copy.mkv'):
            os.rename(self.workingdir + '/video_copy.mkv', self.workingdir + '/video_copy-001.mkv')
        if 'ffmpeginput_file' in vars():
            if os.path.isfile(ffmpeginput_file):
                os.remove(ffmpeginput_file)

        # mux all together
        if self.config.get('smartmkvmerge', 'remux_to_mp4'):
            cut_video = self.workingdir + '/' + os.path.basename(
                os.path.splitext(self.generate_filename(filename, 1))[0] + ".mkv")
        else:
            cut_video = os.path.splitext(self.generate_filename(filename, 1))[0] + ".mkv"

        command = [mkvmerge, '--engage', 'no_cue_duration', '--engage', 'no_cue_relative_position',
                   '-o', cut_video] + self.video_files + self.audio_files
        self.log.debug(f"Command: {command}")
        try:
            blocking_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, env=my_env)
        except OSError:
            return None, "MKVMerge konnte nicht aufgerufen werden oder zu alt (6.5.0 benötigt)"

        processing_errors += self.show_progress(blocking_process)
        returncode = blocking_process.wait()
        if returncode != 0 and returncode != 1:
            return None, 'beim Schreiben des geschnittenen MKVs...' + processing_errors

        # remove all temporary files
        for n in self.video_files + self.audio_files:
            if os.path.isfile(n.lstrip('+')):
                os.remove(n.lstrip('+'))
            if os.path.isfile(os.path.join(self.workingdir, 'x264.index')):
                os.remove(os.path.join(self.workingdir, 'x264.index'))

        # mux to mp4
        if self.config.get('smartmkvmerge', 'remux_to_mp4'):
            self.log.debug("Start muxing to MP4")
            """
            # split files with eac3to
            with ChangeDir(self.workingdir):
                command = ['wine', path.get_tools_path('intern-eac3to/eac3to.exe'),
                            os.path.basename(cut_video), '-demux', '-silence', '-keepDialnorm']
                self.log.debug("Command: {}".format(command))
                try:
                    blocking_process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, universal_newlines=True)
                except OSError:
                    return None, 'Eac3to konnte nicht aufgerufen werden'

                file_match = re.compile(r".*\"(.* - (\d{1,}) - .*)\".*")
                self.gui.main_window.set_tasks_text('Extrahiere Streams')
                self.gui.main_window.set_tasks_progress(50)
                while Gtk.events_pending():
                    Gtk.main_iteration()

                while blocking_process.poll() == None:
                    line = blocking_process.stdout.readline().strip()
                    if 'Creating file' in line:
                        m = re.search(file_match, line)
                        if m:
                            self.rawstreams[m.group(2)] = m.group(1)
                        else:
                            pass

                returncode = blocking_process.wait()
                if returncode != 0:
                    if os.path.isfile(cut_video):
                        os.remove(cut_video)
                    return None, 'Fehler beim Extrahieren der Streams mit Eac3to' + processing_errors

                # remove mkv + log file
                if os.path.isfile(cut_video):
                    os.remove(cut_video)
                if os.path.isfile(os.path.splitext(cut_video)[0] + ' - Log.txt'):
                    os.remove(os.path.splitext(cut_video)[0] + ' - Log.txt')

                args = [self.config.get_program('mp4box'), '-new', '-keep-all', '-isma', '-inter', '500']

                for index in sorted(self.rawstreams.keys()):
                    args.append('-add')
                    if '.dx50' in self.rawstreams[index]:
                        (root_dx50, dx50) = os.path.splitext(self.rawstreams[index])
                        os.rename(self.rawstreams[index], root_dx50 + '.m4v')
                        self.rawstreams[index] = root_dx50 + '.m4v'
                    args.append(self.rawstreams[index])

                cut_video = os.path.splitext(self.generate_filename(filename, 1))[0] + ".mp4"
                args.append(cut_video)

                # mux to mp4 (mp4box)
                self.log.debug("Args: {}".format(args))
                try:
                    blocking_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                        universal_newlines=True)
                except OSError:
                    return None, 'MP4Box konnte nicht aufgerufen werden'

                self.gui.main_window.set_tasks_text('Muxe MP4')
                processing_errors += self.show_progress(blocking_process)
                returncode = blocking_process.wait()
                if returncode != 0:
                    return None, 'Fehler beim Erstellen der MP4' + processing_errors
                """

            args = [self.config.get_program('ffmpeg'), '-i', cut_video, '-c', 'copy']
            tmp_video = cut_video
            cut_video = os.path.splitext(self.generate_filename(filename, 1))[0] + ".mp4"
            args.append(cut_video)

            self.gui.main_window.set_tasks_text('Muxe MP4')
            try:
                blocking_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                    universal_newlines=True)
            except OSError:
                return None, 'ffmpeg konnte nicht aufgerufen werden'

            processing_errors += self.show_progress(blocking_process)
            returncode = blocking_process.wait()
            if os.path.isfile(tmp_video):
                os.remove(tmp_video)
            if returncode != 0:
                return None, 'Fehler beim Erstellen der MP4' + processing_errors

        return cut_video, warning_msg

    def __simulate_smart_mkvmerge(self, start, duration, keyframes):
        end = start + duration
        if start in keyframes:
            if end in keyframes:
                if end <= start:
                    return
                # copy keyframe to keyframe
                self.copy_nr += 1
                return [(False, start + 1, end + 1, 'video_copy-{:03}.mkv'.format(self.copy_nr))]
            else:
                # copy to keyframe before end
                try:
                    lt_kf_before_end = self.get_keyframe_in_front_of_frame(keyframes, end)
                except:
                    return None
                if lt_kf_before_end <= start:
                    self.encode_nr += 1
                    encode = [(True, start, duration, 'video_encode-{:03}.mkv'.format(self.encode_nr))]
                    return encode
                else:
                    self.copy_nr += 1
                    copy = [(False, start + 1, lt_kf_before_end + 1, 'video_copy-{:03}.mkv'.format(self.copy_nr))]
                    # encode to end of interval
                    self.encode_nr += 1
                    encode = [(True, lt_kf_before_end, end - lt_kf_before_end,
                               'video_encode-{:03}.mkv'.format(self.encode_nr))]
                    return copy + encode
        else:
            try:
                nt_kf_from_start = self.get_keyframe_after_frame(keyframes, start)
            except:
                return None
            duration_nt_kf = nt_kf_from_start - start
            if end <= nt_kf_from_start:
                self.encode_nr += 1
                encode = [(True, start, duration, 'video_encode-{:03}.mkv'.format(self.encode_nr))]
                return encode
            else:
                self.encode_nr += 1
                encode = [(True, start, duration_nt_kf, 'video_encode-{:03}.mkv'.format(self.encode_nr))]
                if duration - duration_nt_kf > 0:
                    result = self.__simulate_smart_mkvmerge(nt_kf_from_start, duration - duration_nt_kf, keyframes)
                    if result is not None:
                        return encode + result
                    else:
                        return None
                else:
                    return encode


class ChangeDir:
    def __init__(self, new_path):
        self.new_path = new_path

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.saved_path)
