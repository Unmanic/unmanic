#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.config_data.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 May 2020, (12:40 PM)

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


class MockConfig(object):
    app_version = ''

    def __init__(self):
        # Non config items (objects)
        self.name = "Config"
        self.settings = None

        # Set default db config
        self.DATABASE = {
            "DATABASE": {
                "TYPE":           "SQLITE",
                "FILE":           '/tmp/.unmanic/config/unmanic.db',
                "MIGRATIONS_DIR": '/tmp/migrations',
            }
        }

        # Set the supported codecs (for destination)
        self.SUPPORTED_CODECS = {
            'audio':    {
                'aac':    {
                    'name':            'aac',
                    'encoders':        ['aac'],
                    'default_encoder': 'aac',
                    'description':     'AAC (Advanced Audio Coding)'
                }, 'ac3': {
                    'name':            'ac3',
                    'encoders':        ['ac3'],
                    'default_encoder': 'ac3',
                    'description':     'ATSC A/52A (AC-3)'
                },
                'mp3':    {
                    'name':            'mp3',
                    'encoders':        ['libmp3lame'],
                    'default_encoder': 'libmp3lame',
                    'description':     'MP3 (MPEG audio layer 3)'
                }
            },
            'subtitle': {},
            'video':    {
                'h264':    {
                    'name':            'h264',
                    'encoders':        ['libx264', 'libx264rgb', 'nvenc_h264'],
                    'default_encoder': 'libx264',
                    'description':     'H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10'
                }, 'hevc': {
                    'name':            'hevc',
                    'encoders':        ['libx265'],
                    'default_encoder': 'libx265',
                    'description':     'HEVC (High Efficiency Video Coding)'
                }
            }
        }

        # Set the supported containers (for destination)
        self.SUPPORTED_CONTAINERS = {
            'avi':      {
                'extension':          'avi',
                'description':        'AVI (Audio Video Interleaved)',
                'supports_subtitles': True
            },
            'flv':      {
                'extension':          'flv',
                'description':        'FLV (Flash Video)',
                'supports_subtitles': False
            },
            'matroska': {
                'extension':   'mkv',
                'description': 'Matroska', 'supports_subtitles': True
            },
            'mov':      {
                'extension':          'mov',
                'description':        'QuickTime / MOV',
                'supports_subtitles': True
            },
            'mp4':      {
                'extension':          'mp4',
                'description':        'MP4 (MPEG-4 Part 14)',
                'supports_subtitles': True
            },
            'mpeg':     {
                'extension':          'mpeg',
                'description':        'MPEG-1 Systems / MPEG program stream',
                'supports_subtitles': True
            },
            'mpegts':   {
                'extension':          'ts',
                'description':        'MPEG-TS (MPEG-2 Transport Stream)',
                'supports_subtitles': False
            },
            'ogv':      {
                'extension':          'ogv',
                'description':        'Ogg Video',
                'supports_subtitles': False
            },
            'psp':      {
                'extension':          'psp',
                'description':        'PSP MP4 (MPEG-4 Part 14)',
                'supports_subtitles': False
            },
            'vob':      {
                'extension':          'vob',
                'description':        'MPEG-2 PS (VOB)',
                'supports_subtitles': False
            }
        }

        self.AUDIO_CODEC = 'aac'
        self.AUDIO_STREAM_ENCODER = 'aac'
        self.AUDIO_CODEC_CLONING = 'aac'
        self.AUDIO_STREAM_ENCODER_CLONING = 'aac'
        self.AUDIO_STEREO_STREAM_BITRATE = '128k'
        self.CACHE_PATH = '/tmp/unmanic'
        self.CONFIG_PATH = '/tmp/.unmanic/config'
        self.KEEP_FILENAME_HISTORY = True
        self.DEBUGGING = False
        self.ENABLE_AUDIO_ENCODING = True
        self.ENABLE_AUDIO_STREAM_TRANSCODING = True
        self.ENABLE_AUDIO_STREAM_STEREO_CLONING = True
        self.ENABLE_INOTIFY = True
        self.ENABLE_VIDEO_ENCODING = True
        self.LIBRARY_PATH = '/library'
        self.LOG_PATH = '/tmp/.unmanic/logs'
        self.NUMBER_OF_WORKERS = 3
        self.OUT_CONTAINER = 'matroska'
        self.REMOVE_SUBTITLE_STREAMS = True
        self.RUN_FULL_SCAN_ON_START = False
        self.SCHEDULE_FULL_SCAN_MINUTES = 60
        self.SEARCH_EXTENSIONS = 'mkv,avi,mov,ts,rmvb,mp4,'
        self.VIDEO_CODEC = 'hevc'
        self.VIDEO_STREAM_ENCODER = 'libx265'
        self.ENABLE_HARDWARE_ACCELERATED_DECODING = False
