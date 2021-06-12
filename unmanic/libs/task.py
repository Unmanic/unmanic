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
from operator import attrgetter

from playhouse.shortcuts import model_to_dict, dict_to_model

from unmanic.libs import common, ffmpeg
from unmanic.libs.unffmpeg import containers
from unmanic.libs.unmodels import Settings
from unmanic.libs.unmodels.taskprobe import TaskProbe
from unmanic.libs.unmodels.taskprobestreams import TaskProbeStreams
from unmanic.libs.unmodels.tasks import IntegrityError, Tasks
from unmanic.libs.unmodels.tasksettings import TaskSettings


def prepare_file_destination_data(pathname, container_extension):
    basename = os.path.basename(pathname)
    dirname = os.path.dirname(os.path.abspath(pathname))
    # Fetch the file's name without the file extension (this is going to be reset)
    file_name_without_extension = os.path.splitext(basename)[0]


    # Set destination dict
    basename = "{}.{}".format(file_name_without_extension, container_extension)
    abspath = os.path.join(dirname, basename)
    file_data = {
        'basename': basename,
        'abspath':  abspath
    }

    return file_data

def get_container_by_extension(pathname):
    split_file_name = os.path.splitext(os.path.basename(pathname))
    container_extension = split_file_name[1].lstrip('.')

    supported_containers = containers.get_all_containers()

    for key in supported_containers:
        extension = supported_containers[key].get('extension')
        if extension == container_extension:
            return key


class Task(object):
    """
    Task

    Contains the stage and all data pertaining to a transcode task

    """

    def __init__(self, logger):
        self.name = 'Task'
        self.task = None
        self.task_dict = None
        self.settings = None
        # TODO: Rename to probe
        self.source = None
        self.logger = logger
        self.destination = None
        self.statistics = {}
        self.errors = []

        # Reset all ffmpeg info
        # TODO: Remove ffmpeg
        # self.ffmpeg.set_info_defaults()

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
            # Remove the ID from the settings
            #   or else it will set the id of the newly created settings entry and cause an error
            if attribute_lower == 'id':
                continue
            if hasattr(TaskSettings, attribute_lower):
                task_settings_dict[attribute_lower] = settings.__dict__[attribute]
                continue

        # IF Unmanic is configured to keep the original container, attempt to get the container type by the files extension...
        if task_settings_dict.get('keep_original_container'):
            out_container = get_container_by_extension(self.task.abspath)
            # IF a supported container was matched to the extension, set the out container to that
            if out_container:
                task_settings_dict['out_container'] = out_container

        self.settings = TaskSettings.create(**task_settings_dict)

    def set_cache_path(self):
        if not self.task:
            raise Exception('Unable to set cache path. Task has not been set!')
        # Fetch the file's name without the file extension (this is going to be reset)
        split_file_name = os.path.splitext(self.source.basename)
        file_name_without_extension = split_file_name[0]

        # Get container extension
        container = containers.grab_module(self.settings.out_container)
        container_extension = container.container_extension()

        # Parse an output cache path
        out_folder = "unmanic_file_conversion-{}".format(time.time())
        out_file = "{}-{}.{}".format(file_name_without_extension, time.time(), container_extension)
        cache_directory = os.path.join(self.settings.cache_path, out_folder)
        cache_path = os.path.join(cache_directory, out_file)
        if self.task:
            self.task.cache_path = cache_path

    def get_task_data(self):
        if not self.task:
            raise Exception('Unable to fetch task dictionary. Task has not been set!')
        self.task_dict = model_to_dict(self.task, backrefs=True)
        return self.task_dict

    def get_cache_path(self):
        if not self.task:
            raise Exception('Unable to fetch cache path. Task has not been set!')
        if not self.task.cache_path:
            raise Exception('Unable to fetch cache path. Task cache path has not been set!')
        return self.task.cache_path

    def get_destination_data(self):
        if not self.task:
            raise Exception('Unable to fetch destination data. Task has not been set!')
        if not self.settings:
            raise Exception('Unable to fetch destination data. Task settings has not been set!')

        # Get container extension
        container = containers.grab_module(self.settings.out_container)
        container_extension = container.container_extension()

        return prepare_file_destination_data(self.task.abspath, container_extension)

    def get_source_data(self):
        # TODO: Rename to probe
        if not self.source:
            raise Exception('Unable to fetch source dictionary. Task source has not been set!')
        task_data = self.get_task_data()
        probe_data = task_data.get('probe', [])
        if probe_data:
            return probe_data[0]
        return {}

    def get_source_basename(self):
        if not self.source:
            raise Exception('Unable to fetch file basename. Task source has not been set!')
        return self.source.basename

    def get_source_abspath(self):
        if not self.source:
            raise Exception('Unable to fetch file absolute path. Task source has not been set!')
        return self.source.abspath

    def task_dump(self):
        # Generate a copy of this class as a dict
        task_dict = {
            'task_label':          self.source.basename,
            'task_success':        self.task.success,
            'start_time':          self.task.start_time,
            'finish_time':         self.task.finish_time,
            'processed_by_worker': self.task.processed_by_worker,
            'source':              self.source,
            'destination':         self.destination,
            'statistics':          self.statistics,
            'errors':              self.errors,
            'ffmpeg_log':          self.task.ffmpeg_log,
            'file_probe_data':     {
                'source': self.get_source_data()
            }
        }
        return task_dict

    def read_task_settings_from_db(self):
        """
        Read the task settings from the database

        Note:
            Even though there are faster ways to fetch the data from the DB
            There is no point making this complicated.
            Multiple selects will not take long in this application

        :return:
        """
        if not self.task:
            raise Exception('Unable to set task settings. Task has not been set!')
        # Select the settings for this task
        self.settings = self.task.settings.limit(1).get()

    def read_task_source_from_db(self):
        """
        Read the task source data from the database

        :return:
        """
        if not self.task:
            raise Exception('Unable to set task source data. Task has not been set!')
        # Fetch source data
        self.source = self.task.probe.limit(1).get()

    def read_and_set_task_by_absolute_path(self, abspath):
        """
        Sets the task by it's absolute path.
        If the task already exists in the list, then return that task.
        If the task does not yet exist in the list, create it first.

        :param abspath:
        :return:
        """
        # Get task matching the abspath
        self.task = Tasks.get(abspath=abspath)
        self.read_task_settings_from_db()
        self.read_task_source_from_db()

    def create_task_by_absolute_path(self, abspath, settings, source_data):
        """
        Creates the task by it's absolute path.
        If the task already exists in the list, then this will throw an exception and return false

        Calls to read_and_set_task_by_absolute_path() to read back all data out of the database.

        :param source_data:
        :param settings:
        :param abspath:
        :return:
        """
        try:
            self.task = Tasks.create(abspath=abspath, status='creating')
            self.save_task()
            self._log("Created new task with ID: {} for {}".format(self.task, abspath), level="debug")

            # Save the current settings against this task
            self.create_task_settings_entry(settings, self.task)

            # Fetch the current file data and apply it to the task
            self.create_task_probe_entry(source_data, self.task)
            self._log("Set the source data", level="debug")

            # Read application settings and apply it to the task
            # Destination data is generated based on the settings saved against this task
            #   (not necessarily the current settings)
            destination_data = self.get_destination_data()
            self.set_destination_data(destination_data)
            self._log("Set the destination data", level="debug")

            # Set the cache path to use during the transcoding
            self.set_cache_path()

            # Set the default priority to the ID of the task
            self.task.priority = self.task.id

            # Now set the status to pending. Only then will it be picked up by a worker.
            # This will also save the task.
            self.set_status('pending')

            # Read back the task from the database (ensures that our data has been recorded correctly)
            self.read_and_set_task_by_absolute_path(abspath)
            self._log("Task read from database", level="debug")
            return True
        except IntegrityError as e:
            self._log("Cancel creating new task for {} - {}".format(abspath, e), level="info")
            return False

    def set_status(self, status):
        """
        Sets the task status to either 'pending', 'in_progress' or 'processed'

        :param status:
        :return:
        """
        if status not in ['pending', 'in_progress', 'processed', 'complete']:
            raise Exception('Unable to set status to "{}". Status must be either "pending", "in_progress", or "processed".')
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        self.task.status = status
        self.save()

    def set_success(self, success):
        """
        Sets the task success flag to either 'true' or 'false'

        :param success:
        :return:
        """
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        if success:
            self.task.success = True
        else:
            self.task.success = False
        self.save()

    def save_ffmpeg_log(self, ffmpeg_log):
        """
        Sets the task ffmpeg_log

        :param ffmpeg_log:
        :return:
        """
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        self.task.ffmpeg_log += ''.join(ffmpeg_log)
        self.save()

    def save_task(self):
        if not self.task:
            raise Exception('Unable to save task. Task has not been set!')
        self.task.save()

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
        self.save_task()
        self.settings.save()
        self.source.save()
        for stream in self.source.streams:
            stream.save()

    def delete(self):
        if not self.task:
            raise Exception('Unable to save Task. Task has not been set!')
        self.task.delete_instance()

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

    def get_total_task_list_count(self):
        task_query = Tasks.select().order_by(Tasks.id.desc())
        return task_query.count()

    def get_task_list_filtered_and_sorted(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                                   status=None):
        try:
            query = (Tasks.select())

            if id_list:
                query = query.where(Tasks.id.in_(id_list))

            if search_value:
                query = query.where(Tasks.abspath.contains(search_value))

            if status:
                query = query.where(Tasks.status.in_([status]))

            # Get order by
            order_by = None
            if order:
                if order.get("dir") == "asc":
                    order_by = attrgetter(order.get("column"))(Tasks).asc()
                else:
                    order_by = attrgetter(order.get("column"))(Tasks).desc()

            if order_by and length:
                query = query.order_by(order_by).limit(length).offset(start)

        except Tasks.DoesNotExist:
            # No task entries exist yet
            self._log("No tasks exist yet.", level="warning")
            query = []

        return query.dicts()

    def delete_tasks_recursively(self, id_list):
        """
        Deletes a given list of tasks based on their IDs

        :param id_list:
        :return:
        """
        # Prevent running if no list of IDs was given
        if not id_list:
            return False

        try:
            query = (Tasks.select())

            if id_list:
                query = query.where(Tasks.id.in_(id_list))

            for task_id in query:
                try:
                    task_id.delete_instance(recursive=True)
                except Exception as e:
                    # Catch delete exceptions
                    self._log("An error occurred while deleting task ID: {}.".format(task_id), str(e), level="exception")
                    return False

            return True

        except Tasks.DoesNotExist:
            # No task entries exist yet
            self._log("No tasks currently exist.", level="warning")

    def reorder_tasks(self, id_list, direction):
        # Get the task with the highest ID
        order = {
            "column": 'priority',
            "dir":    'desc',
        }
        pending_task_results = self.get_task_list_filtered_and_sorted(order=order, start=0, length=1,
                                                                              search_value=None, id_list=None, status=None)
        for pending_task_result in pending_task_results:
            task_top_priority = pending_task_result.get('priority')
            break

        # Add 500 to that number to offset it above all others.
        new_priority_offset = (int(task_top_priority) + 500)

        # Update the list of tasks by ID from the database adding the priority offset to their current priority
        # If the direction is to send it to the bottom, then set the priority as 0
        query = Tasks.update(priority=Tasks.priority + new_priority_offset if (direction == "top") else 0).where(Tasks.id.in_(id_list))
        return query.execute()
