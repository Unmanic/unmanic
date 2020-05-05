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

import os
import shutil
import threading
import time

from unmanic.libs.fileinfo import FileInfo
from unmanic.libs import common, history, unffmpeg

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

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self._log("Starting PostProcessor Monitor loop...")
        while not self.abort_flag.is_set():
            time.sleep(1)

            while not self.abort_flag.is_set() and not self.job_queue.processed_is_empty():
                time.sleep(.2)
                self.current_task = self.job_queue.get_next_processed_item()
                if self.current_task:
                    self._log("Post-processing task - {}".format(self.current_task.get_source_abspath()))
                    self.post_process_file()
                    self.write_history_log()

        self._log("Leaving PostProcessor Monitor loop...")

    def post_process_file(self):
        # Check if the job was a success
        if not self.current_task.success:
            self._log("Task was marked as failed.", level='debug')
            self._log("Removing cached file", self.current_task.cache_path, level='debug')
            self.remove_current_task_cache_file()
            return False
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
                    if self.settings.KEEP_FILENAME_HISTORY:
                        self.keep_filename_history(self.current_task.source["dirname"],
                                                   self.current_task.destination["basename"],
                                                   self.current_task.source["basename"])
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
        try:
            file_probe = self.current_task.ffmpeg.file_probe(abspath)
        except unffmpeg.exceptions.ffprobe.FFProbeError as e:
            self._log("Exception in method process_file", str(e), level='exception')
            return False

        result = False
        for stream in file_probe['streams']:
            if stream['codec_type'] == 'video':
                if self.settings.ENABLE_VIDEO_ENCODING:
                    # Check if this file is the right codec
                    if stream['codec_name'] == self.settings.VIDEO_CODEC:
                        result = True
                    elif self.settings.DEBUGGING:
                        self._log("File is the not correct codec {} - {}".format(self.settings.VIDEO_CODEC, abspath))
                        raise PostProcessError(self.settings.VIDEO_CODEC, stream['codec_name'])
                    # TODO: Test duration is the same as src
                    # TODO: Add file checksum from before and after move
                else:
                    result = True
        return result

    def write_history_log(self):
        """
        Record task history

        :return:
        """
        self._log("Writing task history log.", level='debug')
        history_logging = history.History(self.settings)
        task_dump = self.current_task.task_dump()
        history_logging.save_task_history(
            {
                'task_label':          self.current_task.source['basename'],
                'task_success':        self.current_task.success,
                'start_time':          task_dump['statistics']['start_time'],
                'finish_time':         task_dump['statistics']['finish_time'],
                'processed_by_worker': task_dump['statistics']['processed_by_worker'],
                'task_dump':           task_dump,
            }
        )

    def keep_filename_history(self, basedir, newname, originalname):
        """
        Write filename history in file_info (Filebot pattern usefull for download subtitles using original filename)

        :return:
        """
        fileinfo = FileInfo("{}/file_info".format(basedir))
        fileinfo.load()
        fileinfo.append(newname, originalname)
        fileinfo.save()

    def remove_current_task_cache_file(self):
        if os.path.exists(self.current_task.cache_path):
            os.remove(self.current_task.cache_path)
