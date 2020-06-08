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

""" Stellt Methoden für Dateioperationen bereit.
Zeigt bei Fehlern einen gtk.MessageDialog an."""

from os.path import join, basename, exists, dirname, splitext
import logging
import os
import shutil

from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk


# TODO: Achten auf :/\* etc. in Dateiname!
# TODO: Fehler abfangen, fehlerwert zurückgeben, damit das Programm weitermachen kann

log = logging.getLogger(__name__)


def __error(message_text):
    dialog = Gtk.MessageDialog(
        None,
        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        Gtk.MessageType.ERROR,
        Gtk.ButtonsType.OK,
        message_text)

    dialog.run()
    dialog.destroy()


def handle_error(error_cb, message):
    if error_cb:
        error_cb(message)
    else:
        log.debug(message)


def remove_file(filename, error_cb=__error):
    """ Entfernt die angegebene Datei. """

    log.debug(f"Remove {filename}")
    try:
        if os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            os.rmdir(filename)
    except Exception as e:
        handle_error(error_cb, f"Fehler beim Löschen von {filename} ({e})")


def rename_file(old_filename, new_filename, error_cb=__error):
    """ Benennt eine Datei um. Wenn die Datei bereits existiert, wird der neue Name um eine Zahl erweitert. """

    if old_filename == new_filename:
        handle_error(error_cb, f"Umbenennen: Die beiden Dateinamen stimmen überein! ({old_filename})")
        return
    new_filename = make_unique_filename(new_filename)
    log.debug(f"Rename {old_filename} to {new_filename}")
    try:
        os.rename(old_filename, new_filename)
    except Exception as e:
        handle_error(error_cb, f"Fehler beim Umbenennen von {old_filename} nach {new_filename} ({e}).")
        return
    return new_filename


def move_file(filename, target, error_cb=__error):
    """ Verschiebt eine Datei in den angegebenen Ordner."""

    new_filename = join(target, basename(filename))
    if exists(new_filename):
        handle_error(error_cb, f"Umbenennen: Die Datei existiert bereits! ({new_filename})")
        return filename
    log.debug(f"Moving {filename} to {target}")
    try:
        os.rename(filename, new_filename)
    except OSError as e:
        try:
            shutil.move(filename, target)
        except Exception as e:
            handle_error(error_cb, f"Fehler beim Verschieben von {filename} nach {target} ({e}). ")
            return filename

    if os.path.isfile(filename + '.cutlist'):
        os.remove(filename + '.cutlist')
    return new_filename


def make_unique_filename(filename):
    """If filename exists a number will be added to it to compose new_filename:
    ex. /path/to/file.name -> /path/to/file.1.name
    """
    new_filename = filename
    count = 1
    while exists(new_filename):
        path, extension = splitext(filename)
        new_filename = f"{path}.{count:d}{extension}"
        count += 1
    return new_filename


def get_size(filename):
    """Returns the file size in bytes."""
    if os.path.isfile(filename):
        filestat = os.stat(filename)
        size = filestat.st_size
    else:
        size = 0
    return size


def get_date(filename):
    """ Gibt das Datum, an dem die Datei zuletzt geändert wurde, zurück."""
    if os.path.isfile(filename):
        filestat = os.stat(filename)
        date = filestat.st_mtime
    else:
        date = 0
    return date
