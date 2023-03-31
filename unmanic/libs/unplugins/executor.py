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
import copy
import gc
import os
import importlib.util
import importlib
import sys

from . import plugin_types
from unmanic.libs import unlogger, common
from ..unmodels import LibraryPluginFlow


class PluginExecutor(object):

    def __init__(self, plugins_directory=None):
        # Set plugins directory
        if not plugins_directory:
            home_directory = common.get_home_dir()
            plugins_directory = os.path.join(home_directory, '.unmanic', 'plugins')
        self.plugins_directory = plugins_directory
        # List plugin types in order that they are run
        # Listing them in order helps for the frontend
        self.plugin_types = [
            {
                'id':       'frontend.panel',
                'has_flow': False,
            },
            {
                'id':       'frontend.plugin_api',
                'has_flow': False,
            },
            {
                'id':       'library_management.file_test',
                'has_flow': True,
            },
            {
                'id':       'worker.process_item',
                'has_flow': True,
            },
            {
                'id':       'postprocessor.file_move',
                'has_flow': True,
            },
            {
                'id':       'postprocessor.task_result',
                'has_flow': True,
            },
        ]
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

    @staticmethod
    def __include_plugin_site_packages(path):
        plugin_site_packages_dir = os.path.join(path, 'site-packages')
        if os.path.exists(plugin_site_packages_dir) and plugin_site_packages_dir not in sys.path:
            sys.path.append(plugin_site_packages_dir)

    @staticmethod
    def __include_plugin_directory(path):
        if os.path.exists(path) and path not in sys.path:
            sys.path.append(path)

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

        # Ensure the Unmanic plugins directory to sys path prior to loading it
        self.__include_plugin_directory(self.plugins_directory)

        # Add site-packages directory to sys path prior to loading the module
        self.__include_plugin_site_packages(path)

        # Don't re-import the module if it is already loaded.
        if module_name in sys.modules:
            return sys.modules[module_name]

        try:
            # First import the module namespace
            # Without this we are unable to reload the plugin in reload_plugin_module()
            importlib.import_module(plugin_id)

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

    def reload_plugin_module(self, plugin_id):
        """
        Reload a plugin module

        :param plugin_id:
        :return:
        """
        # Set the module name
        module_name = '{}.plugin'.format(plugin_id)
        # self._log("Reloading module '{}'".format(module_name), level="debug")

        if module_name in sys.modules:
            # Get all submodules
            module_names = [module_name]
            for m in sys.modules:
                if plugin_id in m and m not in [plugin_id, module_name]:
                    # Add to removal list
                    module_names.append(m)
            # Reload all imported modules or remove them if that fails
            for mn in module_names:
                try:
                    importlib.reload(sys.modules[mn])
                except ImportError:
                    # The module's parent was probably not imported.
                    # Delete it from sys.modules and carry on.
                    # This will force it to be reloaded again
                    self._log("Exception encountered while trying to reload module '{}'".format(module_name),
                              level="exception")
                    del sys.modules[module_name]

    @staticmethod
    def unload_plugin_module(plugin_id):
        """
        Remove plugin module from sys.modules

        This does not really clean up memory. Things are still getting really messy behind the scenes.
        This just makes it remove the module so that it will need to be re-imported above.

        :param plugin_id:
        :return:
        """
        # Set the module name
        module_name = '{}.plugin'.format(plugin_id)

        if module_name in sys.modules:
            del sys.modules[module_name]

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
            plugin_type_meta = self.get_plugin_type_meta(plugin_type.get('id'))
            plugin_runner = plugin_type_meta.plugin_runner()

            # Check if this module contains the given plugin type runner function
            if hasattr(plugin_module, plugin_runner):
                # If it does, add it to the plugin_modules list
                return_plugin_types.append(plugin_type.get('id'))

        return return_plugin_types

    def execute_plugin_runner(self, data, plugin_id, plugin_type):
        """
        Given a data, a plugin ID, and a plugin type
        Load that plugin module and execute the runner
        Return the modified data

        :param data:
        :param plugin_id:
        :param plugin_type:
        :return:
        """
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        # Get the called runner function for the given plugin type
        plugin_type_meta = self.get_plugin_type_meta(plugin_type)
        plugin_runner = plugin_type_meta.plugin_runner()

        # Check if this module contains the given plugin type runner
        run_successfully = False
        if hasattr(plugin_module, plugin_runner):

            # If it does, get the runner function
            runner = getattr(plugin_module, plugin_runner)

            try:
                runner(data)
                run_successfully = True
            except Exception:
                self._log("Exception while carrying out '{}' plugin runner '{}'".format(plugin_type, plugin_id),
                          level="exception")

            del runner
            # gc.collect()

        return run_successfully

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
        # Filter out only plugins that have runners of this type
        plugin_data = self.build_plugin_data_from_plugin_list_filtered_by_plugin_type(enabled_plugins, plugin_type)

        # Return runners
        return plugin_data

    def get_plugin_settings(self, plugin_id, library_id=None):
        """
        Returns a dictionary of a given plugin's settings

        :param plugin_id:
        :param library_id:
        :return:
        """
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        if not hasattr(plugin_module, 'Settings'):
            # This plugin does not have a settings class
            return {}, {}

        try:
            # Settings plugin_settings
            plugin_settings = plugin_module.Settings(library_id=library_id)

            all_plugin_settings = copy.deepcopy(plugin_settings.get_setting())
            plugin_form_settings = copy.deepcopy(plugin_settings.get_form_settings())
        except Exception as e:
            self._log("Exception while fetching settings for plugin '{}'".format(plugin_id), str(e), level='exception')
            all_plugin_settings = {}
            plugin_form_settings = {}

        return all_plugin_settings, plugin_form_settings

    def save_plugin_settings(self, plugin_id, settings, library_id=None):
        """
        Saves a collection of a given plugin's settings.
        Returns a boolean result for the overall success
        of saving all values.

        :param plugin_id:
        :param settings:
        :param library_id:
        :return:
        """
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        try:
            plugin_settings = plugin_module.Settings(library_id=library_id)

            save_result = True
            for key in settings:
                value = settings.get(key)
                if not plugin_settings.set_setting(key, value):
                    save_result = False

            del plugin_settings, plugin_module

            if save_result:
                self.reload_plugin_module(plugin_id)

            return save_result
        except Exception as e:
            self._log("Exception while saving settings for plugin '{}'".format(plugin_id), str(e), level='exception')
            self._log(str(e), level='exception')
            return False

    def reset_plugin_settings(self, plugin_id, library_id=None):
        """
        Reset a plugin settings by removing the config file

        :param plugin_id:
        :param library_id:
        :return:
        """
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)

        # Load this plugin module
        plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

        try:
            plugin_settings = plugin_module.Settings(library_id=library_id)
            return plugin_settings.reset_settings_to_defaults()
        except Exception as e:
            self._log("Exception while resetting settings for plugin '{}'".format(plugin_id), str(e), level='exception')
            return False

    def get_plugin_changelog(self, plugin_id):
        """
        Returns a list of lines from the plugin's changelog

        :param plugin_id:
        :return:
        """
        changelog = []
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)
        plugin_changelog = os.path.join(plugin_path, 'changelog.md')
        if os.path.exists(plugin_changelog):
            with open(plugin_changelog, 'r') as f:
                changelog = f.readlines()

        return changelog

    def get_plugin_long_description(self, plugin_id):
        """
        Returns a list of lines from the plugin's additional description file

        :param plugin_id:
        :return:
        """
        description = []
        # Get the path for this plugin
        plugin_path = self.__get_plugin_directory(plugin_id)
        plugin_description = os.path.join(plugin_path, 'description.md')
        if os.path.exists(plugin_description):
            with open(plugin_description, 'r') as f:
                description = f.readlines()

        return description

    def test_plugin_runner(self, plugin_id, plugin_type, test_data=None, test_data_modifiers=None):
        if test_data is None:
            test_data = {}
        if test_data_modifiers is None:
            test_data_modifiers = {}
        try:
            # Get the path for this plugin
            plugin_path = self.__get_plugin_directory(plugin_id)

            # Load this plugin module
            plugin_module = self.__load_plugin_module(plugin_id, plugin_path)

            # Get the called runner function for the given plugin type
            plugin_type_meta = self.get_plugin_type_meta(plugin_type)
            if not test_data:
                test_data = plugin_type_meta.get_test_data()
                test_data = plugin_type_meta.modify_test_data(test_data, test_data_modifiers)
            errors = plugin_type_meta.run_data_schema_tests(plugin_id, plugin_module, test_data=test_data)
        except Exception as e:
            self._log("Exception while testing plugin runner for plugin '{}'".format(plugin_id), message2=str(e),
                      level="exception")
            errors = ["Exception encountered while testing runner - {}".format(str(e))]

        return errors

    def test_plugin_settings(self, plugin_id):
        errors = []

        # Get the called runner function for the given plugin type
        plugin_settings = {}
        try:
            plugin_settings, plugin_settings_meta = self.get_plugin_settings(plugin_id)
        except Exception as e:
            errors.append(str(e))

        return errors, plugin_settings
