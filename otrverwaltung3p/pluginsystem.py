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

import os, os.path, sys, logging


class Plugin:
    """ Basisklasse für Plugins """

    Name = "Name of Plugin"
    """ Name des Plugins """
    Desc = "Beschreibung"
    Author = "Autor"
    Configurable = False
    Config = {}  # key-value-pairs for configuration

    # just put your default values in here, the plugin system will do the rest for you

    def __init__(self, app, gui, dirname):
        """ Don't override the constructor. Do the intial work in 'enable'. """
        self.log = logging.getLogger(self.__class__.__name__)
        self.app = app  # for api access
        self.gui = gui  # for api access
        self.dirname = dirname

    def enable(self):
        """ Diese Methode wird aufgerufen, wenn das Plugin aktiviert wird. """
        pass

    def disable(self):
        """ Diese Methode wird aufgerufen, wenn das Plugin deaktiviert wird.
            Es sollte alle in `enable` gemachten Änderungen rückgängig gemacht werden. """
        pass

    def configurate(self, dialog):
        """ Diese Methode wird aufgerufen, wenn der Benutzer das Plugin konfigurieren möchte.
            Alter the dialog.vbox property and return the dialog. The plugin system will do the rest.
            Remember to connect to the 'changed' signals of the widgets you placed in the dialog.
            Use the signals to update your Config dict.
            Note: Set CONFIGURABLE to True. """

        return dialog

    def get_path(self, file=None):

        if file:
            return os.path.join(self.dirname, file)
        else:
            return self.dirname


class PluginSystem:
    def __init__(self, app, gui, plugin_paths, enabled_plugins, plugins_config):
        self.log = logging.getLogger(self.__class__.__name__)
        self.plugins = {}  # value : plugin instance
        self.enabled_plugins = [plugin for plugin in enabled_plugins.split(":") if plugin]  # list of names

        self.log.info("Paths to search: {}".format(plugin_paths))

        for path in plugin_paths:
            if not os.path.isdir(path):
                self.log.info("{} is not a directory.".format(path))
                continue

            sys.path.append(path)

            for file in os.listdir(path):
                plugin_name, extension = os.path.splitext(file)

                if extension == ".py":
                    try:
                        plugin_module = __import__(plugin_name)
                    except Exception as error:
                        self.log.error("Error in >{0}< plugin: {1}".format(plugin_name, error))
                        continue

                    # instanciate plugin

                    if not hasattr(plugin_module, plugin_name):
                        continue

                    self.plugins[plugin_name] = getattr(plugin_module, plugin_name)(
                        app, gui, os.path.dirname(plugin_module.__file__)
                    )

                    if plugin_name in plugins_config:
                        self.plugins[plugin_name].Config.update(plugins_config[plugin_name])

                    self.log.info("Found: {}".format(plugin_name))

        for plugin in self.enabled_plugins:
            if plugin not in self.plugins.keys():
                self.log.error("Error: Plugin >{}< not found.".format(plugin))
                self.enabled_plugins.remove(plugin)
            else:
                self.plugins[plugin].enable()
                self.log.info("Enabled: {}".format(plugin))

    def enable(self, name):
        if name not in self.enabled_plugins:
            self.enabled_plugins.append(name)
        self.plugins[name].enable()

    def disable(self, name):
        self.enabled_plugins.remove(name)
        self.plugins[name].disable()

    def get_config(self):
        plugins_config = {}
        for plugin_name in self.plugins:
            if self.plugins[plugin_name].Configurable:
                plugins_config[plugin_name] = self.plugins[plugin_name].Config

        enabled_plugins = ":".join(self.enabled_plugins)

        return enabled_plugins, plugins_config
