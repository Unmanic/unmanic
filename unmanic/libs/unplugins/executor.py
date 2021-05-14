#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.executor.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (6:55 PM)

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
import os
import importlib.util
import importlib
import sys

from . import plugin_types
from unmanic.libs import unlogger, common
from ..unmodels.pluginflow import PluginFlow


class PluginExecutor(object):

    def __init__(self, plugins_directory=None):
        # Set plugins directory
        if not plugins_directory:
            plugins_directory = os.path.join(os.path.expanduser("~"), '.unmanic', 'plugins')
        self.plugins_directory = plugins_directory
        # TODO: generate this list dynamically
        self.plugin_types = [
            "library_management.file_test",
            "postprocessor.file_move",
            "postprocessor.task_result",
            "worker.process_item",
        ]
        self.default_plugin_runner_name = "unmanic_default_stage"
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __get_plugin_directory(self, plugin_id):
        """
        Returns the path of the plugin by it's plugin ID

        :param plugin_id:
        :return:
        """
        return os.path.join(self.plugins_directory, plugin_id)

    def __get_enabled_plugins(self, plugin_type=None):
        """
        Returns a list of enabled plugins

        :return:
        """
        from unmanic.libs.plugins import PluginsHandler
        plugin_handler = PluginsHandler()
        order = [
            {
                "model":  PluginFlow,
                "column": 'position',
                "dir":    'asc',
            },
            {
                "column": 'name',
                "dir":    'asc',
            },
        ]
        return plugin_handler.get_plugin_list_filtered_and_sorted(order=order, enabled=True, plugin_type=plugin_type)

    @staticmethod
    def __include_plugin_site_packages(path):
        plugin_site_packages_dir = os.path.join(path, 'site-packages')
        if os.path.exists(plugin_site_packages_dir) and plugin_site_packages_dir not in sys.path:
            sys.path.append(plugin_site_packages_dir)

    def __load_plugin_module(self, plugin_id, path):
        """
        Loads and returns the python module from a given plugin path.
            All plugins should have a file called "plugin.py".

        :param plugin_id:
        :param path:
        :return:
        """
        # Set the module name
        module_name = '{}.plugin'.format(plugin_id)

        # Get main module file
        plugin_module_path = os.path.join(path, 'plugin.py')

        # Add site-packages directory to sys path prior to loading the module
        self.__include_plugin_site_packages(path)

        try:
            # Import the module for this plugin
            module_spec = importlib.util.spec_from_file_location(module_name, plugin_module_path)
            plugin_import = importlib.util.module_from_spec(module_spec)

            # Adding the module to sys.modules is optional but it gives us visibility if we need it elsewhere.
            sys.modules[module_name] = plugin_import

            module_spec.loader.exec_module(plugin_import)

            return plugin_import
        except Exception as e:
            self._log("Exception encountered while importing module '{}'".format(plugin_id), message2=str(e),
                      level="exception")
            return None

    @staticmethod
    def default_runner(data):
        return data

    @staticmethod
    def get_plugin_type_meta(plugin_type):
        return plugin_types.grab_module(plugin_type)

    def get_all_plugin_types(self):
        return self.plugin_types

    def get_all_plugin_types_in_plugin(self, plugin_id):
        return_plugin_types = []

        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        for plugin_type in self.get_all_plugin_types():
            # Get the called runner function for the given plugin type
            plugin_type_meta = self.get_plugin_type_meta(plugin_type)
            plugin_runner = plugin_type_meta.plugin_runner()

            # Check if this module contains the given plugin type runner function
            if hasattr(plugin_module, plugin_runner):
                # If it does, add it to the plugin_modules list
                return_plugin_types.append(plugin_type)

        return return_plugin_types

    def build_plugin_data_from_plugin_list_filtered_by_plugin_type(self, plugins_list, plugin_type):
        """
        Given a list of plugins and a plugin type,
        Return a filtered list of dictionaries containing:
            - the plugin module
            - the runner function to execute
            - the metadata for that plugin

        :param plugins_list:
        :param plugin_type:
        :return:
        """
        plugin_modules = []

        # Ensure called runner type exists
        if not plugin_type in plugin_types.get_all_plugin_types():
            self._log("Provided plugin type does not exist!", plugin_type, level="error")
            return plugin_modules

        # Get the called runner function for the given plugin type
        plugin_type_meta = self.get_plugin_type_meta(plugin_type)
        plugin_runner = plugin_type_meta.plugin_runner()

        for plugin_data in plugins_list:
            # Get plugin ID
            plugin_id = plugin_data.get('plugin_id')

            # Get plugin metadata
            plugin_name = plugin_data.get('name')
            plugin_author = plugin_data.get('author')
            plugin_version = plugin_data.get('version')
            plugin_icon = plugin_data.get('icon')
            plugin_description = plugin_data.get('description')

            # Get the path for this plugin
            plugin_path = self.__get_plugin_directory(plugin_id)

            # Load this plugin module
            plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

            # Check if this module contains the given plugin type runner function
            if hasattr(plugin_module, plugin_runner):
                # If it does, add it to the plugin_modules list
                plugin_runner_data = {
                    "plugin_id":     plugin_id,
                    "name":          plugin_name,
                    "author":        plugin_author,
                    "version":       plugin_version,
                    "icon":          plugin_icon,
                    "description":   plugin_description,
                    "plugin_module": plugin_module,
                    "plugin_path":   plugin_path,
                    "runner":        getattr(plugin_module, plugin_runner),
                }
                plugin_modules.append(plugin_runner_data)

        return plugin_modules

    def get_plugin_data_by_type(self, enabled_plugins, plugin_type):
        """
        Given a list of enabled plugins and a plugin type
        Returns a list of dictionaries containing plugin data including
            - the plugin module
            - the runner function to execute
            - the metadata for that plugin

        :param enabled_plugins:
        :param plugin_type:
        :return:
        """
        runners = []

        # Filter out only plugins that have runners of this type
        plugin_data = self.build_plugin_data_from_plugin_list_filtered_by_plugin_type(enabled_plugins, plugin_type)

        plugin_data.append(
            {
                "plugin_id":     self.default_plugin_runner_name,
                "name":          "Default Unmanic Process",
                "author":        "N/A",
                "version":       "N/A",
                "icon":          None,
                "description":   "The default unmanic process as configured by the Unmanic settings",
                "plugin_module": None,
                "plugin_path":   None,
                "runner":        self.default_runner,
            }
        )

        # Return runners
        return plugin_data

    def get_plugin_settings(self, plugin_id):
        """
        Returns a dictionary of a given plugin's settings

        :param plugin_id:
        :return:
        """
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        if not hasattr(plugin_module, 'Settings'):
            # This plugin does not have a settings class
            return {}

        settings = plugin_module.Settings()

        plugin_settings = settings.get_setting()

        return plugin_settings, settings.form_settings

    def save_plugin_settings(self, plugin_id, settings):
        """
        Saves a collection of a given plugin's settings.
        Returns a boolean result for the overall success
        of saving all values.

        :param plugin_id:
        :param settings:
        :return:
        """
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        plugin_settings = plugin_module.Settings()

        save_result = True
        for key in settings:
            value = settings.get(key)
            if not plugin_settings.set_setting(key, value):
                save_result = False

        return save_result

    def get_plugin_changelog(self, plugin_id):
        """
        Returns a list of lines from the plugin's changelog

        :param plugin_id:
        :return:
        """
        changelog = []
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)
        plugin_changelog = os.path.join(plugin_path, 'changelog.txt')
        if os.path.exists(plugin_changelog):
            with open(plugin_changelog, 'r') as f:
                changelog = f.readlines()

        return changelog

    def test_plugin_runner(self, plugin_id, plugin_type, test_data=None):
        # Dont run a test on the default plugin runner
        if plugin_id == self.default_plugin_runner_name:
            return []

        try:
            # Get the path for this plugin
            plugin_path = self.__get_plugin_directory(plugin_id)

            # Load this plugin module
            plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

            # Get the called runner function for the given plugin type
            plugin_type_meta = self.get_plugin_type_meta(plugin_type)
            errors = plugin_type_meta.run_data_schema_tests(plugin_id, plugin_module, test_data=test_data)
        except Exception as e:
            self._log("Exception while testing plugin runner for plugin '{}'".format(plugin_id), message2=str(e),
                      level="exception")
            errors = ["Exception encountered while testing runner - {}".format(str(e))]

        return errors

    def test_plugin_settings(self, plugin_id):
        # Don't run a test on the default plugin runner
        if plugin_id == self.default_plugin_runner_name:
            return []

        errors = []

        # Get the called runner function for the given plugin type
        plugin_settings = {}
        try:
            plugin_settings, plugin_settings_meta = self.get_plugin_settings(plugin_id)
        except Exception as e:
            errors.append(str(e))

        return errors, plugin_settings
