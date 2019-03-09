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

import os, logging
import hashlib
import requests
import urllib.request as urllib2
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

from otrverwaltung.constants import Cut_action
from otrverwaltung.gui.config_bindings import EntryBinding, FileChooserFolderBinding, \
                        CheckButtonBinding, ComboBoxEntryBinding, RadioButtonsBinding, \
                        SpinbuttonBinding
from otrverwaltung import path


class PreferencesWindow(Gtk.Window, Gtk.Buildable):
    __gtype_name__ = "PreferencesWindow"

    def __init__(self):
        Gtk.Window.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        pass

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

    def obj(self, objectname):
        return self.builder.get_object(objectname)

    def bind_config(self, config):
        self.example_filename = 'James_Bond_007_09.01.06_20-15_ard_120_TVOON_DE.mpg.HQ.avi'
        self.example_cut_filename = 'James_Bond_007_09.01.06_20-15_ard_120_TVOON_DE.mpg.HQ-cut.avi'

        # preferences fonts (small font for explanations)
        labels = ['labelDescNewOtrkeys',
                  'labelDescUncutAvis',
                  'labelDescCutAvis',
                  'labelDescTrashOtrkeys',
                  'labelDescTrashAvis']
        for label in labels:
            self.obj(label).modify_font(Pango.FontDescription("9"))

        ''' verschoben in die glade Datei

        # cut options - cut via cutlist
        # avi + hq + mp4
        avidemux = ["avidemux", "avidemux2_cli"]
        virtualdub = [r"intern-vdub", r"/pfad/zu/vdub.exe"]
        smartmkvmerge = [r"SmartMKVmerge"]
        #self.gui.set_model_from_list(self.obj('combobox_avi'), avidemux + virtualdub + smartmkvmerge)
        #self.gui.set_model_from_list(self.obj(''), virtualdub + smartmkvmerge)
        #self.gui.set_model_from_list(self.obj('combobox_mp4'), virtualdub)
        
        # manually
        avidemux_man = [r"avidemux3_qt4",r"avidemux2_qt4",r"avidemux2_gtk"]
        virtualdub_man = [r"intern-VirtualDub", r"/pfad/zu/VirtualDub.exe"]
        cut_interface = [r"CutInterface"]
        #self.gui.set_model_from_list(self.obj('combobox_man_avi'), cut_interface + avidemux_man + virtualdub_man)
        #self.gui.set_model_from_list(self.obj('combobox_man_hq'), cut_interface + avidemux_man + virtualdub_man)
        #self.gui.set_model_from_list(self.obj('combobox_man_mp4'), cut_interface + avidemux_man + virtualdub_man)
       
        #self.gui.set_model_from_list(self.obj('comboboxServer'), ["http://cutlist.at/"])
        #self.gui.set_model_from_list(self.obj('entry_decoder'), ['intern-otrdecoder','intern-easydecoder'])

        #self.gui.set_model_from_list(self.obj(''), ["ffdshow", "x264vfw", "komisar"])
        
        # mkvmerge for ac3
        mkvmerge = ["mkvmerge", "/pfad/zu/mkvmerge"]
        #self.gui.set_model_from_list(self.obj('combobox_ac3'), mkvmerge)
        
        # smartmkvmerge
        smkv_first_audio = [ 'MP3 Spur kopieren', 
                                        'MP3 nach AAC konvertieren',  
                                        'nach 2-Kanal AAC konvertieren - von AC3 wenn vorhanden',  
                                        'nach Mehr-Kanal AAC konvertieren - von AC3 wenn vorhanden']
        #self.gui.set_model_from_list(self.obj('smkv_first_audio'), smkv_first_audio)
        smkv_second_audio = [   'AC3 Spur kopieren', 
                                                'AC3 Spur nach AAC konvertieren',  
                                                'AC3 Spur entfernen']
        #self.gui.set_model_from_list(self.obj('smkv_second_audio'), smkv_second_audio)
        '''

        # If stored decoder is not in the standard list (see PreferenceWindow.glade)
        # it will be prepended and set as active entry.
        entry_list = []
        for row in self.obj('entry_decoder').get_model():
            entry_list.append(row[0])
        decoder_value = self.app.config.get('programs', 'decoder')
        if not decoder_value in entry_list:
            self.obj('entry_decoder').prepend(decoder_value, decoder_value)
            self.obj('entry_decoder').set_active(0)

        # add bindings here.
        EntryBinding(self.obj('entry_username'), self.app.config, 'general', 'cutlist_username')
        EntryBinding(self.obj('entryEMail'), self.app.config, 'general', 'email')
        EntryBinding(self.obj('entryPassword'), self.app.config, 'general', 'password')
        EntryBinding(self.obj('entry_schema'), self.app.config, 'general', 'rename_schema')
        EntryBinding(self.obj('smkv_workingdir'), self.app.config, 'smartmkvmerge', 'workingdir')
        EntryBinding(self.obj('entry_server'), self.app.config, 'general', 'server')
       
        SpinbuttonBinding(self.obj('spinbutton_seeker'), self.app.config, 'general', 'seek_distance_default')
        SpinbuttonBinding(self.obj('spinbutton_x'), self.app.config, 'general', 'cutinterface_resolution_x')
        SpinbuttonBinding(self.obj('spinbutton_y'), self.app.config, 'general', 'cutinterface_resolution_y')
        SpinbuttonBinding(self.obj('spinbutton_iconsize'), self.app.config, 'general', 'icon_size')

        def rename_schema_changed(value):
            new = self.app.rename_by_schema(self.example_cut_filename, value)
            self.obj('label_schema').set_label(
                "<i>%s</i> wird zu <i>%s</i>" % (self.example_filename, new))

        self.app.config.connect('general', 'rename_schema', rename_schema_changed)
        # "initial rename"
        # TODO: remove?
        # rename_schema_changed(self.obj('entry_schema').get_text())

        FileChooserFolderBinding(self.obj('folderNewOtrkeys'), self.app.config, 'general', 'folder_new_otrkeys')
        FileChooserFolderBinding(self.obj('folderTrashOtrkeys'), self.app.config, 'general', 'folder_trash_otrkeys')
        FileChooserFolderBinding(self.obj('folderTrashAvis'), self.app.config, 'general', 'folder_trash_avis')
        FileChooserFolderBinding(self.obj('folderUncutAvis'), self.app.config, 'general', 'folder_uncut_avis')
        FileChooserFolderBinding(self.obj('folderCutAvis'), self.app.config, 'general', 'folder_cut_avis')
        FileChooserFolderBinding(self.obj('folderArchive'), self.app.config, 'general','folder_archive')

        for option in ['folder_new_otrkeys', 'folder_trash_otrkeys', 'folder_trash_avis',
                                        'folder_uncut_avis', 'folder_cut_avis', 'folder_archive']:
            self.app.config.connect('general', option,
                                            lambda value: self.app.show_section(self.app.section))

        CheckButtonBinding(self.obj('checkPasswdStoreMemory'), self.app.config, 'general', 'passwd_store_memory')
        CheckButtonBinding(self.obj('checkCorrect'), self.app.config, 'general', 'verify_decoded')
        CheckButtonBinding(self.obj('check_delete_cutlists'), self.app.config, 'general', 'delete_cutlists')
        CheckButtonBinding(self.obj('check_rename_cut'), self.app.config, 'general', 'rename_cut')
        CheckButtonBinding(self.obj('check_merge_ac3'), self.app.config, 'general', 'merge_ac3s')
        CheckButtonBinding(self.obj('check_mplayer_fullscreen'), self.app.config, 'general', 'mplayer_fullscreen')
        CheckButtonBinding(self.obj('check_prefer_mpv'), self.app.config, 'general', 'prefer_mpv')
        CheckButtonBinding(self.obj('check_ignore_suggested'), self.app.config, 'general', 'ignore_suggested_filename')
        CheckButtonBinding(self.obj('smkv_normalize'), self.app.config, 'smartmkvmerge', 'normalize_audio')
        CheckButtonBinding(self.obj('smkv_mp4'), self.app.config, 'smartmkvmerge', 'remux_to_mp4')
        CheckButtonBinding(self.obj('check_alt_time_frame_conv'), self.app.config, 'general', 'alt_time_frame_conv')
        CheckButtonBinding(self.obj('check_use_internal_icons'), self.app.config, 'general', 'use_internal_icons')
        CheckButtonBinding(self.obj('cb_hide_archive_buttons'), self.app.config, 'general', 'hide_archive_buttons')
        
        self.app.config.connect('general', 'rename_cut',
                                lambda value: self.obj('entry_schema').set_sensitive(value))
        self.app.config.connect('general', 'merge_ac3s',
                                lambda value: self.obj('combobox_ac3').set_sensitive(value))
        self.app.config.connect('general', 'merge_ac3s',
                                lambda value: self.obj('button_set_file_ac3').set_sensitive(value))
        self.app.config.connect('general', 'merge_ac3s',
                                lambda value: self.obj('label_ac3').set_sensitive(value))
        self.app.config.connect('general', 'use_internal_icons',
                                lambda value: self.obj('label_iconsize').set_sensitive(not value))
        self.app.config.connect('general', 'use_internal_icons',
                                lambda value: self.obj('spinbutton_iconsize').set_sensitive(not value))
        self.app.config.connect('general', 'passwd_store',
                                lambda value: self._radioPasswdStore_toggled(value))

        ComboBoxEntryBinding(self.obj('combobox_avi'), self.app.config, 'general', 'cut_avis_by')
        ComboBoxEntryBinding(self.obj('combobox_hq'), self.app.config, 'general', 'cut_hqs_by')
        ComboBoxEntryBinding(self.obj('combobox_mp4'), self.app.config, 'general', 'cut_mp4s_by')
        ComboBoxEntryBinding(self.obj('combobox_man_avi'), self.app.config, 'general', 'cut_avis_man_by')
        ComboBoxEntryBinding(self.obj('combobox_man_hq'), self.app.config, 'general', 'cut_hqs_man_by')
        ComboBoxEntryBinding(self.obj('combobox_man_mp4'), self.app.config, 'general', 'cut_mp4s_man_by')
        ComboBoxEntryBinding(self.obj('h264_codec_cbox'), self.app.config, 'general', 'h264_codec')
        ComboBoxEntryBinding(self.obj('combobox_ac3'), self.app.config, 'general', 'merge_ac3s_by')
        ComboBoxEntryBinding(self.obj('entry_decoder'), self.app.config, 'programs', 'decoder')
        ComboBoxEntryBinding(self.obj('smkv_first_audio'), self.app.config, 'smartmkvmerge', 'first_audio_stream')
        ComboBoxEntryBinding(self.obj('smkv_second_audio'), self.app.config, 'smartmkvmerge', 'second_audio_stream')
        ComboBoxEntryBinding(self.obj('entry_cut_default'), self.app.config, 'general', 'cut_action', data='cut_default')

        RadioButtonsBinding([self.obj(widget) for widget in ['radio_size', 'radio_filename']],
                            self.app.config, 'general', 'choose_cutlists_by')
        RadioButtonsBinding([self.obj(widget) for widget in ['radioPasswdStoreConf', 'radioPasswdStoreWallet','radioPasswdStoreNot']],
                            self.app.config, 'general', 'passwd_store')

        # Initializing
        self.obj('entryPassword').set_visibility(False)
        self.obj('entry_schema').set_sensitive(self.app.config.get('general', 'rename_cut'))
        self.obj('combobox_ac3').set_sensitive(self.app.config.get('general', 'merge_ac3s'))
        self.obj('label_iconsize').set_sensitive(not self.obj('check_use_internal_icons').get_active())
        self.obj('spinbutton_iconsize').set_sensitive(not self.obj('check_use_internal_icons').get_active())
        self._radioPasswdStore_toggled(self.app.config.get('general', 'passwd_store'))


### Signal handlers ###

    def _radioPasswdStore_toggled(self, value):
        if value == 2:  # radioPasswdStoreNot
            self.obj('checkPasswdStoreMemory').set_sensitive(True)
            self.obj('labelPasswdStoreMemory').set_sensitive(True)
            self.obj('entryPassword').set_sensitive(False)
        else:
            self.obj('checkPasswdStoreMemory').set_sensitive(False)
            self.obj('labelPasswdStoreMemory').set_sensitive(False)
            self.obj('entryPassword').set_sensitive(True)

    def _on_button_reset_size_moviewindow_clicked(self, widget):
        self.obj('spinbuttonX').set_value(800.0)
        self.obj('spinbuttonY').set_value(450.0)
        
    def _on_button_check_otr_credentials_clicked(self, entry):
        request_answer=""
        if self.app.config.get('general', 'password') != "" and internet_on():
            URL = "http://www.onlinetvrecorder.com/webrecording/isuser.php"
            PARAMS = {
                'email': self.app.config.get('general', 'email'), 
                'pass': hashlib.md5(self.app.config.get('general', 'password').encode('utf-8')).hexdigest()
            }
            r = requests.get(url = URL, params = PARAMS)
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
        chooser = Gtk.FileChooserDialog(title="Datei auswählen",
                                        action=Gtk.FileChooserAction.OPEN,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_transient_for(self)

        if chooser.run() == Gtk.ResponseType.OK:
            # ~ if type(entry) == Gtk.ComboBoxText:
                # ~ entry.child.set_text(chooser.get_filename())
            # ~ else:
            if type(entry) == Gtk.ComboBoxText:
                entry.prepend(chooser.get_filename(), chooser.get_filename())
                entry.set_active(0)

        chooser.destroy()

    def _on_entry_decoder_changed(self, widget, data=None):
        self.log.debug("Function start")
        if 'otrtool' in widget.get_active_text():
            self.obj('checkCorrect').set_sensitive(False)
        else:
            self.obj('checkCorrect').set_sensitive(True)

    def on_preferences_window_key_press_event(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval).upper()
        if event.type == Gdk.EventType.KEY_PRESS:
            if keyname == 'ESCAPE':
                self.hide()
                return True

    def _on_preferences_buttonClose_clicked(self, widget, data=None):
        self.hide()

    def _on_preferences_window_delete_event(self, window, event):
        self.hide()
        return True  # don't destroy


def NewPreferencesWindow(app, gui):
    glade_filename = path.getdatapath('ui', 'PreferencesWindow.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    window = builder.get_object("preferences_window")
    window.app = app
    window.gui = gui
    return window

def internet_on():
    ## Check if online
    try:
        ## google.com ip
        urllib2.urlopen('http://216.58.192.142', timeout=1)
        return True
    except urllib2.URLError as err: 
        return False
