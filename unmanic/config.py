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
from unmanic.libs import unmodels, unlogger, unffmpeg
from unmanic.libs import common, history
from unmanic.libs.singleton import SingletonType

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class CONFIG(object, metaclass=SingletonType):
    app_version = ''

    # Set the default UI Port
    UI_PORT = common.get_ui_port()

    # Set default config directory
    CONFIG_PATH = common.get_config_dir()

    # Set default plugin directory
    PLUGINS_PATH = os.path.join(common.get_home_dir(), '.unmanic', 'plugins')

    # Set default db config
    DATABASE = None

    def __init__(self, config_path=None, db_connection=None):
        # Non config items (objects)
        self.name = "Config"
        self.settings = None
        self.db_connection = db_connection

        # Apply default DB settings
        # self.apply_default_db_settings(config_path)

        # Import env variables and override all previous settings.
        self.import_settings_from_env()
        # Read settings from database
        self.import_settings_from_db()
        # TODO: Retire this. It is not needed any longer
        # Finally, re-read config from file and override all previous settings.
        self.import_settings_from_file(config_path)

        # Overwrite current settings
        if config_path:
            self.set_config_item('config_path', config_path, save_settings=False)

        # Apply settings to the unmanic logger
        self.setup_unmanic_logger()

        # Save settings
        if self.settings and self.db_connection:
            self.settings.save()

        # TODO: Remove temporary beta data migration
        history_logging = history.History(self)
        history_logging.migrate_old_beta_data()

    def _log(self, message, message2='', level="info"):
        """
        Generic logging method. Can be implemented on any unmanic class

        :param message:
        :param message2:
        :param level:
        :return:
        """
        # TODO: Format all classes with this to fetch a logger
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(self.name)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.name))

    def get_empty_settings_model(self):
        """
        Return a settings Model object
        :return:
        """
        if self.settings:
            return self.settings
        else:
            # Fetch blank settings Model object
            return unmodels.Settings()

    def get_config_as_dict(self):
        """
        Return a dictionary of configuration fields and their current values

        :return:
        """
        # Create a copy of this class's dict
        settings = self.get_empty_settings_model()
        config_dict = settings.get_current_field_values_dict()
        # Return dictionary of config items
        return config_dict

    def get_config_keys(self):
        """
        Return a list of configuration fields

        :return:
        """
        keys = self.get_config_as_dict().keys()
        keys = [item.upper() for item in keys]
        return keys

    def setup_unmanic_logger(self):
        """
        Pass configuration to the global logger

        :return:
        """
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        unmanic_logging.setup_logger(self)

    def apply_default_db_settings(self, config_path=None):
        """
        Apply the default DB settings.

        :return:
        """
        if not config_path:
            config_path = os.path.join(common.get_home_dir(), '.unmanic', 'config')
        app_dir = os.path.dirname(os.path.abspath(__file__))
        self.DATABASE = {
            "TYPE":           "SQLITE",
            "FILE":           os.path.join(config_path, 'unmanic.db'),
            "MIGRATIONS_DIR": os.path.join(app_dir, 'migrations'),
        }

    def import_settings_from_db(self):
        """
        Read configuration from DB.
        If configuration does not yet exist, create it first.

        Configuration is applied to this class with uppercase field names
        for the sake of simplifying reading throughout the rest of the application.

        :return:
        """
        # Fetch current settings (create it if nothing yet exists)
        db_settings = unmodels.Settings()
        # If there is no DB connection just create an empty settings model
        if self.db_connection:
            try:
                # Fetch a single row (get() will raise DoesNotExist exception if no results are found)
                self.settings = db_settings.select().limit(1).get()
            except:
                # Create settings (defaults will be applied)
                self.settings = db_settings.create()
        else:
            self.settings = self.get_empty_settings_model()
        # Check if key is a valid setting
        current_settings = self.get_config_as_dict()
        for setting in current_settings:
            # Import settings
            self.set_config_item(setting.upper(), current_settings[setting], save_settings=False)

    def import_settings_from_env(self):
        """
        Read configuration from environment variables.
        This is useful for running in a docker container or for unit testing.

        :return:
        """
        for setting in self.get_config_keys():
            if setting in os.environ:
                self.set_config_item(setting, os.environ.get(setting), save_settings=False)

    def import_settings_from_file(self, config_path=None):
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
            # Set values that match the settings model attributes
            current_config = self.get_config_keys()
            for item in current_config:
                if item in data:
                    self.set_config_item(item, data[item], save_settings=False)
            # Set config values that are in the 'DATABASE' or 'UI_PORT' keys (if provided)
            if 'DATABASE' in data:
                setattr(self, 'DATABASE', data['DATABASE'])
            if 'UI_PORT' in data:
                setattr(self, 'UI_PORT', data['UI_PORT'])

    def write_settings_to_file(self):
        """
        Dump current settings to the settings JSON file.

        :return:
        """
        if not os.path.exists(self.get_config_path()):
            os.makedirs(self.get_config_path())
        settings_file = os.path.join(self.get_config_path(), 'settings.json')
        data = self.get_config_as_dict()
        data = {k.upper(): v for k, v in data.items()}
        result = common.json_dump_to_file(data, settings_file)
        if not result['success']:
            for message in result['errors']:
                self._log("Exception in writing settings to file:", message2=str(message), level="exception")

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

        # Second attempt to fetch it from the Settings Model
        if hasattr(self.settings, key):
            return getattr(self.settings, key)

    def set_config_item(self, key, value, save_settings=True):
        """
        Assigns a value to a given configuration field.
        This is applied to both this class and the Settings Model.

        If 'save_settings' is set to False, then settings are only
        assigned and not saved to either file or database.

        :param key:
        :param value:
        :param save_settings:
        :return:
        """
        if key == 'DATABASE':
            # Only save database settings to file
            # Database settings are not stored in the database O_o
            self.__dict__[key] = value
            if save_settings:
                self.write_settings_to_file()
        else:
            # Get lowercase value of key
            field_id = key.lower()
            # Check if key is a valid setting
            if field_id not in self.get_config_as_dict().keys():
                self._log("Attempting to save unknown key", message2=str(key), level="warning")
                # Do not proceed if this is any key other than the database
                return
            settings_model = self.get_empty_settings_model()
            # Parse field value by it's type for this setting (bool, string, etc.)
            parsed_field_value = settings_model.parse_field_value_by_type(field_id, value)
            if self.settings:
                # Assign value to setting field
                setattr(self.settings, field_id, parsed_field_value)

            # Assign field type converted value to class variable
            # TODO: Remove this once we have migrated to using only the settings model object
            setattr(self, key, parsed_field_value)

            # Save settings (if requested)
            if save_settings:
                self.write_settings_to_file()
                if self.settings and self.db_connection:
                    self.settings.save()

    def allowed_search_extensions(self):
        """
        Return a tuple of the configured extensions to search for.

        :return:
        """
        search_extensions = self.get_search_extensions()
        if isinstance(search_extensions, str):
            # Split the comma separated sting into a list
            value = search_extensions.split(",")
            # Strip all whitespace (including within the item as extensions dont have any whitespace)
            value = [item.replace(' ', '') for item in value]
            # Remove empty values from the list
            value = [item for item in value if item]
            return value
        return list(search_extensions)

    def file_ends_in_allowed_search_extensions(self, file_name):
        # Get the file extension
        file_extension = os.path.splitext(file_name)[-1][1:]
        # Ensure the file's extension is lowercase
        file_extension = file_extension.lower()
        self._log("Check file_extension", file_extension, level="debug")
        # Get the list of configured extensions to search for
        allowed_search_extensions = self.allowed_search_extensions()
        self._log("Check allowed_search_extensions", allowed_search_extensions, level="debug")
        # Check if it ends with one of the allowed search extensions
        if file_extension in allowed_search_extensions:
            return True
        return False

    def read_version(self):
        """
        Return the application's version number as a string

        :return:
        """
        if not self.app_version:
            self.app_version = metadata.read_version_string('long')
        return self.app_version

    def get_supported_containers(self):
        """
        Return a list of containers supported by unmanic

        :return:
        """
        return unffmpeg.containers.get_all_containers()

    def get_all_supported_codecs(self):
        """
        Return a list of all codecs supported by unmanic

        :return:
        """
        return unffmpeg.Info().get_all_supported_codecs()

    def get_supported_audio_codecs(self):
        """
        Return a list of audio codecs supported by unmanic

        :return:
        """
        supported_codecs = self.get_all_supported_codecs()
        if 'audio' not in supported_codecs:
            return {}
        return supported_codecs['audio']

    def get_supported_video_codecs(self):
        """
        Return a list of video codecs supported by unmanic

        :return:
        """
        supported_codecs = self.get_all_supported_codecs()
        if 'video' not in supported_codecs:
            return {}
        return supported_codecs['video']

    def get_audio_stream_encoder(self):
        """
        Get setting - audio_stream_encoder

        :return:
        """
        supported_codecs = self.get_all_supported_codecs()
        if 'audio' not in supported_codecs:
            return ''
        return self.AUDIO_STREAM_ENCODER

    def get_audio_codec_cloning(self):
        """
        Get setting - audio_codec_cloning

        :return:
        """
        return self.AUDIO_CODEC_CLONING

    def get_audio_stream_encoder_cloning(self):
        """
        Get setting - audio_stream_encoder_cloning

        :return:
        """
        return self.AUDIO_STREAM_ENCODER_CLONING

    def get_audio_stereo_stream_bitrate(self):
        """
        Get setting - audio_stereo_stream_bitrate

        :return:
        """
        return self.AUDIO_STEREO_STREAM_BITRATE

    def get_cache_path(self):
        """
        Get setting - cache_path

        :return:
        """
        return self.CACHE_PATH

    def get_config_path(self):
        """
        Get setting - config_path

        :return:
        """
        return self.CONFIG_PATH

    def get_keep_filename_history(self):
        """
        Get setting - keep_filename_history

        :return:
        """
        return self.KEEP_FILENAME_HISTORY

    def get_debugging(self):
        """
        Get setting - debugging

        :return:
        """
        return self.DEBUGGING

    def get_enable_audio_encoding(self):
        """
        Get setting - enable_audio_encoding

        :return:
        """
        return self.ENABLE_AUDIO_ENCODING

    def get_enable_audio_stream_transcoding(self):
        """
        Get setting - enable_audio_stream_transcoding

        :return:
        """
        return self.ENABLE_AUDIO_STREAM_TRANSCODING

    def get_enable_audio_stream_stereo_cloning(self):
        """
        Get setting - enable_audio_stream_stereo_cloning

        :return:
        """
        return self.ENABLE_AUDIO_STREAM_STEREO_CLONING

    def get_enable_inotify(self):
        """
        Get setting - enable_inotify

        :return:
        """
        return self.ENABLE_INOTIFY

    def get_enable_video_encoding(self):
        """
        Get setting - enable_video_encoding

        :return:
        """
        return self.ENABLE_VIDEO_ENCODING

    def get_library_path(self):
        """
        Get setting - library_path

        :return:
        """
        return self.LIBRARY_PATH

    def get_log_path(self):
        """
        Get setting - log_path

        :return:
        """
        return self.LOG_PATH

    def get_number_of_workers(self):
        """
        Get setting - number_of_workers

        :return:
        """
        return self.NUMBER_OF_WORKERS

    def get_keep_original_container(self):
        """
        Get setting - keep_original_container

        :return:
        """
        return self.KEEP_ORIGINAL_CONTAINER

    def get_out_container(self):
        """
        Get setting - out_container

        :return:
        """
        return self.OUT_CONTAINER

    def get_remove_subtitle_streams(self):
        """
        Get setting - remove_subtitle_streams

        :return:
        """
        return self.REMOVE_SUBTITLE_STREAMS

    def get_run_full_scan_on_start(self):
        """
        Get setting - run_full_scan_on_start

        :return:
        """
        return self.RUN_FULL_SCAN_ON_START

    def get_schedule_full_scan_minutes(self):
        """
        Get setting - schedule_full_scan_minutes

        :return:
        """
        return self.SCHEDULE_FULL_SCAN_MINUTES

    def get_search_extensions(self):
        """
        Get setting - search_extensions

        :return:
        """
        return self.SEARCH_EXTENSIONS

    def get_video_codec(self):
        """
        Get setting - video_codec

        :return:
        """
        return self.settings.video_codec

    def get_video_stream_encoder(self):
        """
        Get setting - video_stream_encoder

        :return:
        """
        supported_codecs = self.get_all_supported_codecs()
        if 'video' not in supported_codecs:
            return ''
        return self.VIDEO_STREAM_ENCODER

    def get_overwrite_additional_ffmpeg_options(self):
        """
        Get setting - overwrite_additional_ffmpeg_options

        :return:
        """
        return self.OVERWRITE_ADDITIONAL_FFMPEG_OPTIONS

    def get_additional_ffmpeg_options(self):
        """
        Get setting - additional_ffmpeg_options

        :return:
        """
        return self.ADDITIONAL_FFMPEG_OPTIONS

    def get_enable_hardware_accelerated_decoding(self):
        """
        Get setting - enable_hardware_accelerated_decoding

        :return:
        """
        return self.ENABLE_HARDWARE_ACCELERATED_DECODING

    def get_plugins_path(self):
        """
        Get setting - config_path

        :return:
        """
        return self.PLUGINS_PATH
