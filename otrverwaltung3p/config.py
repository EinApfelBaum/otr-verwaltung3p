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


import json
import os.path
import logging
import shutil
from base64 import b64decode, b64encode
try:
    import keyring
except ImportError:
    pass

from otrverwaltung3p import path
from otrverwaltung3p.libs import pyaes


class Config:
    """ Loads and saves configuration fields from/to file. """

    def __init__(self, config_file, fields):
        """ """

        self.__config_file = config_file
        self.__fields = fields
        self.__callbacks = {}
        self.log = logging.getLogger(self.__class__.__name__)
        try:
            import keyring
            if shutil.which('kwalletd5') or shutil.which('gnome-keyring'):
                self.secret_service_available = True
            else:
                self.secret_service_available = False
        except Exception as e:
            self.secret_service_available = False
            self.log.debug("Keyring exception: {}".format())
        self.log.debug("Keyring available: {}".format(self.secret_service_available))

    def connect(self, category, option, callback):
        self.__callbacks.setdefault(category, {})
        self.__callbacks[category].setdefault(option, []).append(callback)

    def set(self, category, option, value):
        if option in ['email', 'password']:
            self.log.debug("[%(category)s][%(option)s] to *****" % {"category": category,
                                                                                "option": option})
        else:
            self.log.debug("[%(category)s][%(option)s] to %(value)s" % {"category": category,
                                                                "option": option, "value": value})
            pass

        try:
            for callback in self.__callbacks[category][option]:
                callback(value)
        except KeyError:
            pass

        if option is 'password' and self.__fields['general']['passwd_store'] == 1 and value is not None:
            keyring.set_password("otr-verwaltung3p", self.__fields['general']['email'], value)
            self.log.debug("Writing password to keyring")
        else:
            self.__fields[category][option] = value

    def get(self, category, option):
        """ Gets a configuration option. """
        value = ""

        if option is 'password' and self.__fields['general']['passwd_store'] == 1:
            password = keyring.get_password("otr-verwaltung3p", self.__fields['general']['email'])
            if password is not None:
                value = password
        else:
            value = self.__fields[category][option]
        if option in ['email', 'password']:
            self.log.debug("[%(category)s][%(option)s]: *****" % \
                                                        {"category": category, "option": option})
        else:
            self.log.debug("[%(category)s][%(option)s]: %(value)s" % \
                                        {"category": category, "option": option, "value": value})

        return value

    def save(self):
        """ Saves configuration to disk. """

        try:
            # make sure directories exist
            try:
                os.makedirs(os.path.dirname(self.__config_file))
            except OSError:
                pass

            config_file = open(self.__config_file, "w")

            if self.__fields['general']['passwd_store'] == 0:  # Store password in conf
                if len(str(self.__fields['general']['password'])) > 0:
                    key = b64decode(self.__fields['general']['aes_key'].encode('UTF-8'))
                    enc_aes = pyaes.AESModeOfOperationCTR(key)
                    cipher_text = enc_aes.encrypt(self.__fields['general']['password'])
                    self.__fields['general']['password'] = b64encode(cipher_text).decode('UTF-8')
            else:  # Password will not be stored or stored in keyring/wallet
                self.__fields['general']['password'] = ''

            self.log.debug("Writing to {0}".format(self.__config_file))
            json.dump(self.__fields, config_file, ensure_ascii=False, sort_keys=True, indent=4)
            config_file.close()
            os.chmod(self.__config_file, 0o600)
        except IOError as message:
            self.log.error("Config file not available. Dumping configuration:")
            print(json.dumps(self.__fields, sort_keys=True, indent=4))

    def load(self):
        """ Reads an existing configuration file. """

        try:
            config = open(self.__config_file, 'r')
            json_config = json.load(config)
            config.close()
        except (IOError, json.decoder.JSONDecodeError) as message:
            self.log.error("Config file is not available or has invalid json content. " + \
                                                                "Using default configuration.")
            self.log.debug(message)
            json_config = {}

        for category, options in self.__fields.items():
            for option, value in options.items():
                try:
                    if category is 'general' and option is 'password':
                        if json_config['general']['passwd_store'] == 0:
                            if len(str(json_config[category][option])) > 0:
                                key = b64decode(self.__fields['general']['aes_key'].encode('UTF-8'))
                                decrypt_aes = pyaes.AESModeOfOperationCTR(key)
                                bdec = b64decode(json_config[category][option].encode('UTF-8'))
                                plain_text = decrypt_aes.decrypt(bdec).decode('UTF-8')
                                self.set(category, option, plain_text)
                    elif category is 'general' and option is 'server':
                        # Check for trailing slash in url
                        serverurl = json_config[category][option].strip()
                        if not serverurl.endswith("/"):
                            serverurl += "/"
                        self.set(category, option, serverurl)
                    else:
                        self.set(category, option, json_config[category][option])
                except KeyError:
                    self.log.debug("KeyError")
                    self.set(category, option, value)

    def get_program(self, program):
        """ Returns the full calling string of a program
            either the pure config value or the internal version,
            if the config value contains 'intern' """

        value = self.__fields['programs'][program]
        intern_program = path.get_tools_path(value)

        if 'intern-' in value:
            if os.path.isfile(intern_program):
                return intern_program

        return value

    def get_config_file_path(self):
        return os.path.abspath(self.__config_file)
