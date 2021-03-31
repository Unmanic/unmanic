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


class PluginExecutor(object):

    def __init__(self, plugins_directory=None):
        # Set plugins directory
        if not plugins_directory:
            plugins_directory = os.path.join(os.path.expanduser("~"), '.unmanic', 'plugins')
        self.plugins_directory = plugins_directory
        self.plugin_sort_order = {
            "column": 'position',
            "dir":    'desc',
        }
        # TODO: generate this list dynamically
        self.plugin_types = [
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

    def __get_enabled_plugins(self):
        """
        Returns a list of enabled plugins

        :return:
        """
        from unmanic.libs.plugins import PluginsHandler
        plugin_handler = PluginsHandler()
        return plugin_handler.get_plugin_list_filtered_and_sorted(order=self.plugin_sort_order, enabled=True)

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

    def get_plugin_runners_filtered_by_type(self, plugins, plugin_type):
        """
        Returns a filtered list of plugin modules for a given plugin type

        :param plugins:
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

        for plugin in plugins:
            # Get plugin ID
            plugin_id = plugin.get('plugin_id')

            # Get the path for this plugin
            plugin_path = self.__get_plugin_directory(plugin_id)

            # Load this plugin module
            plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

            # Check if this module contains the given plugin type runner function
            if hasattr(plugin_module, plugin_runner):
                # If it does, add it to the plugin_modules list
                plugin_runner_data = {
                    "plugin_id":     plugin_id,
                    "plugin_module": plugin_module,
                    "plugin_path":   plugin_path,
                    "runner":        getattr(plugin_module, plugin_runner),
                }
                plugin_modules.append(plugin_runner_data)

        return plugin_modules

    def get_plugin_modules_by_type(self, plugin_type):
        """
        Returns a list of plugin runners.
        Runners are filtered by plugin_type and sorted by order of execution.

        :param plugin_type:
        :return:
        """
        runners = []
        # Fetch all enabled plugins
        enabled_plugins = self.__get_enabled_plugins()

        # Filter out only plugins that have runners of this type
        plugin_modules = self.get_plugin_runners_filtered_by_type(enabled_plugins, plugin_type)

        plugin_modules.append(
            {
                "plugin_id":     self.default_plugin_runner_name,
                "plugin_module": None,
                "plugin_path":   None,
                "runner":        self.default_runner,
            }
        )

        # Return runners
        return plugin_modules

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

        plugin_settings = plugin_module.Settings()

        return plugin_settings.get_setting()

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
            plugin_settings = self.get_plugin_settings(plugin_id)
        except Exception as e:
            errors.append(str(e))


        return errors, plugin_settings
