#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.postprocessor.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Apr 2019, (7:33 PM)
 
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
import json
import os
import shutil
import threading
import time

from lib import common

"""

The post-processor handles all tasks carried out on completion of a workers ffmpeg task.
This may be on either success or failure of the task.

The post-processor runs as a single thread, processing completed jobs one at a time.
This prevents conflicting copy operations or deleting a file that is also being post processed.

"""


class PostProcessError(Exception):
    def __init___(self, expected_var, result_var):
        Exception.__init__(self, "Errors found during post process checks. Expected {}, but instead found {}".format(
            expected_var, result_var))
        self.expected_var = expected_var
        self.result_var = result_var


class PostProcessor(threading.Thread):
    """
    PostProcessor

    """

    def __init__(self, data_queues, settings, job_queue):
        super(PostProcessor, self).__init__(name='PostProcessor')
        self.logger = data_queues["logging"].get_logger(self.name)
        self.settings = settings
        self.job_queue = job_queue
        self.abort_flag = threading.Event()
        self.current_task = None
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def run(self):
        self._log("Starting PostProcessor Monitor loop...")
        while not self.abort_flag.is_set():
            time.sleep(1)

            while not self.abort_flag.is_set() and not self.job_queue.processed_is_empty():
                time.sleep(.2)
                self.current_task = self.job_queue.get_next_processed_item()
                if self.current_task:
                    self._log("Post-processing item - {}".format(self.current_task.get_source_abspath()))
                    self.post_process_file()
                    self.write_history_log()

        self._log("Leaving PostProcessor Monitor loop...")

    def post_process_file(self):
        # Ensure file is correct format
        self.current_task.success = self.validate_streams(self.current_task.cache_path)
        # Move file back to original folder and remove source
        if self.current_task.success:
            # Move the file
            self._log(
                "Moving file {} --> {}".format(self.current_task.cache_path, self.current_task.destination['abspath']))
            shutil.move(self.current_task.cache_path, self.current_task.destination['abspath'])

            # Set file out
            self.current_task.ffmpeg.set_file_out(self.current_task.destination['abspath'])

            # Run another validation on the moved file to ensure it is correct
            self.current_task.success = self.validate_streams(self.current_task.destination['abspath'])
            if self.current_task.success:
                # If successfully moved the cached re-encoded copy, remove source
                # TODO: Add env variable option to keep src
                if self.current_task.source['abspath'] != self.current_task.destination['abspath']:
                    self._log("Removing source: {}".format(self.current_task.source['abspath']))
                    os.remove(self.current_task.source['abspath'])
            else:
                self._log("Copy / Replace failed during post processing '{}'".format(self.current_task.cache_path),
                          level='warning')
                return False
        else:
            self._log("Encoded file failed post processing test '{}'".format(self.current_task.cache_path),
                      level='warning')
            return False

    def validate_streams(self, abspath):
        # Read video information for the input file
        file_probe = self.current_task.ffmpeg.file_probe(abspath)
        if not file_probe:
            return False

        result = False
        for stream in file_probe['streams']:
            if stream['codec_type'] == 'video':
                # Check if this file is the right codec
                if stream['codec_name'] == self.settings.VIDEO_CODEC:
                    result = True
                elif self.settings.DEBUGGING:
                    self._log("File is the not correct codec {} - {}".format(self.settings.VIDEO_CODEC, abspath))
                    raise PostProcessError(self.settings.VIDEO_CODEC, stream['codec_name'])
                # TODO: Test duration is the same as src
                # TODO: Add file checksum from before and after move
        return result

    def write_history_log(self):
        # Read the current history log from file
        historical_log = self.settings.read_history_log()

        # Set the completed timestamp
        time_completed = time.time()

        # Set the job id
        job_id = '{}-{}'.format(common.random_string(), time_completed)

        # Append the file data to the history log
        historical_log.append({
            'job_id': job_id,
            'description': self.current_task.source['basename'],
            'time_complete': time_completed,
            'abspath': self.current_task.source['abspath'],
            'success': self.current_task.success
        })

        # Create config path in not exists
        if not os.path.exists(self.settings.CONFIG_PATH):
            os.makedirs(self.settings.CONFIG_PATH)

        # Create completed job details path in not exists
        completed_job_details_dir = os.path.join(self.settings.CONFIG_PATH, 'completed_job_details')
        if not os.path.exists(completed_job_details_dir):
            os.makedirs(completed_job_details_dir)

        # Set path of history json file
        history_file = os.path.join(self.settings.CONFIG_PATH, 'history.json')
        # Set path of conversion details file
        job_details_file = os.path.join(completed_job_details_dir, '{}.json'.format(job_id))

        try:
            # Write job details file
            with open(job_details_file, 'w') as outfile:
                json.dump(self.current_task.task_dump(), outfile, sort_keys=True, indent=4)
            # Write history file
            with open(history_file, 'w') as outfile:
                json.dump(historical_log, outfile, sort_keys=True, indent=4)
        except Exception as e:
            self._log("Exception in writing history to file:", message2=str(e), level="exception")
