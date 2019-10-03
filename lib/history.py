#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Jun 2019, (10:42 AM)
 
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
import time

from lib import common, unlogger, unmodels

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class History(object):
    """
    History

    Record statistical data for historical jobs
    """

    def __init__(self, settings=None):
        self.name = 'History'
        self.settings = settings

    def _log(self, message, message2='', level="info"):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(self.name)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.name))

    def read_history_log(self):
        """
        Note: Depreciated
        TODO: Remove this function

        :return:
        """
        self._log("read_history_log function is depreciated", level="warning")
        self._log("Reading history from file:", level="debug")
        data = []
        if not os.path.exists(self.settings.CONFIG_PATH):
            os.makedirs(self.settings.CONFIG_PATH)
        history_file = os.path.join(self.settings.CONFIG_PATH, 'history.json')
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

    def read_completed_job_data(self, job_id):
        """
        Note: Depreciated
        TODO: Remove this function

        :return:
        """
        self._log("read_completed_job_data function is depreciated", level="warning")
        self._log("Reading completed job data from file:", level="debug")
        data = []
        # Create completed job details path in not exists
        completed_job_details_dir = os.path.join(self.settings.CONFIG_PATH, 'completed_job_details')
        if not os.path.exists(completed_job_details_dir):
            os.makedirs(completed_job_details_dir)
        # Set path of conversion details file
        job_details_file = os.path.join(completed_job_details_dir, '{}.json'.format(job_id))
        if os.path.exists(job_details_file):
            try:
                with open(job_details_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                self._log("ValueError in reading completed job data from file:", level="exception")
            except Exception as e:
                self._log("Exception in reading completed job data from file:", message2=str(e), level="exception")
        return data

    def save_task_history(self, task_data):
        """
        Record a task's data and state to the database.

        :param task_data:
        :return:
        """
        try:
            with unmodels.db.atomic():

                # Create the new historical task entry
                new_historic_task = self.create_historic_task_entry(task_data)

                # TODO: Create a snapshot of the current configuration of the application into HistoricTaskSettings

                # Ensure a dump of the task was passed through with the task data param
                # This dump is a snapshot of all information pertaining to the task
                task_dump = task_data.get('task_dump', {})
                if not task_dump:
                    self._log('Passed param dict', json.dumps(task_data), level="debug")
                    raise Exception('Function param missing task data dump')

                # Create an entry of the data from the source ffprobe
                self.create_historic_task_probe_entry('source', new_historic_task, task_dump)

                # Create an entry of the data from the destination ffprobe
                self.create_historic_task_probe_entry('destination', new_historic_task, task_dump)

        except Exception as error:
            self._log("Failed to save historic task entry to database.", error, level="error")

    def create_historic_task_entry(self, task_data):
        """
        Create a historic task entry

        Required task_data params:
            - task_label
            - task_success
            - start_time
            - finish_time
            - processed_by_worker

        :param task_data:
        :return:
        """
        historic_task = unmodels.HistoricTasks()

        if not task_data:
            self._log('Task data param empty', json.dumps(task_data), level="debug")
            raise Exception('Task data param empty. This should not happen - Something has gone really wrong.')

        new_historic_task = historic_task.create(task_label=task_data['task_label'],
                                                 task_success=task_data['task_success'],
                                                 start_time=task_data['start_time'],
                                                 finish_time=task_data['finish_time'],
                                                 processed_by_worker=task_data['processed_by_worker'])
        return new_historic_task

    def create_historic_task_probe_entry(self, probe_type, historic_task, task_dump):
        """
        Create an entry of the data from the source or destination ffprobe
        Create an entry for each stream in the file probe with create_historic_task_probe_streams_entries()

        Required task_dump params:
            - type
            - abspath
            - basename
            - bit_rate
            - format_long_name
            - format_name
            - size

        :param probe_type:
        :param historic_task:
        :param task_dump:
        :return:
        """
        task_probe = unmodels.HistoricTaskProbe()

        probe_data = task_dump.get(probe_type, None)

        if not probe_data:
            self._log('Task dump dict missing {} data'.function(probe_type), json.dumps(probe_data), level="debug")
            raise Exception('Function param missing {} data'.function(probe_type))

        file_probe = probe_data.get('file_probe', None)
        file_probe_format = file_probe.get('format', None)

        new_historic_task_probe = task_probe.create(historictask_id=historic_task,
                                                    type=probe_type,
                                                    abspath=task_dump['source']['abspath'],
                                                    basename=task_dump['source']['basename'],
                                                    bit_rate=file_probe_format.get('bit_rate', ''),
                                                    format_long_name=file_probe_format.get('format_long_name', ''),
                                                    format_name=file_probe_format.get('format_name', ''),
                                                    size=file_probe_format.get('size', ''))

        self.create_historic_task_probe_streams_entries(probe_type, new_historic_task_probe, file_probe)

        return new_historic_task_probe

    def create_historic_task_probe_streams_entries(self, probe_type, historic_task_probe, file_probe):
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

        :param probe_type:
        :param historic_task_probe:
        :param file_probe:
        :return:
        """
        task_probe_streams = unmodels.HistoricTaskProbeStreams()

        # Loop over streams and add them
        for stream in file_probe.get('streams', []):

            if not stream.get('codec_type', None):
                self._log('Stream data for {} missing codec_type'.format(probe_type), json.dumps(stream), level="debug")
                raise Exception('Stream data for {} missing required "codec_type" data'.format(probe_type))

            task_probe_streams.create(historictaskprobe_id=historic_task_probe,
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
                                      channel_layout=stream.get('channel_layout', ''))
