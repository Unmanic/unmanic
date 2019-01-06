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
from lib import common

import json
try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

HOME_DIR = os.path.expanduser("~")
APP_DIR  = os.path.dirname(os.path.abspath(__file__))

class CONFIG(object):
    def __init__(self):
        common._logger("Importing configuration")

        self.readVersion()

        ### Set defaults
        # TODO: Set these back to defaults
        self.CONFIG_PATH=os.path.join(HOME_DIR, '.unmanic', 'config')
        self.LIBRARY_PATH='/library'
        self.CACHE_PATH='/tmp/unmanic'
        self.VIDEO_CODEC='hevc'
        self.AUDIO_CODEC='aac'
        self.OUT_CONTAINER='mkv'
        self.SUPPORTED_CONTAINERS=('mkv','avi','mov','ts','rmvb','mp4',)
        self.REMOVE_SUBTITLE_STREAMS=True
        self.DEBUGGING=True
        self.AUDIO_STEREO_STREAM_BITRATE='128k'
        self.SCHEDULE_FULL_SCAN_MINS='60'
        self.RUN_FULL_SCAN_ON_START=False
        self.NUMBER_OF_WORKERS='3'

        ### Set the supported codecs (for destination)
        # TODO: Read this from ffmpeg
        self.CODEC_CONFIG = {
            "hevc": {
                "type":"video",
                "codec_long_name":"HEVC (High Efficiency Video Coding)",
                "encoder":"libx265"
            },
            "h264": {
                "type":"video",
                "codec_long_name":"H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                "encoder":"libx264"
            },
            "aac": {
                "type":"audio",
                "codec_long_name":"AAC (Advanced Audio Coding)",
                "encoder":"aac"
            },
            "mp3": {
                "type":"audio",
                "codec_long_name":"MP3 (MPEG audio layer 3)",
                "encoder":"libmp3lame"
            }
        }

        ### Set the supported muxers (for destination)
        # TODO: Read this from ffmpeg
        self.MUXER_CONFIG = {
            "avi": {
                "extension":"avi",
                "description":"AVI (Audio Video Interleaved)",
            },
            "matroska": {
                "extension":"mkv",
                "description":"Matroska",
            },
        }

        ### Import env variables and override defaults
        self.importSettingsFromEnv()

        ### Finally, read config from file and override all above settings.
        self.readSettingsFromFile()

    def importSettingsFromEnv(self):
        # TODO: Shorten this into a function if possible
        if "LIBRARY_PATH" in os.environ:
            self.LIBRARY_PATH = os.environ.get("LIBRARY_PATH")
        if "CACHE_PATH" in os.environ:
            self.CACHE_PATH = os.environ.get("CACHE_PATH")
        if "VIDEO_CODEC" in os.environ:
            self.VIDEO_CODEC = os.environ.get("VIDEO_CODEC")
        if "AUDIO_CODEC" in os.environ:
            self.AUDIO_CODEC = os.environ.get("AUDIO_CODEC")
        if "OUT_CONTAINER" in os.environ:
            self.OUT_CONTAINER = os.environ.get("OUT_CONTAINER")
        if "SUPPORTED_CONTAINERS" in os.environ:
            self.SUPPORTED_CONTAINERS = tuple(os.environ.get("SUPPORTED_CONTAINERS").split(","))
        if "REMOVE_SUBTITLE_STREAMS" in os.environ:
            self.REMOVE_SUBTITLE_STREAMS = True if os.environ.get("REMOVE_SUBTITLE_STREAMS").lower() in ['t','true','1'] else False
        if "DEBUGGING" in os.environ:
            self.DEBUGGING = True if os.environ.get("DEBUGGING").lower() in ['t','true','1'] else False
        if "SCHEDULE_FULL_SCAN_MINS" in os.environ:
            value = os.environ.get("SCHEDULE_FULL_SCAN_MINS")
            if value.isdigit():
                self.SCHEDULE_FULL_SCAN_MINS = value
        if "AUDIO_STEREO_STREAM_BITRATE" in os.environ:
            self.AUDIO_STEREO_STREAM_BITRATE = os.environ.get("AUDIO_STEREO_STREAM_BITRATE")


    def readSettingsFromFile(self):
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        settings_file = os.path.join(self.CONFIG_PATH, 'settings.json')
        if os.path.exists(settings_file):
            data = {}
            try:
                with open(settings_file) as infile:
                    data = json.load(infile)
            except Exception as e:
                common._logger("Exception in reading saved settings from file:", message2=str(e), level="exception")
            current_config = self.getConfigAsDict()
            for item in current_config:
                if item in data:
                    self.setConfigItem(item, data[item], save_to_file=False)

    def writeSettingsToFile(self):
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        settings_file = os.path.join(self.CONFIG_PATH, 'settings.json')
        data = self.getConfigAsDict()
        try:
            with open(settings_file, 'w') as outfile:
                json.dump(data, outfile, sort_keys = True, indent = 4)
        except Exception as e:
            common._logger("Exception in writing settings to file:", message2=str(e), level="exception")

    def getConfigAsDict(self):
        return self.__dict__

    def getConfigKeys(self):
        return self.__dict__.keys()

    def setConfigItem(self, key, value, save_to_file=True):
        ### Import env variables and overide defaults
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
                value = True if value.lower() in ['t','true','1'] else False
            self.REMOVE_SUBTITLE_STREAMS = value
        if "DEBUGGING" in key:
            if isinstance(value, str):
                value = True if value.lower() in ['t','true','1'] else False
            self.DEBUGGING = value
        if "SCHEDULE_FULL_SCAN_MINS" in key:
            if value.isdigit():
                self.SCHEDULE_FULL_SCAN_MINS = value
        if "RUN_FULL_SCAN_ON_START" in key:
            if isinstance(value, str):
                value = True if value.lower() in ['t','true','1'] else False
            self.RUN_FULL_SCAN_ON_START = value
        if "AUDIO_STEREO_STREAM_BITRATE" in key:
            self.AUDIO_STEREO_STREAM_BITRATE = value
        ### Save to file
        if save_to_file:
            self.writeSettingsToFile()

    def getSupportedVideoConfigs(self):
        return_list = {}
        for x in self.CODEC_CONFIG:
            if self.CODEC_CONFIG[x]['type'] == 'video':
                return_list[x] = self.CODEC_CONFIG[x]
        return return_list

    def getSupportedAudioConfigs(self):
        return_list = {}
        for x in self.CODEC_CONFIG:
            if self.CODEC_CONFIG[x]['type'] == 'audio':
                return_list[x] = self.CODEC_CONFIG[x]
        return return_list

    def readHistoryLog(self):
        data = []
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        history_file = os.path.join(self.CONFIG_PATH, 'history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                common._logger("ValueError in reading history from file:", level="exception")
            except Exception as e:
                common._logger("Exception in reading history from file:", message2=str(e), level="exception")
        data.reverse()
        return data

    def writeHistoryLog(self, data):
        common._logger("Writing to history file", message2=data)
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)
        history_file = os.path.join(self.CONFIG_PATH, 'history.json')
        try:
            with open(history_file, 'w') as outfile:
                json.dump(data, outfile, sort_keys = True, indent = 4)
        except Exception as e:
            common._logger("Exception in writing history to file:", message2=str(e), level="exception")

    def readVersion(self):
        version_file = os.path.join(APP_DIR,'version')
        with open(version_file,'r') as f:
            version = f.read()
        self.VERSION = version

