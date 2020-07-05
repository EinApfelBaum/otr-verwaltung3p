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

import hashlib
import logging
import os
import requests
import shutil
import sys
import urllib.request as urllib2

from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk, Pango

from otrverwaltung3p.constants import Cut_action
from otrverwaltung3p.gui.config_bindings import EntryBinding, FileChooserFolderBinding, \
                        CheckButtonBinding, ComboBoxEntryBinding, RadioButtonsBinding, \
                        SpinbuttonBinding, TextbufferBinding
from otrverwaltung3p import path as otrvpath

progs = ["ffmpeg", "ffprobe", "ffmsindex", "mediainfo", "mkvmerge", "mpv"]


class PreferencesWindow(Gtk.Window, Gtk.Buildable):
    __gtype_name__ = "PreferencesWindow"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.app = None
        self.builder = None
        self.css = b"""
                    .font_larger { font-size: larger; }
                    .font_smaller { font-size: smaller; }
                    .font_bold { font-weight: bold; }
                    """
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(self.css)
        self.example_filename = 'James_Bond_007_09.01.06_20-15_ard_120_TVOON_DE.mpg.HQ.avi'
        self.example_cut_filename = 'James_Bond_007_09.01.06_20-15_ard_120_TVOON_DE.mpg.HQ-cut.avi'
        self.filechooser_title_setup = {'entry_folder_new_otrkeys': 'Ordner für neue otrkey-Dateien',
                                        'entry_folder_uncut_avis': 'Ordner für ungeschnittene Avis',
                                        'entry_folder_cut_avis': 'Ordner für geschnittene Avis',
                                        'entry_folder_trash_otrkeys': 'Müllorder für otrkey-Dateien',
                                        'entry_folder_trash_avis': 'Müllorder für Avis',
                                        'entry_folder_archive': 'Archiv Ordner',
                                        'entry_prog_ffmpeg': 'Öffne ffmpeg',
                                        'entry_prog_ffprobe': 'Öffne ffprobe',
                                        'entry_prog_ffmsindex': 'Öffne ffmsindex',
                                        'entry_prog_mediainfo': 'Öffne mediainfo',
                                        'entry_prog_mkvmerge': 'Öffne mkvmerge',
                                        'entry_prog_mpv': 'Öffne mpv',
                                        'entry_prog_decoder': 'Öffne otrdecoder',
                                        'entry_folder_wineprefix': 'Wineprefix für vdub.exe'}
        self.last_path = None

    def obj(self, objectname):
        return self.builder.get_object(objectname)

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

    def bind_config(self, app):
        self.app = app
        # If stored decoder is not in the standard list (see PreferenceWindow.glade)
        # it will be prepended and set as active entry.
        entries = []
        if sys.platform == 'linux':
            entries = ['intern-easydecoder']
            if shutil.which('otrtool'):
                entries.append('otrtool')
            for entry in entries:
                self.obj('entry_prog_decoder').append(entry, entry)
        decoder_value = self.app.config.get('programs', 'decoder')
        if decoder_value not in entries:
            self.obj('entry_prog_decoder').prepend(decoder_value, decoder_value)
            self.obj('entry_prog_decoder').set_active(0)

        # 1 Speicherorte
        for folder in ['folder_new_otrkeys', 'folder_uncut_avis', 'folder_cut_avis', 'folder_trash_otrkeys',
                       'folder_trash_avis', 'folder_archive']:
            EntryBinding(self.obj('entry_' + folder), self.app.config, 'general', folder)

        # 2 OTR-Einstellungen
        ComboBoxEntryBinding(self.obj('entry_prog_decoder'), self.app.config, 'programs', 'decoder')
        CheckButtonBinding(self.obj('check_verify_decoded'), self.app.config, 'general', 'verify_decoded')
        EntryBinding(self.obj('entry_email'), self.app.config, 'general', 'email')
        EntryBinding(self.obj('entry_password'), self.app.config, 'general', 'password')
        RadioButtonsBinding([self.obj(widget) for widget in ['radioPasswdStoreConf', 'radioPasswdStoreWallet',
                                                             'radioPasswdStoreNot']],
                            self.app.config, 'general', 'passwd_store')
        CheckButtonBinding(self.obj('check_passwd_store_memory'), self.app.config, 'general', 'passwd_store_memory')

        # 3 Schneiden
        ComboBoxEntryBinding(self.obj('combobox_avi'), self.app.config, 'general', 'cut_avis_by')
        ComboBoxEntryBinding(self.obj('combobox_hq'), self.app.config, 'general', 'cut_hqs_by')
        ComboBoxEntryBinding(self.obj('combobox_hd2'), self.app.config, 'general', 'cut_hd2_by')
        ComboBoxEntryBinding(self.obj('combobox_mp4'), self.app.config, 'general', 'cut_mp4s_by')
        ComboBoxEntryBinding(self.obj('combobox_man_avi'), self.app.config, 'general', 'cut_avis_man_by')
        ComboBoxEntryBinding(self.obj('combobox_man_hq'), self.app.config, 'general', 'cut_hqs_man_by')
        ComboBoxEntryBinding(self.obj('combobox_man_hd2'), self.app.config, 'general', 'cut_hd2_man_by')
        ComboBoxEntryBinding(self.obj('combobox_man_mp4'), self.app.config, 'general', 'cut_mp4s_man_by')
        ComboBoxEntryBinding(self.obj('h264_codec_cbox'), self.app.config, 'general', 'h264_codec')
        ComboBoxEntryBinding(self.obj('combobox_ac3'), self.app.config, 'general', 'merge_ac3s_by')
        CheckButtonBinding(self.obj('check_merge_ac3'), self.app.config, 'general', 'merge_ac3s')
        ComboBoxEntryBinding(self.obj('smkv_first_audio'), self.app.config, 'smartmkvmerge', 'first_audio_stream',
                             data=['normalize_audio', self.obj('check_normalize_audio')])
        ComboBoxEntryBinding(self.obj('smkv_second_audio'), self.app.config, 'smartmkvmerge', 'second_audio_stream',
                             data=['normalize_audio', self.obj('check_normalize_audio')])
        EntryBinding(self.obj('smkv_workingdir'), self.app.config, 'smartmkvmerge', 'workingdir')
        CheckButtonBinding(self.obj('check_normalize_audio'), self.app.config, 'smartmkvmerge', 'normalize_audio')
        CheckButtonBinding(self.obj('smkv_mp4'), self.app.config, 'smartmkvmerge', 'remux_to_mp4')
        ComboBoxEntryBinding(self.obj('encoder_engine'), self.app.config, 'smartmkvmerge', 'encoder_engine')

        # 4 Cutlist
        EntryBinding(self.obj('entry_server'), self.app.config, 'general', 'server')
        RadioButtonsBinding([self.obj(widget) for widget in ['radio_size', 'radio_filename']],
                            self.app.config, 'general', 'choose_cutlists_by')
        CheckButtonBinding(self.obj('check_delete_cutlists'), self.app.config, 'general', 'delete_cutlists')
        EntryBinding(self.obj('entry_cutlist_username'), self.app.config, 'general', 'cutlist_username')
        CheckButtonBinding(self.obj('check_mplayer_fullscreen'), self.app.config, 'general', 'mplayer_fullscreen')
        CheckButtonBinding(self.obj('check_prefer_mplayer'), self.app.config, 'general', 'prefer_mplayer')
        CheckButtonBinding(self.obj('check_ignore_suggested'), self.app.config, 'general', 'ignore_suggested_filename')
        EntryBinding(self.obj('entry_cutlist_comment'), self.app.config, 'general', 'cutlist_comment')
        TextbufferBinding(self.obj('txtbuf_snippets'), self.app.config, 'general', 'snippets', self.obj)

        # 5 Umbenennen
        CheckButtonBinding(self.obj('check_rename_cut'), self.app.config, 'general', 'rename_cut')
        EntryBinding(self.obj('entry_schema'), self.app.config, 'general', 'rename_schema')

        # 6 Hauptfenster
        SpinbuttonBinding(self.obj('spinbutton_iconsize'), self.app.config, 'general', 'icon_size')
        CheckButtonBinding(self.obj('check_use_internal_icons'), self.app.config, 'general', 'use_internal_icons')
        CheckButtonBinding(self.obj('check_hide_archive_buttons'), self.app.config, 'general', 'hide_archive_buttons')
        ComboBoxEntryBinding(self.obj('entry_cut_default'), self.app.config, 'general', 'cut_action',
                             data=['cut_default'])
        CheckButtonBinding(self.obj('check_show_conclusiondialog_after_cutting'), self.app.config, 'general',
                           'show_conclusiondialog_after_cutting')

        # 7 Cutinterface
        SpinbuttonBinding(self.obj('spinbtn_seeker'), self.app.config, 'cutinterface', 'seek_distance_default')
        SpinbuttonBinding(self.obj('spinbtn_seek1'), self.app.config, 'cutinterface', 'seek1')
        SpinbuttonBinding(self.obj('spinbtn_seek2'), self.app.config, 'cutinterface', 'seek2')
        SpinbuttonBinding(self.obj('spinbutton_x'), self.app.config, 'cutinterface', 'resolution_x')
        SpinbuttonBinding(self.obj('spinbutton_y'), self.app.config, 'cutinterface', 'resolution_y')
        CheckButtonBinding(self.obj('check_vol_adjust_on'), self.app.config, 'general', 'vol_adjust_on')
        EntryBinding(self.obj('entry_vol_adjust'), self.app.config, 'general', 'vol_adjust')
        CheckButtonBinding(self.obj('check_alt_time_frame_conv'),
                           self.app.config, 'cutinterface', 'alt_time_frame_conv'),
        SpinbuttonBinding(self.obj('spinbutton_test_cut_offset_secs'),
                          self.app.config, 'cutinterface', 'test_cut_offset_secs')
        CheckButtonBinding(self.obj('check_show_tooltips'), self.app.config, 'cutinterface', 'show_tooltips')
        CheckButtonBinding(self.obj('check_not_force_search_cutlist_by_name'), self.app.config, 'cutinterface',
                           'not_force_search_cutlist_by_name')

        # 8 Programme
        for prog in ['ffmpeg', 'ffprobe', 'ffmsindex', 'x264', 'mediainfo', 'mkvmerge', 'mpv', 'vdub']:
            EntryBinding(self.obj('entry_prog_' + prog), self.app.config, 'programs', prog)
        EntryBinding(self.obj('entry_folder_wineprefix'), self.app.config, 'programs', 'wineprefix')

        def rename_schema_changed(value):
            new_name = self.app.rename_by_schema(self.example_cut_filename, value)
            self.obj('label_schema').set_label(f"<i>{self.example_filename}</i> wird zu <i>{new_name}</i>")

        if not self.app.config.keyring_available:
            self.obj('radioPasswdStoreWallet').set_sensitive(False)

        self.app.config.connect('general', 'rename_schema', rename_schema_changed)
        # "initial rename"
        # TODO: remove?
        # rename_schema_changed(self.obj('entry_schema').get_text())

        for option in ['folder_new_otrkeys', 'folder_trash_otrkeys', 'folder_trash_avis', 'folder_uncut_avis',
                       'folder_cut_avis', 'folder_archive']:
            self.app.config.connect('general', option, lambda value: self.app.show_section(self.app.section))

        self.app.config.connect('general', 'rename_cut', lambda value: self.obj('entry_schema').set_sensitive(value))
        self.app.config.connect('general', 'merge_ac3s', lambda value: self.obj('combobox_ac3').set_sensitive(value))
        self.app.config.connect('general', 'merge_ac3s', lambda value: self.obj('button_set_file_ac3')
                                .set_sensitive(value))
        self.app.config.connect('general', 'merge_ac3s', lambda value: self.obj('label_ac3').set_sensitive(value))
        self.app.config.connect('general', 'use_internal_icons', lambda value: self.obj('label_iconsize')
                                .set_sensitive(not value))
        self.app.config.connect('general', 'use_internal_icons', lambda value: self.obj('spinbutton_iconsize')
                                .set_sensitive(not value))
        self.app.config.connect('general', 'passwd_store', lambda value: self._radio_passwd_store_toggled(value))

        # Delete combobox entries for intern-vdub if not installed
        if otrvpath.get_internal_virtualdub_path('vdub.exe') is None:
            for widget_name in ['combobox_avi', 'combobox_hq', 'combobox_hd2', 'combobox_mp4']:
                self.obj(widget_name).remove(1)
        # and (not os.path.exists(self.app.config.get_program('vdub'))
        #      or not os.path.exists(self.app.config.get_program('wineprefix')))

        # Initializing
        self.obj('entry_password').set_visibility(False)
        self.obj('entry_schema').set_sensitive(self.app.config.get('general', 'rename_cut'))
        self.obj('combobox_ac3').set_sensitive(self.app.config.get('general', 'merge_ac3s'))
        self.obj('label_iconsize').set_sensitive(not self.obj('check_use_internal_icons').get_active())
        self.obj('spinbutton_iconsize').set_sensitive(not self.obj('check_use_internal_icons').get_active())
        self._radio_passwd_store_toggled(self.app.config.get('general', 'passwd_store'))
        first = 'AAC' in self.app.config.get('smartmkvmerge', 'first_audio_stream')
        second = 'AAC' in self.app.config.get('smartmkvmerge', 'second_audio_stream')
        if first or second:
            self.obj('check_normalize_audio').set_sensitive(True)
        else:
            self.obj('check_normalize_audio').set_sensitive(False)

        # for prog in ["ffmpeg", "ffprobe", "ffmsindex", 'x264', 'mpv']:
        #     for prefix in ['lbl_prog_', 'entry_prog_', 'btn_prog_', 'lbl_check_']:
        #         self.obj(prefix + prog).set_visible(False)
        # if sys.platform != 'win32':
        #     for prefix in ['lbl_prog_', 'entry_prog_', 'btn_prog_', 'lbl_check_']:
        #         self.obj(prefix + 'vdub').set_visible(False)

# Signal handlers ###

    def on_entry_prog_changed(self, entry):
        entry_name = Gtk.Buildable.get_name(entry)
        prog_name = entry_name.rpartition('_')[2]   # name scheme is entry_prog_ffmpeg
        lbl_check = self.obj("lbl_check_" + prog_name)
        if os.path.exists(entry.get_text()):
            lbl_check.set_markup("<span color='green'>✓</span>")
        else:
            lbl_check.set_markup("<span color='red'>✘</span>")
        return False

    def _on_btn_snippets_save_clicked(self, txtbuf):
        self.app.config.set('general', 'snippets', txtbuf.props.text)
        self.obj('btn_snippets_save').set_sensitive(False)

    def _radio_passwd_store_toggled(self, value):
        if value == 2:  # radioPasswdStoreNot
            self.obj('check_passwd_store_memory').set_sensitive(True)
            self.obj('labelPasswdStoreMemory').set_sensitive(True)
            self.obj('entry_password').set_sensitive(False)
        else:
            self.obj('check_passwd_store_memory').set_sensitive(False)
            self.obj('labelPasswdStoreMemory').set_sensitive(False)
            self.obj('entry_password').set_sensitive(True)

    def _on_button_reset_size_moviewindow_clicked(self, widget):
        self.obj('spinbutton_x').set_value(800.0)
        self.obj('spinbutton_y').set_value(450.0)

    def _on_button_check_otr_credentials_clicked(self, entry):
        request_answer=""
        if self.app.config.get('general', 'password') != "" and internet_on():
            url = "http://www.onlinetvrecorder.com/webrecording/isuser.php"
            params = {
                'email': self.app.config.get('general', 'email'),
                'pass': hashlib.md5(self.app.config.get('general', 'password').encode('utf-8')).hexdigest()
            }
            r = requests.get(url=url, params=params)
            request_answer = r.text;
        if internet_on():
            if 'yes' in request_answer:
                self.obj('checkOTRCredentials').modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#008000'))
                self.obj('OTRCredentialCheckResponse').set_markup("<span color='green'>✓</span>")
            else:
                self.obj('checkOTRCredentials').modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#c70002'))
                self.obj('OTRCredentialCheckResponse').set_markup("<span color='red'>✘</span>")
        else:
            self.obj('checkOTRCredentials').modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse('#d87107'))
            self.obj('OTRCredentialCheckResponse').set_markup("<span color='red'>🖧 Keine Internetverbindung!</span>")

    def _on_button_set_file_clicked(self, entry, data=None):
        entry_name = Gtk.Buildable.get_name(entry)
        try:
            chooser_title = self.filechooser_title_setup[entry_name] + ":"
        except KeyError:
            chooser_title = "Datei auswählen:"

        if entry_name.startswith('entry_prog') or entry_name.startswith('combobox_'):
            chooser_action = Gtk.FileChooserAction.OPEN
        else:
            chooser_action = Gtk.FileChooserAction.SELECT_FOLDER

        chooser = Gtk.FileChooserDialog(title=chooser_title, parent=self, action=chooser_action,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_transient_for(self)
        if isinstance(entry, Gtk.Entry):
            if entry_name.startswith('entry_prog'):
                self.last_path = None
            if os.path.exists(entry.get_text()) and self.last_path is None:
                chooser.set_current_folder(os.path.join(entry.get_text(), '..'))
            elif self.last_path is not None:
                chooser.set_current_folder(os.path.join(self.last_path, '..'))
            else:
                chooser.set_current_folder(os.path.expanduser("~"))

        if chooser.run() == Gtk.ResponseType.OK:
            if isinstance(entry, Gtk.ComboBoxText):
                entry.prepend(chooser.get_filename(), chooser.get_filename())
                entry.set_active(0)
            elif isinstance(entry, Gtk.Entry):
                entry.set_text(chooser.get_filename())
                self.last_path = entry.get_text()

        chooser.destroy()

    def _on_entry_prog_decoder_changed(self, widget, data=None):
        if 'otrtool' in widget.get_active_text():
            self.obj('check_verify_decoded').set_sensitive(False)
        else:
            self.obj('check_verify_decoded').set_sensitive(True)

    def on_preferences_window_key_press_event(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval).upper()
        if event.type == Gdk.EventType.KEY_PRESS:
            if keyname == 'ESCAPE':
                self._on_preferences_button_close_clicked(None)
                return True

    def _on_preferences_button_close_clicked(self, widget, data=None):
        self.hide()
        try:
            # Update settings in Cutinterface
            self.app.gui.ci_instance.config_update()
        except AttributeError:
            pass

    def _on_preferences_window_delete_event(self, window, event):
        self._on_preferences_button_close_clicked(None)
        return True


def new():
    glade_filename = otrvpath.getdatapath('ui', 'PreferencesWindow.glade')
    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    window = builder.get_object("preferences_window")
    # window.app = app
    # window.gui = gui
    return window


def internet_on():
    # Check if online
    try:
        # google.com ip
        urllib2.urlopen('http://216.58.192.142', timeout=1)
        return True
    except urllib2.URLError as err:
        return False
