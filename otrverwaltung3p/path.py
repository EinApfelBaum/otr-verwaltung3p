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

from appdirs import AppDirs
import filecmp
import os.path
import shutil
import sys


data_dir = '../data'
dirs = AppDirs("otrverwaltung3p", "")


def getdatapath(*args):
    """Retrieve otrverwaltung data path

    This path is by default <otrverwaltung_lib_path>/../data/ in trunk
    and /usr/share/otrverwaltung in an installed version but this path
    is specified at installation time.
    """
    return os.path.join(os.path.dirname(__file__), data_dir, *args)


def get_storage_dir(filename=""):
    return os.path.join(dirs.user_data_dir, filename)


def get_config_dir(filename=""):
    return os.path.join(dirs.user_config_dir, filename)


def get_path(filename=""):
    return os.path.join(sys.path[0], "otrverwaltung3p", filename)


def get_plugin_paths():
    plugins_home = get_storage_dir("plugins")
    plugins_usr = os.path.join(data_dir, 'plugins')
    return plugins_home, plugins_usr


def get_gui_path(filename=''):
    return os.path.join(get_path(), "gui", filename)


def get_image_path(filename=""):
    return getdatapath("media", filename)


def get_tools_path(filename=""):
    return getdatapath("tools", filename)


def get_internal_virtualdub_path(filename=""):
    if sys.platform == 'win32':
        return None
    vdub_path = getdatapath("tools/intern-VirtualDub", filename)
    if os.path.expanduser("~") in os.path.abspath(sys.path[0]):
        # started from home dir
        if os.path.exists(vdub_path):
            return vdub_path
        else:
            return  None
    else:
        # started from the system
        if os.path.exists(vdub_path):
            if os.path.exists(os.path.join(dirs.user_data_dir, "intern-VirtualDub", 'VERSION')):
                if not filecmp.cmp(getdatapath("tools/intern-VirtualDub", 'VERSION'),
                                   os.path.join(dirs.user_data_dir, "intern-VirtualDub", 'VERSION')):
                    # Version ist nicht aktuell
                    shutil.rmtree(os.path.join(dirs.user_data_dir, "intern-VirtualDub"), ignore_errors=True)
                    shutil.copytree(getdatapath('tools/intern-VirtualDub'),
                                    os.path.join(dirs.user_data_dir, "intern-VirtualDub"), symlinks=True)
            else:
                shutil.copytree(getdatapath('tools/intern-VirtualDub'),
                                os.path.join(dirs.user_data_dir, "intern-VirtualDub"), symlinks=True)

            return os.path.join(dirs.user_data_dir, "intern-VirtualDub", filename)
        else:
            return None
