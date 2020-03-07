# ---BEGIN LICENSE---
# Copyright (C) 2020 Dirk Lorenzen
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
# ---END LICENSE---

import sys
import os
import glob
import fileinput

from setuptools import setup
from setuptools.command.install import install
from setuptools import Distribution


def update_data_path(path=None, oldvalue=None):
    try:
        with fileinput.input('otrverwaltung3p/path.py', inplace=True) as f:
            for line in f:
                if 'data_dir =' in line:
                    if not oldvalue:  # update to prefix, store oldvalue
                        oldvalue = line
                        line = f"data_dir = '{path}'\n"
                    else:  # restore oldvalue
                        line = f"{oldvalue}"
                print(line, end='')

    except (OSError, IOError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    return oldvalue

def create_desktop_file(datadir):
    try:
        with open('otrverwaltung3p.desktop.in', 'r') as f:
            filedata = f.readlines()
        with open('otrverwaltung3p.desktop', 'w') as f:
            for line in filedata:
                if 'Icon=' in line:
                    line = f"Icon={os.path.join(datadir, 'media/icon.png')}\n"
                f.write(line)
    except (OSError, IOError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)


class InstallCommand(install):
    """Pre/Post-installation for installation mode."""

    def run(self):
        dist = Distribution()
        dist.parse_command_line()
        try:
            prefix = dist.get_option_dict('install')['prefix'][1]
        except KeyError:
            prefix = sys.prefix

        prefixed_path = os.path.join(prefix, 'share/otrverwaltung3p')
        previous_datapath = update_data_path(path=prefixed_path)
        create_desktop_file(prefixed_path)

        install.run(self)

        _ = update_data_path(oldvalue=previous_datapath)
        os.remove('otrverwaltung3p.desktop')

    @staticmethod
    def get_version():
        with open('data/VERSION', 'r') as version_file:
            version = version_file.read().strip()
        return version

    @staticmethod
    def get_data_files():
        data_files = [
            ('share/otrverwaltung3p/media', glob.glob("data/media/*.png")),
            ('share/otrverwaltung3p/media', glob.glob("data/media/*.gif")),
            ('share/otrverwaltung3p/plugins', glob.glob("data/plugins/[!_]*.py")),
            ('share/otrverwaltung3p/plugins', glob.glob("data/plugins/[!_]*.png")),
            ('share/otrverwaltung3p/ui', glob.glob("data/ui/[!xml]*")),
            ('share/otrverwaltung3p/ui/xml', glob.glob("data/ui/xml/*.xml")),
            ('share/otrverwaltung3p', ["data/VERSION"]),
            ('share/applications', ["otrverwaltung3p.desktop"])]

        if sys.platform == "linux":
            data_files.append(('share/otrverwaltung3p/tools', glob.glob("data/tools/[!_]*")))

        return data_files


assert sys.version_info[0] == 3, "otr-verwaltung3p is Python 3 only."
# distutils depends on setup.py beeing executed from the same dir.
os.chdir(os.path.dirname(os.path.realpath(__file__)))

setup(
    cmdclass={'install': InstallCommand},
    name='otr-verwaltung3p',
    version=InstallCommand.get_version(),
    description='Dateien von onlinetvrecorder.com verwalten',
    url='https://github.com/EinApfelBaum/otr-verwaltung3p',
    license='GPL-3',
    author='Benjamin Elbers',
    author_email='noone@nowhere.org',
    scripts=['bin/otrverwaltung3p'],
    packages=['otrverwaltung3p', 'otrverwaltung3p.actions', 'otrverwaltung3p.elements', 'otrverwaltung3p.gui',
              'otrverwaltung3p.gui.widgets', 'otrverwaltung3p.libs.pyaes', 'otrverwaltung3p.libs.pymediainfo'],
    data_files=InstallCommand.get_data_files())
