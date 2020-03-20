# BEGIN LICENSE
# Copyright (C) 2020 Dirk Lorenzen <gcurse@web.de>
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
from gi.repository import Gio

from otrverwaltung3p.constants import Section

class DirectoryMonitor:
    def __init__(self, app, monitored_dir, section, file_regex):
        self.app = app
        self.section = section
        self.monitored_dir = Gio.File.new_for_path(monitored_dir)
        self.file_regex = file_regex

    def start(self):
        self.monitor = self.monitored_dir.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect('changed', self.directory_changed)

    def directory_changed(self, monitor, file1, file2, event_type):
        if self.app.section == self.section:
            unwanted_event_types = [Gio.FileMonitorEvent.ATTRIBUTE_CHANGED,
                                    Gio.FileMonitorEvent.CHANGES_DONE_HINT]
            # ~ unwanted_file_extensions = ['.cutlist', '.txt', '.ac3']
            filename_ok = False if file1 is None else self.file_regex.match(file1.get_basename())

            if event_type not in unwanted_event_types and filename_ok:
                self.app.show_section(self.app.section)
