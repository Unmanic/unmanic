#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.config.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2018, (7:21 AM)

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
import json

from unmanic import metadata
from unmanic.libs import unlogger
from unmanic.libs import common
from unmanic.libs.singleton import SingletonType

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class Config(object, metaclass=SingletonType):
    app_version = ''

    test = ''

    def __init__(self, config_path=None, **kwargs):
        # Set the default UI Port
        self.ui_port = 8888

        # Set default directories
        home_directory = common.get_home_dir()
        self.config_path = os.path.join(home_directory, '.unmanic', 'config')
        self.log_path = os.path.join(home_directory, '.unmanic', 'logs')
        self.plugins_path = os.path.join(home_directory, '.unmanic', 'plugins')
        self.userdata_path = os.path.join(home_directory, '.unmanic', 'userdata')

        # Configure debugging
        self.debugging = False

        # Configure first run (future feature)
        self.first_run = False

        # Configure first run (future feature)
        self.release_notes_viewed = None

        # Library Settings:
        self.library_path = common.get_default_library_path()
        self.enable_library_scanner = False
        self.schedule_full_scan_minutes = 1440
        self.follow_symlinks = True
        self.concurrent_file_testers = 2
        self.run_full_scan_on_start = False
        self.clear_pending_tasks_on_restart = True
        self.auto_manage_completed_tasks = False
        self.max_age_of_completed_tasks = 91
        self.always_keep_failed_tasks = True

        # Worker settings
        self.cache_path = common.get_default_cache_path()

        # Link settings
        self.installation_name = ''
        self.remote_installations = []
        self.distributed_worker_count_target = 0

        # Legacy config
        # TODO: Remove this before next major version bump
        self.number_of_workers = None
        self.worker_event_schedules = None

        # Import env variables and override all previous settings.
        self.__import_settings_from_env()

        # Import Unmanic path settings from command params
        if kwargs.get('unmanic_path'):
            self.set_config_item('config_path', os.path.join(kwargs.get('unmanic_path'), 'config'), save_settings=False)
            self.set_config_item('plugins_path', os.path.join(kwargs.get('unmanic_path'), 'plugins'), save_settings=False)
            self.set_config_item('userdata_path', os.path.join(kwargs.get('unmanic_path'), 'userdata'), save_settings=False)

        # Finally, re-read config from file and override all previous settings.
        self.__import_settings_from_file(config_path)

        # Overwrite current settings with given args
        if config_path:
            self.set_config_item('config_path', config_path, save_settings=False)

        # Overwrite all other settings passed from command params
        if kwargs.get('port'):
            self.set_config_item('ui_port', kwargs.get('port'), save_settings=False)

        # Apply settings to the unmanic logger
        self.__setup_unmanic_logger()

    def _log(self, message, message2='', level="info"):
        """
        Generic logging method. Can be implemented on any unmanic class

        :param message:
        :param message2:
        :param level:
        :return:
        """
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(__class__.__name__)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.__name__))

    def get_config_as_dict(self):
        """
        Return a dictionary of configuration fields and their current values

        :return:
        """
        return self.__dict__

    def get_config_keys(self):
        """
        Return a list of configuration fields

        :return:
        """
        return self.get_config_as_dict().keys()

    def __setup_unmanic_logger(self):
        """
        Pass configuration to the global logger

        :return:
        """
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        unmanic_logging.setup_logger(self)

    def __import_settings_from_env(self):
        """
        Read configuration from environment variables.
        This is useful for running in a docker container or for unit testing.

        :return:
        """
        for setting in self.get_config_keys():
            if setting in os.environ:
                self.set_config_item(setting, os.environ.get(setting), save_settings=False)

    def __import_settings_from_file(self, config_path=None):
        """
        Read configuration from the settings JSON file.

        :return:
        """
        # If config path was not passed as variable, use the default one
        if not config_path:
            config_path = self.get_config_path()
        # Ensure the config path exists
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        settings_file = os.path.join(config_path, 'settings.json')
        if os.path.exists(settings_file):
            data = {}
            try:
                with open(settings_file) as infile:
                    data = json.load(infile)
            except Exception as e:
                self._log("Exception in reading saved settings from file:", message2=str(e), level="exception")
            # Set data to Config class
            self.set_bulk_config_items(data, save_settings=False)

    def __write_settings_to_file(self):
        """
        Dump current settings to the settings JSON file.

        :return:
        """
        if not os.path.exists(self.get_config_path()):
            os.makedirs(self.get_config_path())
        settings_file = os.path.join(self.get_config_path(), 'settings.json')
        data = self.get_config_as_dict()
        result = common.json_dump_to_file(data, settings_file)
        if not result['success']:
            for message in result['errors']:
                self._log("Error:", message2=str(message), level="error")
            raise Exception("Exception in writing settings to file")

    def get_config_item(self, key):
        """
        Get setting from either this class or the Settings model

        :param key:
        :return:
        """
        # First attempt to fetch it from this class' get functions
        if hasattr(self, "get_{}".format(key)):
            getter = getattr(self, "get_{}".format(key))
            if callable(getter):
                return getter()

    def set_config_item(self, key, value, save_settings=True):
        """
        Assigns a value to a given configuration field.
        This is applied to both this class.

        If 'save_settings' is set to False, then settings are only
        assigned and not saved to file.

        :param key:
        :param value:
        :param save_settings:
        :return:
        """
        # Get lowercase value of key
        field_id = key.lower()
        # Check if key is a valid setting
        if field_id not in self.get_config_keys():
            self._log("Attempting to save unknown key", message2=str(key), level="warning")
            # Do not proceed if this is any key other than the database
            return

        # If in a special config list, execute that command
        if hasattr(self, "set_{}".format(key)):
            setter = getattr(self, "set_{}".format(key))
            if callable(setter):
                setter(value)
        else:
            # Assign value directly to class attribute
            setattr(self, key, value)

        # Save settings (if requested)
        if save_settings:
            try:
                self.__write_settings_to_file()
            except Exception as e:
                self._log("Failed to write settings to file: ", message2=str(self.get_config_as_dict()), level="exception")

    def set_bulk_config_items(self, items, save_settings=True):
        """
        Write bulk config items to this class.

        :param items:
        :param save_settings:
        :return:
        """
        # Set values that match the settings model attributes
        config_keys = self.get_config_keys()
        for config_key in config_keys:
            # Only import the item if it exists (Running a get here would default a missing var to None)
            if config_key in items:
                self.set_config_item(config_key, items[config_key], save_settings=save_settings)

    @staticmethod
    def read_version():
        """
        Return the application's version number as a string

        :return:
        """
        return metadata.read_version_string('long')

    def read_system_logs(self, lines=None):
        """
        Return an array of system log lines

        :param lines:
        :return:
        """
        log_lines = []
        log_file = os.path.join(self.log_path, 'unmanic.log')
        line_count = 0
        for line in reversed(list(open(log_file))):
            log_lines.insert(0, line.rstrip())
            line_count += 1
            if line_count == lines:
                break
        return log_lines

    def get_ui_port(self):
        """
        Get setting - ui_port

        :return:
        """
        return self.ui_port

    def get_cache_path(self):
        """
        Get setting - cache_path

        :return:
        """
        return self.cache_path

    def set_cache_path(self, cache_path):
        """
        Get setting - cache_path

        :return:
        """
        if cache_path == "":
            self._log("Cache path cannot be empty. Resetting it to default", level="warning")
            cache_path = common.get_default_cache_path()
        self.cache_path = cache_path

    def get_config_path(self):
        """
        Get setting - config_path

        :return:
        """
        return self.config_path

    def get_debugging(self):
        """
        Get setting - debugging

        :return:
        """
        return self.debugging

    def set_debugging(self, value):
        """
        Set setting - debugging

        This requires an update to the logger object

        :return:
        """
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        if value:
            unmanic_logging.enable_debugging()
        else:
            unmanic_logging.disable_debugging()
        self.debugging = value

    def get_first_run(self):
        """
        Get setting - first_run

        :return:
        """
        return self.first_run

    def get_release_notes_viewed(self):
        """
        Get setting - release_notes_viewed

        :return:
        """
        return self.release_notes_viewed

    def get_library_path(self):
        """
        Get setting - library_path

        :return:
        """
        return self.library_path

    def get_clear_pending_tasks_on_restart(self):
        """
        Get setting - clear_pending_tasks_on_restart

        :return:
        """
        return self.clear_pending_tasks_on_restart

    def get_auto_manage_completed_tasks(self):
        """
        Get setting - auto_manage_completed_tasks

        :return:
        """
        return self.auto_manage_completed_tasks

    def get_max_age_of_completed_tasks(self):
        """
        Get setting - max_age_of_completed_tasks

        :return:
        """
        return self.max_age_of_completed_tasks

    def get_always_keep_failed_tasks(self):
        """
        Get setting - always_keep_failed_tasks

        :return:
        """
        return self.always_keep_failed_tasks

    def get_log_path(self):
        """
        Get setting - log_path

        :return:
        """
        return self.log_path

    def get_number_of_workers(self):
        """
        Get setting - number_of_workers

        :return:
        """
        return self.number_of_workers

    def get_worker_event_schedules(self):
        """
        Get setting - worker_event_schedules

        :return:
        """
        return self.worker_event_schedules

    def get_enable_library_scanner(self):
        """
        Get setting - enable_library_scanner

        :return:
        """
        return self.enable_library_scanner

    def get_run_full_scan_on_start(self):
        """
        Get setting - run_full_scan_on_start

        :return:
        """
        return self.run_full_scan_on_start

    def get_schedule_full_scan_minutes(self):
        """
        Get setting - schedule_full_scan_minutes

        :return:
        """
        return self.schedule_full_scan_minutes

    def get_follow_symlinks(self):
        """
        Get setting - follow_symlinks

        :return:
        """
        return self.follow_symlinks

    def get_concurrent_file_testers(self):
        """
        Get setting - concurrent_file_testers

        :return:
        """
        return self.concurrent_file_testers

    def get_plugins_path(self):
        """
        Get setting - config_path

        :return:
        """
        return self.plugins_path

    def get_userdata_path(self):
        """
        Get setting - userdata_path

        :return:
        """
        return self.userdata_path

    def get_installation_name(self):
        """
        Get setting - installation_name

        :return:
        """
        return self.installation_name

    def get_remote_installations(self):
        """
        Get setting - remote_installations

        :return:
        """
        remote_installations = []
        for ri in self.remote_installations:
            ri['distributed_worker_count_target'] = self.distributed_worker_count_target
            remote_installations.append(ri)
        return remote_installations

    def get_distributed_worker_count_target(self):
        """
        Get setting - distributed_worker_count_target

        :return:
        """
        return self.distributed_worker_count_target
