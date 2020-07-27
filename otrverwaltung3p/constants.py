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


class Section:
    """ Die verschiedenen Ansichten """

    PLANNING = 6
    DOWNLOAD = 7
    """ Geplante Sendungen"""
    OTRKEY = 0
    """ Nicht dekodiert """
    VIDEO_UNCUT = 1
    VIDEO_CUT = 2
    ARCHIVE = 3
    TRASH = 4
    TRASH_AVI = 5
    TRASH_OTRKEY = 8


class Action:
    # planning
    PLAN_ADD = 11
    PLAN_REMOVE = 12
    PLAN_EDIT = 13
    PLAN_SEARCH = 14
    # download
    DOWNLOAD_ADD = 16
    DOWNLOAD_ADD_LINK = 17
    DOWNLOAD_START = 18
    DOWNLOAD_STOP = 19
    DOWNLOAD_REMOVE = 20
    # decode and cut
    DECODE = 0
    DECODEANDCUT = 1
    CUT = 2
    # file movement
    DELETE = 3
    ARCHIVE = 4
    RESTORE = 6
    RENAME = 7
    NEW_FOLDER = 8
    REAL_DELETE = 10


class CutAction:
    ASK = 0
    BEST_CUTLIST = 1
    CHOOSE_CUTLIST = 2
    MANUALLY = 3
    LOCAL_CUTLIST = 4


class Status:
    OK = 0
    ERROR = 1
    NOT_DONE = 2


class Format:
    AVI = 0
    HQ = 1
    MP4 = 2
    HD = 3
    AC3 = 4
    HD2 = 5  # new HD 2020
    HQ0 = 6  # old HQ 2011, core < 125
    HD0 = 7  # old HD 2011, core < 125
    MP40 = 8  # old mp4 2011, core < 125

    reverse_dict = {
        0: "AVI",
        1: "HQ",
        2: "MP4",
        3: "HD",
        4: "AC3",
        5: "HD2",
        6: "HQ0",
        7: "HD0",
        8: "MP40",
    }

    @staticmethod
    def to_string(format_constant):
        if format_constant in Format.reverse_dict:
            format_string = Format.reverse_dict[format_constant]
        else:
            format_string = ""
        return format_string


class Program:
    AVIDEMUX = 0
    VIRTUALDUB = 1
    CUT_INTERFACE = 2
    SMART_MKVMERGE = 3


class DownloadTypes:
    TORRENT = 0
    BASIC = 1
    OTR_DECODE = 2
    OTR_CUT = 3


class DownloadStatus:
    RUNNING = 0
    STOPPED = 1
    ERROR = 2
    FINISHED = 3
    SEEDING = 4
