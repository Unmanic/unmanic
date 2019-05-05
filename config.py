#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Dec 06 2018, (7:21:18 AM)
#
#   Copyright:
#          Copyright (C) Josh Sunnex - All Rights Reserved
#
#          Permission is hereby granted, free of charge, to any person obtaining a copy
#          of this software and associated documentation files (the "Software"), to deal
#          in the Software without restriction, including without limitation the rights
#          to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#          copies of the Software, and to permit persons to whom the Software is
#          furnished to do so, subject to the following conditions:
# 
#          The above copyright notice and this permission notice shall be included in all
#          copies or substantial portions of the Software.
# 
#          THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#          EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#          MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#          IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#          DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#          OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#          OR OTHER DEALINGS IN THE SOFTWARE.
#
#
###################################################################################################

import os
import time
from lib import common

import json

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

HOME_DIR = os.path.expanduser("~")
APP_DIR = os.path.dirname(os.path.abspath(__file__))


class CONFIG(object):
    def __init__(self, logger=None):
        self.name = "Config"
        self.logger = logger

        # Set defaults
        self.CONFIG_PATH = os.path.join(HOME_DIR, '.unmanic', 'config')
        self.LOG_PATH = os.path.join(HOME_DIR, '.unmanic', 'logs')
        self.LIBRARY_PATH = '/library'
        self.CACHE_PATH = '/tmp/unmanic'
        self.VIDEO_CODEC = 'hevc'
        self.AUDIO_CODEC = 'aac'
        self.OUT_CONTAINER = 'mkv'
        self.SUPPORTED_CONTAINERS = ('mkv', 'avi', 'mov', 'ts', 'rmvb', 'mp4',)
        self.REMOVE_SUBTITLE_STREAMS = True
        self.DEBUGGING = False
        self.AUDIO_STEREO_STREAM_BITRATE = '128k'
        self.SCHEDULE_FULL_SCAN_MINS = '60'
        self.RUN_FULL_SCAN_ON_START = False
        self.NUMBER_OF_WORKERS = '3'
        self.INOTIFY = True

        # Set the supported codecs (for destination)
        # TODO: Read this from ffmpeg
        self.CODEC_CONFIG = {
            "hevc": {
                "type": "video",
                "codec_long_name": "HEVC (High Efficiency Video Coding)",
                "encoder": "libx265"
            },
            "h264": {
                "type": "video",
                "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                "encoder": "libx264"
            },
            "aac": {
                "type": "audio",
                "codec_long_name": "AAC (Advanced Audio Coding)",
                "encoder": "aac"
            },
            "mp3": {
                "type": "audio",
                "codec_long_name": "MP3 (MPEG audio layer 3)",
                "encoder": "libmp3lame"
            }
        }

        # Set the supported muxers (for destination)
        self.MUXER_CONFIG = {
            "3g2": {
                "extension": "3g2",
                "description": "3GP2 (3GPP2 file format)",
            },
            "3gp": {
                "extension": "3gp",
                "description": "3GP (3GPP file format)",
            },
            "avi": {
                "extension": "avi",
                "description": "AVI (Audio Video Interleaved)",
            },
            "flv": {
                "extension": "flv",
                "description": "FLV (Flash Video)",
            },
            "matroska": {
                "extension": "mkv",
                "description": "Matroska",
            },
            "mov": {
                "extension": "mov",
                "description": "QuickTime / MOV",
            },
            "mp4": {
                "extension": "mp4",
                "description": "MP4 (MPEG-4 Part 14)",
            },
            "mpeg": {
                "extension": "mpeg",
                "description": "MPEG-1 Systems / MPEG program stream",
            },
            "mpegts": {
                "extension": "ts",
                "description": "MPEG-TS (MPEG-2 Transport Stream)",
            },
            "ogv": {
                "extension": "ogv",
                "description": "Ogg Video",
            },
            "psp": {
                "extension": "psp",
                "description": "PSP MP4 (MPEG-4 Part 14)",
            },
            "vob": {
                "extension": "vob",
                "description": "MPEG-2 PS (VOB)",
            },
        }

        # Import env variables and override defaults
        self.import_settings_from_env()

        # Finally, read config from file and override all above settings.
        self.read_settings_from_file()

    def _log(self, message, message2='', level="info"):
        if self.logger:
            message = common.format_message(message, message2)
            getattr(self.logger, level)(message)

    def import_settings_from_env(self):
        env_settings = [
            'AUDIO_CODEC',
            'AUDIO_STEREO_STREAM_BITRATE',
            'CACHE_PATH',
            'CONFIG_PATH',
            'LOG_PATH',
            'DEBUGGING',
            'LIBRARY_PATH',
            'NUMBER_OF_WORKERS',
            'OUT_CONTAINER',
            'REMOVE_SUBTITLE_STREAMS',
            'RUN_FULL_SCAN_ON_START',
            'SCHEDULE_FULL_SCAN_MINS',
            'SUPPORTED_CONTAINERS',
            'VIDEO_CODEC'
        ]
        for setting in env_settings:
            if setting in os.environ:
                self.set_config_item(setting, os.environ.get(setting), save_to_file=False)

    def read_settings_from_file(self):
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        settings_file = os.path.join(self.CONFIG_PATH, 'settings.json')
        if os.path.exists(settings_file):
            data = {}
            try:
                with open(settings_file) as infile:
                    data = json.load(infile)
            except Exception as e:
                self._log("Exception in reading saved settings from file:", message2=str(e), level="exception")
            current_config = self.get_config_as_dict()
            for item in current_config:
                if item in data:
                    self.set_config_item(item, data[item], save_to_file=False)

    def write_settings_to_file(self):
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        settings_file = os.path.join(self.CONFIG_PATH, 'settings.json')
        data = self.get_config_as_dict()
        try:
            with open(settings_file, 'w') as outfile:
                json.dump(data, outfile, sort_keys=True, indent=4)
        except Exception as e:
            self._log("Exception in writing settings to file:", message2=str(e), level="exception")

    def get_config_as_dict(self):
        # Create a copy of this class's dict
        config_dict = self.__dict__.copy()
        # Remove the logger element
        config_dict.pop('logger', None)
        # Return the remaining keys
        return config_dict

    def get_config_keys(self):
        return self.get_config_as_dict().keys()

    def set_config_item(self, key, value, save_to_file=True):
        # Import env variables and override defaults
        if "CONFIG_PATH" in key:
            self.CONFIG_PATH = value
        if "LOG_PATH" in key:
            self.LOG_PATH = value
        if "NUMBER_OF_WORKERS" in key:
            self.NUMBER_OF_WORKERS = value
        if "LIBRARY_PATH" in key:
            self.LIBRARY_PATH = value
        if "CACHE_PATH" in key:
            self.CACHE_PATH = value
        if "VIDEO_CODEC" in key:
            self.VIDEO_CODEC = value
        if "AUDIO_CODEC" in key:
            self.AUDIO_CODEC = value
        if "OUT_CONTAINER" in key:
            self.OUT_CONTAINER = value
        if "SUPPORTED_CONTAINERS" in key:
            if isinstance(value, str):
                value = value.split(",")
            self.SUPPORTED_CONTAINERS = tuple(value)
        if "REMOVE_SUBTITLE_STREAMS" in key:
            if isinstance(value, str):
                value = True if value.lower() in ['t', 'true', '1'] else False
            self.REMOVE_SUBTITLE_STREAMS = value
        if "DEBUGGING" in key:
            if isinstance(value, str):
                value = True if value.lower() in ['t', 'true', '1'] else False
            self.DEBUGGING = value
        if "SCHEDULE_FULL_SCAN_MINS" in key:
            if value.isdigit():
                self.SCHEDULE_FULL_SCAN_MINS = value
        if "RUN_FULL_SCAN_ON_START" in key:
            if isinstance(value, str):
                value = True if value.lower() in ['t', 'true', '1'] else False
            self.RUN_FULL_SCAN_ON_START = value
        if "AUDIO_STEREO_STREAM_BITRATE" in key:
            self.AUDIO_STEREO_STREAM_BITRATE = value
        if "INOTIFY" in key:
            if isinstance(value, str):
                value = True if value.lower() in ['t', 'true', '1'] else False
            self.INOTIFY = value

        # Save to file
        if save_to_file:
            self.write_settings_to_file()

    def get_supported_video_configs(self):
        return_list = {}
        for x in self.CODEC_CONFIG:
            if self.CODEC_CONFIG[x]['type'] == 'video':
                return_list[x] = self.CODEC_CONFIG[x]
        return return_list

    def get_supported_audio_configs(self):
        return_list = {}
        for x in self.CODEC_CONFIG:
            if self.CODEC_CONFIG[x]['type'] == 'audio':
                return_list[x] = self.CODEC_CONFIG[x]
        return return_list

    def read_history_log(self):
        data = []
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        history_file = os.path.join(self.CONFIG_PATH, 'history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                self._log("ValueError in reading history from file:", level="exception")
            except Exception as e:
                self._log("Exception in reading history from file:", message2=str(e), level="exception")
        data.reverse()
        return data

    def read_version(self):
        version_file = os.path.join(APP_DIR, 'version')
        with open(version_file, 'r') as f:
            version = f.read()
        return version
