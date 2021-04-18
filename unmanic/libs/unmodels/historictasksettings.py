#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.historictasksettings.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     30 Sep 2019, (6:49 PM)
 
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

import datetime

from peewee import *
from unmanic.libs.unmodels.basemodel import BaseModel
from unmanic.libs.unmodels.historictasks import HistoricTasks


class HistoricTaskSettings(BaseModel):
    """
    HistoricTaskSettings
    """
    historictask_id = ForeignKeyField(HistoricTasks)
    audio_codec = TextField(null=False)
    audio_stream_encoder = TextField(null=False)
    audio_codec_cloning = TextField(null=False)
    audio_stream_encoder_cloning = TextField(null=False)
    audio_stereo_stream_bitrate = TextField(null=False)
    cache_path = TextField(null=False)
    config_path = TextField(null=False)
    debugging = BooleanField(null=False)
    enable_audio_encoding = BooleanField(null=False)
    enable_audio_stream_transcoding = BooleanField(null=False)
    enable_audio_stream_stereo_cloning = BooleanField(null=False)
    enable_inotify = BooleanField(null=False)
    enable_video_encoding = BooleanField(null=False)
    library_path = TextField(null=False)
    log_path = TextField(null=False)
    number_of_workers = IntegerField(null=False)
    keep_original_container = BooleanField(null=False)
    out_container = TextField(null=False)
    remove_subtitle_streams = BooleanField(null=False)
    run_full_scan_on_start = BooleanField(null=False)
    schedule_full_scan_minutes = IntegerField(null=False)
    search_extensions = TextField(null=False)
    video_codec = TextField(null=False)
    additional_ffmpeg_options = TextField(null=True)
    enable_hardware_accelerated_decoding = BooleanField(null=False, default=False)
