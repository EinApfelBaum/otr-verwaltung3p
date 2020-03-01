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

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, Gdk
# import os.path
import os, re
import logging

from otrverwaltung3p.constants import Action, Status, Cut_action
from otrverwaltung3p.gui.widgets.FolderChooserComboBox import FolderChooserComboBox
from otrverwaltung3p import path

replacements = {"Ä": "Ae", "ä": "ae", "Ö": "Oe", "ö": "oe", "Ü": "Ue",
                "ü": "ue", "ß": "ss"}
fileextensions = ['.avi', '.mp4', '.mkv']

class ConclusionDialog(Gtk.Dialog, Gtk.Buildable):
    """ The dialog is organized in boxes:
            box_filenames - Shows the filename and the statuses of a decode/cut action.
            box_buttons - Play button, Cut-Play button, Put uncut file in trash, box_rename,
            box_rating, box_create_cutlist - Settings for a cutlist.


        If cut.status == status.OK:                 v=Visible, x!=not visible

                          BEST_CUTLIST  CHOOSE_CUTLIST  LOCAL_CUTLIST  MANUALLY
        button_play           V               V              V            V
        button_play_cut       V               V              V            V
        combobox_external_r   V               V              x!           x!       !
        combobox_archive      V               V              V            V
        check_delete_uncut    V               V              V            V
        box_rename            V               V              V            V
        box_create_cutlist    x!              x!             x!           V        ! """

    __gtype_name__ = "ConclusionDialog"

    def __init__(self):
        Gtk.Dialog.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.widget_entry_suggested = None
        self.connect('key-press-event', self._do_keypress_event)

    def obj(self, obj_name):
        return self.builder.get_object(obj_name)

    def do_parser_finished(self, builder):
        self.builder = builder
        self.builder.connect_signals(self)

        self.obj('check_create_cutlist').modify_font(Pango.FontDescription("bold"))

        self.combobox_archive = FolderChooserComboBox(add_empty_entry=True)
        self.obj('box_archive').pack_end(self.combobox_archive, True, True, 0)
        self.widget_entry_suggested = self.obj('entry_suggested')

        for combobox in ['combobox_external_rating', 'combobox_own_rating']:
            cell = Gtk.CellRendererText()
            cell.set_property('ellipsize', Pango.EllipsizeMode.END)
            self.obj(combobox).pack_start(cell, True)
            self.obj(combobox).add_attribute(cell, 'text', 0)

    # Convenience

    def _run(self, file_conclusions, rename_by_schema, archive_directory):
        self.rename_by_schema = rename_by_schema
        self.__file_conclusions = file_conclusions
        self.forward_clicks = 0

        if len(file_conclusions) == 1:
            self.obj('button_back').hide()
            self.obj('button_forward').hide()
            self.obj('label_count').hide()

        self.combobox_archive.fill(archive_directory)
        self.combobox_archive.connect('changed', self._on_combobox_archive_changed)

        self.show_conclusion(0)

        self.run()
        self.hide()
        return self.__file_conclusions

    def __status_to_s(self, status, message):
        string = ''

        if status == Status.OK:
            string = "OK"
        elif status == Status.ERROR:
            string = "Fehler"
        elif status == Status.NOT_DONE:
            string = "Nicht durchgeführt"

        if message:
            if status == Status.ERROR:
                message = "<b>%s</b>" % message

            string += ": %s" % message

        return string

    def set_entry_suggested_on_close(self):
        """ Called by '_on_button_abort_clicked', '_on_buttonConclusionClose_clicked',
            _on_button_back_clicked and _on_button_forward_clicked.
            Set 'entry_suggested' (the suggested movie name) to the value of 'comboboxentry_rename'
            if 'Cutlist erstellen' is true. 'self.file_conclusion.cut.rename' holds the value of
            'comboboxentry_rename' (auto-updated by '_on_comboboxentry_rename_changed')
        """
        if self.obj('check_create_cutlist').get_active():
            if self.obj('entry_suggested').get_text() == "":
                edit_fname = self.file_conclusion.cut.rename
                self.log.debug("edit_fname = {}".format(edit_fname))
                # If Cancel button is clicked edit_fname is set to False. So check.
                if edit_fname:
                    for ext in fileextensions:
                        if edit_fname.endswith(ext):
                            edit_fname = edit_fname.replace(ext, '')
                    self.obj('entry_suggested').set_text(edit_fname)

    ###
    ### Controls
    ###

    def _on_button_back_clicked(self, widget, data=None):
        self.set_entry_suggested_on_close()
        self.show_conclusion(self.conclusion_iter - 1)

    def _on_button_forward_clicked(self, widget, data=None):
        self.set_entry_suggested_on_close()
        self.show_conclusion(self.conclusion_iter + 1)
        self.forward_clicks += 1

    def _on_button_abort_clicked(self, widget, data=None):
        self.set_entry_suggested_on_close()
        widgets_hidden = ['button_play_cut', 'box_rating', 'check_delete_uncut', 'box_rename',
                          'box_archive', 'button_play', 'box_create_cutlist', 'hbox_replace']
        for widget in widgets_hidden:
            self.obj(widget).hide()

        self.file_conclusion.cut.status = Status.NOT_DONE
        self.obj('check_upload_cutlist').set_active(False)
        self.file_conclusion.cut.rename = False
        status, message = self.file_conclusion.cut.status, self.file_conclusion.cut.message
        self.obj('label_cut_status').set_markup(self.__status_to_s(status, message))

        if os.path.isfile(self.file_conclusion.cut_video):
            os.remove(self.file_conclusion.cut_video)

    def _on_buttonConclusionClose_clicked(self, widget, data=None):
        self.set_entry_suggested_on_close()

    def show_conclusion(self, new_iter):
        self.conclusion_iter = new_iter
        self.file_conclusion = self.__file_conclusions[self.conclusion_iter]
        self.obj('label_count').set_text("Zeige Datei %s/%s" % (str(new_iter + 1), len(self.__file_conclusions)))

        # basic show/hide
        action = self.file_conclusion.action
        self.show_all()
        widgets_hidden = []
        if action == Action.DECODE:
            self.obj('box_buttons').show()  # hide all except play button
            widgets_hidden = ['image_cut', 'label_cut', 'label_cut_status', 'button_play_cut',
                              'box_rating', 'check_delete_uncut', 'box_rename', 'box_archive',
                              'hbox_replace']
        elif action == Action.CUT:
            widgets_hidden = ['image_decode', 'label_decode', 'label_decode_status']

        for widget in widgets_hidden:
            self.obj(widget).hide()

        # enable back- and forward button?
        self.obj('button_back').set_sensitive(not self.conclusion_iter == 0)
        self.obj('button_forward').set_sensitive(
            not (self.conclusion_iter + 1 == len(self.__file_conclusions)))
        self.obj('button_abort').set_sensitive(action == Action.CUT
                                               or action == Action.DECODEANDCUT
                                               and self.file_conclusion.cut.status == Status.OK)

        # status message
        if action != Action.DECODE:
            status, message = self.file_conclusion.cut.status, self.file_conclusion.cut.message
            self.obj('label_cut_status').set_markup(self.__status_to_s(status, message))
            self.obj('label_filename').set_markup(f"<b>{os.path.basename(self.file_conclusion.uncut_video)}</b>")

        if action != Action.CUT:
            status = self.file_conclusion.decode.status
            message = self.file_conclusion.decode.message
            self.obj('label_decode_status').set_markup(self.__status_to_s(status, message))
            self.obj('label_filename').set_markup(f"<b>{os.path.basename(self.file_conclusion.otrkey)}</b>")

        # fine tuning
        if action == Action.DECODE:
            self.obj('box_create_cutlist').hide()

        else:
            cut_ok = (self.file_conclusion.cut.status == Status.OK)
            cut_action = self.file_conclusion.cut.cut_action

            # set visibility
            self.obj('button_play').props.visible = cut_ok
            self.obj('button_play_cut').props.visible = cut_ok
            self.obj('box_archive').props.visible = cut_ok

            self.obj('check_delete_uncut').props.visible = cut_ok
            if cut_ok:
                self.obj('check_delete_uncut').set_active(self.file_conclusion.cut.delete_uncut)

            self.obj('box_rename').props.visible = cut_ok
            self.obj('hbox_replace').props.visible = cut_ok

            if cut_ok:
                rename_list = []
                rename_list_entries = {}

                full_fname = os.path.basename(self.file_conclusion.cut_video)
                for ext in fileextensions:
                    if full_fname.endswith(ext):
                        full_fname = full_fname.replace(ext, '')

                if self.app.config.get('general', 'rename_cut'):
                    auto_fname = self.rename_by_schema(os.path.basename(self.file_conclusion.cut_video))
                    for ext in fileextensions:
                        if auto_fname.endswith(ext):
                            auto_fname = auto_fname.replace(ext, '')
                    rename_list.append(full_fname)
                    rename_list_index = 0
                    rename_list_entries['full_fname'] = rename_list_index
                    rename_list.append(auto_fname)
                    rename_list_index += 1
                    rename_list_entries['auto_fname'] = rename_list_index
                else:
                    rename_list.append(full_fname)
                    rename_list_index = 0
                    rename_list_entries['full_fname'] = rename_list_index

                re_fname = re.compile(r".*?\.[0-9]{2}\.[a-zA-Z0-9_-]*")
                try:
                    bare_fname = re_fname.match(os.path.basename(self.file_conclusion.uncut_video)).group()
                except Exception as e:
                    self.log.info(f"Filename does not match the otr pattern.\n"
                                  f"This happens when cutting a already cut file.\nException: {e}")
                if self.file_conclusion.cut.cutlist.filename:  # suggested moviename
                    sugg_fname = self.file_conclusion.cut.cutlist.filename
                    for ext in fileextensions:
                        if sugg_fname.endswith(ext):
                            sugg_fname = sugg_fname.replace(ext, '')
                    if sugg_fname != bare_fname:
                        rename_list.append(sugg_fname)
                        rename_list_index += 1
                        rename_list_entries['sugg_fname'] = rename_list_index
                        # ~ rename_label = self.obj('label5')
                        ## set background of label 'Umbenennen' to yellow to indicate there is
                        ## a suggested filename in cutlist. Set font color to black
                        # ~ rename_label.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(100, 100, 0, 0.8))
                        # ~ rename_label.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(0, 0, 0, 1.0))

                edit_fname = self.file_conclusion.cut.rename
                self.log.debug("edit_fname = {}".format(edit_fname))
                if not edit_fname == "" and not edit_fname.replace('.mkv', '') in rename_list:
                    rename_list.append(edit_fname)  # Edited filename
                    rename_list_index += 1
                    rename_list_entries['edit_fname'] = rename_list_index

                self.obj('comboboxentry_rename').remove_all()
                self.gui.set_model_from_list(self.obj('comboboxentry_rename'), rename_list)
                # set active row
                if 'edit_fname' in rename_list_entries:
                    self.obj('comboboxentry_rename').set_active(rename_list_entries['edit_fname'])
                else:
                    if self.app.config.get('general', 'ignore_suggested_filename'):
                        if self.app.config.get('general', 'rename_cut'):
                            self.obj('comboboxentry_rename').set_active(rename_list_entries['auto_fname'])
                        else:
                            self.obj('comboboxentry_rename').set_active(rename_list_entries['full_fname'])
                    else:
                        if 'sugg_fname' in rename_list_entries:
                            self.obj('comboboxentry_rename').set_active(rename_list_entries['sugg_fname'])

                archive_to = self.file_conclusion.cut.archive_to
                if not archive_to:
                    self.combobox_archive.set_active(0)
                else:
                    for count, row in enumerate(self.combobox_archive.liststore):
                        if row[3] == archive_to:
                            self.combobox_archive.set_active(count)

            if cut_action == Cut_action.BEST_CUTLIST or cut_action == Cut_action.CHOOSE_CUTLIST:
                self.obj('box_rating').props.visible = cut_ok
                self.obj('combobox_external_rating').set_active(self.file_conclusion.cut.my_rating + 1)

                if cut_ok:
                    text = self.obj('label_cut_status').get_text()
                    text += (f"\nMit Cutlist {self.file_conclusion.cut.cutlist.id} geschnitten: "
                             f"Autor: <b>{self.file_conclusion.cut.cutlist.author}</b>, "
                             f"Wertung: <b>{self.file_conclusion.cut.cutlist.rating}</b>"
                             f"\nKommentar: <b>{self.file_conclusion.cut.cutlist.usercomment}</b>")
                    self.obj('label_cut_status').set_markup(text)
            else:
                self.obj('box_rating').hide()

            if cut_action == Cut_action.MANUALLY:
                self.obj('box_create_cutlist').props.visible = cut_ok

                if cut_ok:
                    self.obj('check_create_cutlist').set_active(self.file_conclusion.cut.create_cutlist)
                    self.obj('check_upload_cutlist').set_active(self.file_conclusion.cut.upload_cutlist)

                    c = self.file_conclusion.cut.cutlist
                    self.obj('combobox_own_rating').set_active(c.ratingbyauthor + 1)
                    self.obj('check_wrong_content').set_active(c.wrong_content)
                    self.obj('entry_actual_content').set_text(c.actualcontent)
                    self.obj('check_missing_beginning').set_active(c.missing_beginning)
                    self.obj('check_missing_ending').set_active(c.missing_ending)
                    self.obj('check_other_error').set_active(c.other_error)
                    self.obj('entry_other_error_description').set_text(c.othererrordescription)
                    self.obj('entry_suggested').set_text(c.suggested_filename)
                    self.obj('entry_comment').set_text(c.usercomment)
            else:
                self.obj('box_create_cutlist').hide()

        if action != Action.CUT:
            self.obj('button_play').props.visible = (self.file_conclusion.decode.status == Status.OK)

        # Reset cursor of MainWindow
        self.gui.main_window.get_window().set_cursor(None)

    ###
    ### Signals handlers
    ###

    # box_buttons

    def _do_keypress_event(self, widget, event, *args):
        keyname = Gdk.keyval_name(event.keyval).upper()
        if event.type == Gdk.EventType.KEY_PRESS:
            if keyname == 'ESCAPE':
                ret_val = True
            else:
                ret_val = False
        return ret_val

    def _on_button_play_clicked(self, widget, data=None):
        if self.file_conclusion.action == Action.DECODE or (self.file_conclusion.action == Action.DECODEANDCUT
                                                            and self.file_conclusion.cut.status != Status.OK):
            self.app.play_file(self.file_conclusion.uncut_video)
        else:
            self.app.play_file(self.file_conclusion.cut_video)

    def _on_button_conclusion_play_cut_clicked(self, widget, data=None):
        self.app.show_cuts_after_cut(self.file_conclusion.cut_video, self.file_conclusion.cut.cutlist)

    def _on_combobox_external_rating_changed(self, widget, data=None):
        rating = widget.get_active() - 1
        self.log.info("cut.my_rating = {}".format(rating))
        self.file_conclusion.cut.my_rating = rating

    def _on_check_delete_uncut_toggled(self, widget, data=None):
        self.log.info("cut.delete_uncut = {}".format(widget.get_active()))
        self.file_conclusion.cut.delete_uncut = widget.get_active()

    def _on_comboboxentry_rename_changed(self, widget, data=None):
        self.log.debug("cut.rename = {}".format(widget.get_active_text()))
        self.file_conclusion.cut.rename = widget.get_active_text()
        # ~ if self.file_conclusion.cut.create_cutlist:
        # ~     self.widget_entry_suggested.set_text(widget.get_active_text())

    def _on_button_spaces_clicked(self, widget, data=None):
        self.log.debug("Function start")
        name = self.obj('comboboxentry_rename').get_active_text()
        new_name = name.replace(' ', '_')
        self.obj('comboboxtext-entry').set_text(new_name)

    def _on_button_umlauts_clicked(self, widget, data=None):
        self.log.debug("Function start")
        name = self.obj('comboboxentry_rename').get_active_text()
        for key, value in replacements.items():
            if key in name:
                name = name.replace(key, value)
        self.obj('comboboxtext-entry').set_text(name)

    def _on_combobox_archive_changed(self, widget, data=None):
        if self.file_conclusion != Action.DECODE:
            archive_to = self.combobox_archive.get_active_path()
            self.file_conclusion.cut.archive_to = archive_to

    # box_create_cutlist
    def _on_check_create_cutlist_toggled(self, widget, data=None):
        create_cutlist = widget.get_active()
        self.log.info("cut.create_cutlist = {}".format(create_cutlist))
        self.file_conclusion.cut.create_cutlist = create_cutlist
        self.obj('box_create_cutlist_options').set_sensitive(create_cutlist)
        self.obj('check_upload_cutlist').set_sensitive(create_cutlist)

    def _on_check_upload_cutlist_toggled(self, widget, data=None):
        upload_cutlist = widget.get_active()
        self.log.info("cut.upload_cutlist = {}".format(upload_cutlist))
        self.file_conclusion.cut.upload_cutlist = upload_cutlist

    def _on_combobox_own_rating_changed(self, widget, data=None):
        ratingbyauthor = widget.get_active() - 1
        self.log.info("cut.cutlist.ratingbyauthor = {}".format(ratingbyauthor))
        self.file_conclusion.cut.cutlist.ratingbyauthor = ratingbyauthor

    def _on_check_wrong_content_toggled(self, widget, data=None):
        self.log.info("cut.cutlist.wrong_content = {}".format(widget.get_active()))
        self.file_conclusion.cut.cutlist.wrong_content = widget.get_active()

    def _on_entry_actual_content_changed(self, widget, data=None):
        self.log.info("cut.cutlist.actualcontent = {}".format(widget.get_text()))
        self.file_conclusion.cut.cutlist.actualcontent = widget.get_text()

    def _on_check_missing_beginning_toggled(self, widget, data=None):
        self.log.info("cut.cutlist.missing_beginning = {}".format(widget.get_active()))
        self.file_conclusion.cut.cutlist.missing_beginning = widget.get_active()

    def _on_check_missing_ending_toggled(self, widget, data=None):
        self.log.info("cut.cutlist.missing_ending = {}".format(widget.get_active()))
        self.file_conclusion.cut.cutlist.missing_ending = widget.get_active()

    def _on_check_other_error_toggled(self, widget, data=None):
        self.log.info("cut.cutlist.other_error = {}".format(widget.get_active()))
        self.file_conclusion.cut.cutlist.other_error = widget.get_active()

    def _on_entry_other_error_description_changed(self, widget, data=None):
        self.log.info("cut.cutlist.othererrordescription = {}".format(widget.get_text()))
        self.file_conclusion.cut.cutlist.othererrordescription = widget.get_text()

    def _on_entry_suggested_changed(self, widget, data=None):
        self.log.info("cut.cutlist.suggested_filename = {}".format(widget.get_text()))
        self.file_conclusion.cut.cutlist.suggested_filename = widget.get_text()

    def _on_entry_comment_changed(self, widget, data=None):
        self.log.info("cut.cutlist.usercomment = {}".format(widget.get_text()))
        self.file_conclusion.cut.cutlist.usercomment = widget.get_text()

def NewConclusionDialog(app, gui):
    glade_filename = path.getdatapath('ui', 'ConclusionDialog.glade')

    builder = Gtk.Builder()
    builder.add_from_file(glade_filename)
    dialog = builder.get_object("conclusion_dialog")
    dialog.app = app
    dialog.gui = gui

    return dialog
