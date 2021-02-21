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
from unmanic.libs import common, history, ffmpeg, unffmpeg

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

    def __init__(self, data_queues, settings, task_queue):
        super(PostProcessor, self).__init__(name='PostProcessor')
        self.logger = data_queues["logging"].get_logger(self.name)
        self.settings = settings
        self.task_queue = task_queue
        self.abort_flag = threading.Event()
        self.current_task = None
        self.ffmpeg = None
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def setup_ffmpeg(self):
        """
        Configure ffmpeg object.

        :return:
        """
        settings = {
            'audio_codec':                          self.current_task.settings.audio_codec,
            'audio_codec_cloning':                  self.current_task.settings.audio_codec_cloning,
            'audio_stereo_stream_bitrate':          self.current_task.settings.audio_stereo_stream_bitrate,
            'audio_stream_encoder':                 self.current_task.settings.audio_stream_encoder,
            'cache_path':                           self.current_task.settings.cache_path,
            'debugging':                            self.current_task.settings.debugging,
            'enable_audio_encoding':                self.current_task.settings.enable_audio_encoding,
            'enable_audio_stream_stereo_cloning':   self.current_task.settings.enable_audio_stream_stereo_cloning,
            'enable_audio_stream_transcoding':      self.current_task.settings.enable_audio_stream_transcoding,
            'enable_video_encoding':                self.current_task.settings.enable_video_encoding,
            'out_container':                        self.current_task.settings.out_container,
            'remove_subtitle_streams':              self.current_task.settings.remove_subtitle_streams,
            'video_codec':                          self.current_task.settings.video_codec,
            'video_stream_encoder':                 self.current_task.settings.video_stream_encoder,
            'overwrite_additional_ffmpeg_options':  self.current_task.settings.overwrite_additional_ffmpeg_options,
            'additional_ffmpeg_options':            self.current_task.settings.additional_ffmpeg_options,
            'enable_hardware_accelerated_decoding': self.current_task.settings.enable_hardware_accelerated_decoding,
        }
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self._log("Starting PostProcessor Monitor loop...")
        while not self.abort_flag.is_set():
            time.sleep(1)

            while not self.abort_flag.is_set() and not self.task_queue.task_list_processed_is_empty():
                time.sleep(.2)
                self.current_task = self.task_queue.get_next_processed_tasks()
                if self.current_task:
                    try:
                        self._log("Post-processing task - {}".format(self.current_task.get_source_abspath()))
                    except Exception as e:
                        self._log("Exception in fetching task absolute path", message2=str(e), level="exception")
                    self.setup_ffmpeg()
                    # Post process the converted file (return it to original directory etc.)
                    self.post_process_file()
                    # Write source and destination data to historic log
                    self.write_history_log()
                    # Remove file from task queue
                    # self.current_task.set_status('complete')
                    self.current_task.delete()

        self._log("Leaving PostProcessor Monitor loop...")

    def post_process_file(self):
        # Check if the job was a success
        if not self.current_task.task.success:
            self._log("Task was marked as failed.", level='debug')
            self._log("Removing cached file", self.current_task.task.cache_path, level='debug')
            self.remove_current_task_cache_file()
            return
        # Ensure file is correct format
        self.current_task.task.success = self.validate_streams(self.current_task.task.cache_path)
        # Read current task data
        # task_data = self.current_task.get_task_data()
        cache_path = self.current_task.get_cache_path()
        source_data = self.current_task.get_source_data()
        destination_data = self.current_task.get_destination_data()
        # Move file back to original folder and remove source
        if self.current_task.task.success:
            # Move the file
            self._log("Moving file {} --> {}".format(cache_path, destination_data['abspath']))
            shutil.move(cache_path, destination_data['abspath'])

            # Run another validation on the moved file to ensure it is correct
            self.current_task.task.success = self.validate_streams(destination_data['abspath'])
            if self.current_task.task.success:
                # If successfully moved the cached re-encoded copy, remove source
                # TODO: Add env variable option to keep src
                if source_data['abspath'] != destination_data['abspath']:
                    self._log("Removing source: {}".format(source_data['abspath']))
                    if self.settings.KEEP_FILENAME_HISTORY:
                        dirname = os.path.dirname(source_data['abspath'])
                        self.keep_filename_history(dirname, destination_data["basename"], source_data["basename"])
                    os.remove(source_data['abspath'])
            else:
                self._log("Copy / Replace failed during post processing '{}'".format(cache_path),
                          level='warning')
                return
        else:
            self._log("Encoded file failed post processing test '{}'".format(cache_path),
                      level='warning')
            return

    def validate_streams(self, abspath):
        # Read video information for the input file
        try:
            file_probe = self.ffmpeg.file_probe(abspath)
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
                        continue
                    elif self.settings.DEBUGGING:
                        self._log("File is the not correct codec {} - {} :: {}".format(self.settings.VIDEO_CODEC, abspath,
                                                                                       stream['codec_name']))
                        # TODO: If settings are modified during a conversion, the file being converted should not fail.
                        #  Modify ffmpeg.py to have settings passed to it rather than reading directly from the config object
                        #  Test against the task's configured video codec
                    # TODO: Test duration is the same as src
                    # TODO: Add file checksum from before and after move

        return result

    def write_history_log(self):
        """
        Record task history

        :return:
        """
        self._log("Writing task history log.", level='debug')
        history_logging = history.History(self.settings)
        task_dump = self.current_task.task_dump()

        try:
            destination_data = self.current_task.get_destination_data()
            destination_file_probe = self.ffmpeg.file_probe(destination_data['abspath'])
            file_probe_format = destination_file_probe.get('format', {})

            destination_data.update(
                {
                    'bit_rate':         file_probe_format.get('bit_rate', ''),
                    'format_long_name': file_probe_format.get('format_long_name', ''),
                    'format_name':      file_probe_format.get('format_name', ''),
                    'size':             file_probe_format.get('size', ''),
                    'duration':         file_probe_format.get('duration', ''),
                    'streams':          destination_file_probe.get('streams', [])
                }
            )
            task_dump['file_probe_data']['destination'] = destination_data
        except unffmpeg.exceptions.ffprobe.FFProbeError as e:
            self._log("Exception in method write_history_log", str(e), level='exception')
        except Exception as e:
            self._log("Exception in method write_history_log", str(e), level='exception')

        history_logging.save_task_history(
            {
                'task_label':          task_dump.get('task_label', ''),
                'task_success':        task_dump.get('task_success', ''),
                'start_time':          task_dump.get('start_time', ''),
                'finish_time':         task_dump.get('finish_time', ''),
                'processed_by_worker': task_dump.get('processed_by_worker', ''),
                'task_dump':           task_dump,
            }
        )

    def keep_filename_history(self, basedir, newname, originalname):
        """
        Write filename history in file_info (Filebot pattern useful for download subtitles using original filename)

        :return:
        """
        fileinfo = FileInfo("{}/file_info".format(basedir))
        fileinfo.load()
        fileinfo.append(newname, originalname)
        fileinfo.save()

    def remove_current_task_cache_file(self):
        if os.path.exists(self.current_task.task.cache_path):
            os.remove(self.current_task.task.cache_path)
