#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.task.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     27 Apr 2019, (2:08 PM)
 
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
import time

from unmanic.libs import common, ffmpeg
from unmanic.libs.unffmpeg import containers


class Task(object):
    """
    Task

    Contains the stage and all data pertaining to a job

    """

    def __init__(self, settings, data_queues):
        self.name = 'Task'
        self.settings = settings
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings)
        self.logger = data_queues["logging"].get_logger(self.name)
        self.source = None
        self.destination = None
        self.success = False
        self.cache_path = None
        self.statistics = {}
        self.errors = []
        self.ffmpeg_log = []

        # Reset all ffmpeg info
        self.ffmpeg.set_info_defaults()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def set_source_data(self, pathname):
        # Set source dict
        self.source = {
            'abspath': os.path.abspath(pathname),
            'basename': os.path.basename(pathname),
            'dirname': os.path.dirname(os.path.abspath(pathname))
        }

        # Set FFMPEG file in
        self.ffmpeg.set_file_in(self.source['abspath'])

        # Set the video codecs
        self.source['video_codecs'] = ','.join(self.ffmpeg.get_current_video_codecs(self.ffmpeg.file_in['file_probe']))

    def set_destination_data(self):
        # Fetch the file's name without the file extension (this is going to be reset)
        file_name_without_extension = os.path.splitext(self.source['basename'])[0]

        # Get container extension
        container = containers.grab_module(self.settings.OUT_CONTAINER)
        container_extension = container.container_extension()

        # Set destination dict
        basename = "{}.{}".format(file_name_without_extension, container_extension)
        abspath = os.path.join(self.source['dirname'], basename)
        self.destination = {
            'basename': basename,
            'abspath':  abspath
        }

    def set_cache_path(self):
        # Fetch the file's name without the file extension (this is going to be reset)
        file_name_without_extension = os.path.splitext(self.source['basename'])[0]

        # Get container extension
        container = containers.grab_module(self.settings.OUT_CONTAINER)
        container_extension = container.container_extension()

        # Parse an output cache path
        out_folder = "unmanic_file_conversion-{}".format(time.time())
        out_file = "{}-{}.{}".format(file_name_without_extension, time.time(), container_extension)
        self.cache_path = os.path.join(self.settings.CACHE_PATH, out_folder, out_file)

    def get_source_basename(self):
        if not self.source:
            return False
        return self.source['basename']

    def get_source_abspath(self):
        if not self.source:
            return False
        return self.source['abspath']

    def get_source_video_codecs(self):
        if not self.source:
            return False
        return self.source['video_codecs']

    def task_dump(self):
        # Generate a copy of this class as a dict
        task_dict = {
            'success':     self.success,
            'source':      self.source,
            'destination': self.destination,
            'statistics':  self.statistics,
            'errors':      self.errors,
            'ffmpeg_log':  self.ffmpeg_log
        }
        # Append the ffmpeg probe data
        if self.ffmpeg.file_in:
            task_dict['source']['file_probe'] = self.ffmpeg.file_in.get('file_probe', {})
        if self.ffmpeg.file_in:
            task_dict['destination']['file_probe'] = self.ffmpeg.file_out.get('file_probe', {})
        # Append file size data
        return task_dict

    def set_task_stats(self, statistics):
        if 'processed_by_worker' in statistics:
            self.statistics['processed_by_worker'] = statistics['processed_by_worker']
        if 'start_time' in statistics:
            self.statistics['start_time'] = statistics['start_time']
        if 'finish_time' in statistics:
            self.statistics['finish_time'] = statistics['finish_time']
        if 'video_encoder' in statistics:
            self.statistics['video_encoder'] = statistics['video_encoder']
        if 'audio_encoder' in statistics:
            self.statistics['audio_encoder'] = statistics['audio_encoder']
