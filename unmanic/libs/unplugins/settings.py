#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.settings.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     16 Mar 2021, (7:14 PM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import json
import os
import sys

from unmanic import config
from unmanic.libs.singleton import SingletonType


class PluginSettings(object, metaclass=SingletonType):
    """
    A dictionary of settings accessible to the Plugin class and able
    to be configured by users from within the Unmanic WebUI.

    """
    settings = {}

    """
    A dictionary of form settings used by Unmanic's WebUI to configure
    the plugin's settings form.

    """
    form_settings = {}

    """
    A cached copy of settings as they are stored on disk.

    """
    settings_configured = None

    def __get_plugin_settings_file(self):
        plugin_directory = self.get_plugin_directory()
        profile_directory = self.get_profile_directory()
        # Temp code to migrate settings to userdata
        # TODO: Remove after initial release
        if not os.path.exists(os.path.join(profile_directory, 'settings.json')):
            if os.path.exists(os.path.join(plugin_directory, 'settings.json')):
                import shutil
                shutil.move(
                    os.path.join(plugin_directory, 'settings.json'),
                    os.path.join(profile_directory, 'settings.json')
                )
        return os.path.join(profile_directory, 'settings.json')

    def __export_configured_settings(self):
        """
        Write settings to settings file

        :return:
        """
        plugin_settings_file = self.__get_plugin_settings_file()

        with open(plugin_settings_file, 'w') as f:
            json.dump(self.settings_configured, f, indent=2)

    def __import_configured_settings(self):
        """
        Read settings from settings file

        :return:
        """
        plugin_settings_file = self.__get_plugin_settings_file()

        # Default the configured settings to the plugin defaults
        self.settings_configured = self.settings

        # if the file does not yet exist, create it
        if not os.path.exists(plugin_settings_file):
            self.__export_configured_settings()

        # Read plugin settings from file
        with open(plugin_settings_file) as infile:
            plugin_settings = json.load(infile)

        # Loop over settings
        for key in self.settings:
            if key in plugin_settings:
                self.settings_configured[key] = plugin_settings.get(key)

    def get_plugin_directory(self):
        """
        Return the absolute path to the Plugin's directory.
        This is where the Plugin is currently installed.

        :return:
        """
        return os.path.dirname(os.path.abspath(sys.modules[self.__class__.__module__].__file__))

    def get_profile_directory(self):
        """
        Return the absolute path to the Plugin's profile directory.
        This is where where Plugin settings are saved and where all mutable data for the
        Plugin should be stored.

        :return:
        """
        settings = config.Config()
        userdata_path = settings.get_userdata_path()
        plugin_directory = self.get_plugin_directory()
        plugin_id = os.path.basename(plugin_directory)
        profile_directory = os.path.join(userdata_path, plugin_id)
        if not os.path.exists(profile_directory):
            os.makedirs(profile_directory)
        return profile_directory

    def get_form_settings(self):
        """
        Return the current form settings.

        :return:
        """
        return self.form_settings

    def get_setting(self, key=None):
        """
        Fetch a single configuration value, or, when passed "all" as the key argument,
        return the full configuration dictionary.

        :param key:
        :return:
        """
        # First import settings
        try:
            self.__import_configured_settings()
        except json.decoder.JSONDecodeError:
            # If the import fails, then it will resort to defaults.
            # That is fine. Better than breaking the rest of the process
            pass

        if key is None:
            return self.settings_configured
        else:
            return self.settings_configured.get(key)

    def set_setting(self, key, value):
        """
        Set a singe configuration value.
        Used by the Unmanic WebUI to save user settings.
        Settings are stored on disk in order to be persistent.

        :param key:
        :param value:
        :return:
        """
        # First import settings
        try:
            self.__import_configured_settings()
        except json.decoder.JSONDecodeError:
            # If the import fails, then it will resort to defaults.
            # That is fine. Better than breaking the rest of the process
            pass

        # Ensure plugin has this setting
        if key not in self.settings:
            return False

        # Set the configured value
        self.settings_configured[key] = value

        # Export the settings again
        self.__export_configured_settings()

        return True
