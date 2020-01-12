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

try:
    import simplejson as json
except ImportError:
    import json
import os
import logging

from base64 import b64decode, b64encode
from otrverwaltung import path as otrv_path
from Crypto.Cipher import AES


X264_MP4_OLD = '--force-cfr --profile baseline --preset medium --trellis 0'
X264_MP4_NEW = '--force-cfr --trellis 0 --preset veryfast'


class Config:
    """ Loads and saves configuration fields from/to file. """

    def __init__(self, config_file, fields):
        self._config_file = config_file
        self._fields = fields
        self._callbacks = {}
        self.log = logging.getLogger(self.__class__.__name__)

    def connect(self, category, option, callback):
        self._callbacks.setdefault(category, {})
        self._callbacks[category].setdefault(option, []).append(callback)

    def set(self, category, option, value):
        """Set a configuration option."""
        removed = '**REMOVED**' if option in ('email', 'password') else value
        self.log.debug(
            "[%(category)s][%(option)s] to %(value)s",
            {"category": category, "option": option, "value": removed}
        )
        try:
            for callback in self._callbacks[category][option]:
                callback(value)
        except KeyError:
            pass
        self._fields[category][option] = value

    def get(self, category, option):
        """ Gets a configuration option. """
        value = self._fields[category][option]
        removed = '**REMOVED**' if option in ('email', 'password') else value
        self.log.debug(
            "[%(category)s][%(option)s] to %(value)s",
            {"category": category, "option": option, "value": removed}
        )
        return value

    def _pad(self, password):
        general = self._fields['general']
        blocksize = general['aes_blocksize']
        return (
            password
            + (blocksize - len(password) % blocksize)
            * general['aes_padding']
        )

    def _encrypt_aes(self, suite, password):
        return b64encode(
            suite.encrypt(self._pad(password).encode('utf-8'))
        )

    def _decrypt_aes(self, suite, crypted, padding):
        return suite.decrypt(
            b64decode(crypted).decode('utf-8')
        ).rstrip(padding)

    def save(self):
        """ Saves configuration to disk. """
        try:
            # make sure directories exist
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
            general = self._fields['general']
            with open(self._config_file, "w") as config_file:
                try:
                    if len(general['password']) > 0:
                        # Encryption
                        encryption_suite = AES.new(
                            b64decode(general['aes_key'].encode('utf-8')),
                            AES.MODE_ECB
                        )
                        cipher_text = self._encrypt_aes(
                            encryption_suite, general['password']
                        )
                        self._fields['general']['password'] = b64encode(
                            cipher_text
                        ).decode('utf-8')
                except ValueError:
                    self._fields['general']['password'] = general['password']
                self.log.debug("Writing to %s", config_file)
                json.dump(self._fields, config_file, ensure_ascii=False,
                          sort_keys=True, indent=4)
        except IOError:
            self.log.error("Config file not available. Dumping configuration:")
            print(json.dumps(self._fields, sort_keys=True, indent=4))
            self.log.exception("Error:")

    def load(self):
        """ Reads an existing configuration file. """
        try:
            with open(self._config_file, 'r') as config:
                json_config = json.load(config)
        except (IOError, json.decoder.JSONDecodeError):
            self.log.exception(
                "Config file is not available or has invalid json content. "
                "Using default configuration. Error:"
            )
            json_config = {}
        for category, options in self._fields.items():
            for option, value in options.items():
                conf = json_config[category][option]
                try:
                    if category == 'general' and option == 'password':
                        try:
                            general = json_config['general']
                            # Decryption
                            padding = general['aes_padding']
                            decryption_suite = AES.new(
                                b64decode(general['aes_key'].encode('utf-8')),
                                AES.MODE_ECB
                            )
                            crypted = b64decode(json_config[category][option])
                            plain_text = self._decrypt_aes(
                                decryption_suite, crypted, padding
                            )
                            self.set(category, option, plain_text)
                        except ValueError:
                            self.set(category, option, conf)
                    elif category == 'general' and option == 'server':
                        # Check for trailing slash in url
                        serverurl = conf.strip()
                        if not serverurl.endswith("/"):
                            serverurl += "/"
                        self.set(category, option, serverurl)
                    elif (
                        category == 'smartmkvmerge'
                        and option == 'x264_mp4_string'
                    ):
                        # If x264_mp4_string is old default for mp4,
                        # set to new one
                        if conf == X264_MP4_OLD:
                            json_config[category][option] = X264_MP4_NEW
                    else:
                        self.set(category, option, conf)
                except KeyError:
                    self.set(category, option, value)

        # DELETE
        # ~ for key, value in newConfFields.items():
            # ~ self.set(value, key, newConfValues.get(key))

    def get_program(self, program):
        """ Returns the full calling string of a program
            either the pure config value or the internal version,
            if the config value contains 'intern' """
        value = self._fields['programs'][program]
        intern_program = otrv_path.get_tools_path(value)
        if 'intern-' in value:
            if os.path.isfile(intern_program):
                return intern_program
        return value
