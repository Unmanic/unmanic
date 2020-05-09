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
import copy
import json
import os
import time

from unmanic.libs import common, ffmpeg
from unmanic.libs.unffmpeg import containers
from unmanic.libs.unmodels import Settings
from unmanic.libs.unmodels.taskprobe import TaskProbe
from unmanic.libs.unmodels.taskprobestreams import TaskProbeStreams
from unmanic.libs.unmodels.tasks import IntegrityError, Tasks
from unmanic.libs.unmodels.tasksettings import TaskSettings


def prepare_file_destination_data(pathname, settings):
    basename = os.path.basename(pathname)
    dirname = os.path.dirname(os.path.abspath(pathname))
    # Fetch the file's name without the file extension (this is going to be reset)
    file_name_without_extension = os.path.splitext(basename)[0]

    # Get container extension
    container = containers.grab_module(settings.out_container)
    container_extension = container.container_extension()

    # Set destination dict
    basename = "{}.{}".format(file_name_without_extension, container_extension)
    abspath = os.path.join(dirname, basename)
    file_data = {
        'basename': basename,
        'abspath':  abspath
    }

    return file_data


class Task(object):
    """
    Task

    Contains the stage and all data pertaining to a transcode task

    """

    def __init__(self, settings, data_queues):
        # TODO: Remove settings (should not be required)
        # TODO: Remove data_queues and replace with logging
        self.name = 'Task'
        self.task = None
        self.settings = None
        self.source = None
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings)
        self.logger = data_queues["logging"].get_logger(self.name)
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

    def set_source_data(self, source_data):
        # Set source data dict
        self.source = source_data

    def set_destination_data(self, destination_data):
        # Set destination data dict
        self.destination = destination_data

    def create_task_settings_entry(self, settings, task):
        """
        Create an entry of the current settings data

        :param settings:
        :param task:
        :return:
        """
        if not settings:
            self._log('Task dump missing settings data', json.dumps(settings), level="debug")
            raise Exception('Function param missing settings data')

        # Loop over settings object attributes. If the attribute is part of the TaskSettings object,
        #   add it to the task_settings dictionary to be used as create args below
        task_settings_dict = {
            'task_id': task
        }
        for attribute in settings.__dict__:
            # Ensure the settings attribute is in the TaskSettings object also
            attribute_lower = attribute.lower()
            if hasattr(TaskSettings, attribute_lower):
                task_settings_dict[attribute_lower] = settings.__dict__[attribute]
                continue
        self.settings = TaskSettings.create(**task_settings_dict)

    def set_cache_path(self):
        # Fetch the file's name without the file extension (this is going to be reset)
        file_name_without_extension = os.path.splitext(self.source.basename)[0]

        # Get container extension
        container = containers.grab_module(self.settings.out_container)
        container_extension = container.container_extension()

        # Parse an output cache path
        out_folder = "unmanic_file_conversion-{}".format(time.time())
        out_file = "{}-{}.{}".format(file_name_without_extension, time.time(), container_extension)
        self.cache_path = os.path.join(self.settings.cache_path, out_folder, out_file)
        # TODO: Remove the cache_path variable and only use self.task.cache_path
        #   if not self.task:
        #       raise Exception('Unable to set cache_path. Task has not been set!')
        if self.task:
            self.task.cache_path = self.cache_path

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

    def set_task_by_absolute_path(self, abspath):
        """
        Sets the task by it's absolute path.
        If the task already exists in the list, then return that task.
        If the task does not yet exist in the list, create it first.

        :param abspath:
        :return:
        """
        # Get task matching the abspath
        self.task = Tasks.get(abspath=abspath)
        # No point making this complicated. multiple selects will not take long in this application
        self.settings = self.task.settings.limit(1).get()
        # Fetch source data
        self.source = self.task.probe.limit(1).get()

        # for stream in self.source.streams:
        #     print(stream.codec_type)

    def create_task_by_absolute_path(self, abspath, settings, source_data):
        """
        Creates the task by it's absolute path.
        If the task already exists in the list, then this will throw an exception and return false

        Calls to set_task_by_absolute_path() to read back all data out of the database.

        :param source_data:
        :param settings:
        :param abspath:
        :return:
        """
        try:
            self.task = Tasks.create(abspath=abspath, status='pending')
            self.create_task_settings_entry(settings, self.task)
            self._log("Created new task with ID: {} for {}".format(self.task, abspath), level="debug")

            # Fetch the current file data and apply it to the task
            self.create_task_probe_entry(source_data, self.task)
            self._log("Set the source data", level="debug")

            # Read application settings and apply it to the task
            # Destination data is generated based on the settings saved against this task
            #   (not necessarily the current settings)
            destination_data = prepare_file_destination_data(self.task.abspath, self.settings)
            self.set_destination_data(destination_data)
            self._log("Set the destination data", level="debug")

            # Set the cache path to use during the transcoding
            self.set_cache_path()
            # Save the task in order to save that cache path
            self.task.save()

            # Read back the task from the database (ensures that our data has been recorded correctly)
            self.set_task_by_absolute_path(abspath)
            self._log("Task read from database", level="debug")
            return True
        except IntegrityError as e:
            self._log("Cancel creating new task for {} - {}".format(abspath, e), level="info")
            return False

    def set_status(self, status):
        if not status in ['pending', 'in_progress', 'processed']:
            raise Exception('Unable to set status to "{}". Status must be either "pending", "in_progress", or "processed".')
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        self.task.status = status

    def save(self):
        """
        Save task model object

        :return:
        """
        if not self.task:
            raise Exception('Unable to save Task. Task has not been set!')
        if not self.settings:
            raise Exception('Unable to save Task settings. Task settings has not been set!')
        if not self.source:
            raise Exception('Unable to save Task source. Task source has not been set!')
        self.task.save()
        self.settings.save()
        self.source.save()
        for stream in self.source.streams:
            stream.save()

    def create_task_probe_entry(self, source_data, task):
        """
        Create an entry of the data from the source ffprobe
        Create an entry for each stream in the file probe with create_task_probe_streams_entries()

        Required source_data params:
            - abspath
            - basename
            - bit_rate
            - format_long_name
            - format_name
            - size

        Other file_probe params:
            - duration

        :param task:
        :param source_data:
        :return:
        """
        if not source_data:
            self._log('Task dump missing source data', json.dumps(source_data), level="debug")
            raise Exception('Function param missing source data')

        # Get the file probe's "format" data
        file_probe_format = source_data.get('format', None)

        self.source = TaskProbe.create(
            task_id=task,
            abspath=source_data['abspath'],
            basename=source_data['basename'],
            bit_rate=file_probe_format.get('bit_rate', ''),
            format_long_name=file_probe_format.get('format_long_name', ''),
            format_name=file_probe_format.get('format_name', ''),
            size=file_probe_format.get('size', ''),
            duration=file_probe_format.get('duration', '')
        )
        self.create_task_probe_streams_entries(self.source, source_data)

    def create_task_probe_streams_entries(self, task_probe, source_data):
        """
        Create an entry for each stream in the file's ffprobe

        Required file_probe params:
            - codec_type

        Other file_probe params:
            - codec_long_name
            - avg_frame_rate
            - bit_rate
            - coded_height
            - coded_width
            - height
            - width
            - duration
            - channels
            - channel_layout

        :param task_probe:
        :param source_data:
        :return:
        """
        # Loop over streams and add them
        for stream in source_data.get('streams', []):

            if not stream.get('codec_type', None):
                self._log('Stream data missing codec_type', json.dumps(stream), level="debug")
                raise Exception('Stream data missing required "codec_type" data')

            TaskProbeStreams.create(
                taskprobe_id=task_probe,
                codec_type=stream.get('codec_type', None),
                codec_long_name=stream.get('codec_long_name', ''),
                avg_frame_rate=stream.get('avg_frame_rate', ''),
                bit_rate=stream.get('bit_rate', ''),
                coded_height=stream.get('coded_height', ''),
                coded_width=stream.get('coded_width', ''),
                height=stream.get('height', ''),
                width=stream.get('width', ''),
                duration=stream.get('duration', ''),
                channels=stream.get('channels', ''),
                channel_layout=stream.get('channel_layout', '')
            )
