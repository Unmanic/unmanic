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
import hashlib
import os
import shutil
import threading
import time

from unmanic.libs.fileinfo import FileInfo
from unmanic.libs import common, history, ffmpeg, unffmpeg
from unmanic.libs.plugins import PluginsHandler

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
        # Init plugins handler
        plugin_handler = PluginsHandler()

        # Read current task data
        # task_data = self.current_task.get_task_data()
        cache_path = self.current_task.get_cache_path()
        source_data = self.current_task.get_source_data()
        destination_data = self.current_task.get_destination_data()
        # Move file back to original folder and remove source
        file_move_processes_success = True
        # Create a list for filling with destination paths
        destination_files = []
        if self.current_task.task.success:
            # Run a postprocess file movement on the cache file for for each plugin that configures it

            # Ensure finaly cache path file is correct format
            self.current_task.task.success = self.validate_streams(self.current_task.task.cache_path)

            # Fetch all 'postprocessor.file_move' plugin modules
            plugin_modules = plugin_handler.get_plugin_modules_by_type('postprocessor.file_move')

            # Check if the source file needs to be remove by default (only if it does not match the destination file)
            remove_source_file = False
            if source_data['abspath'] != destination_data['abspath']:
                remove_source_file = True

            # Set initial data (some fields will be overwritten further down)
            initial_data = {
                "source_data":        None,
                'remove_source_file': remove_source_file,
                'copy_file':          None,
                "file_in":            None,
                "file_out":           None,
            }

            for plugin_module in plugin_modules:
                # Always set source_data to the original file's source_data
                initial_data["source_data"] = source_data
                # Always set copy_file to True
                initial_data["copy_file"] = True
                # Always set file in to cache path
                initial_data["file_in"] = cache_path
                # Always set file out to destination data absolute path
                initial_data["file_out"] = destination_data.get('abspath')

                # Run plugin and fetch return data
                plugin_runner = plugin_module.get("runner")
                try:
                    data = plugin_runner(initial_data)
                except Exception as e:
                    self._log("Exception while carrying out plugin runner on postprocessor file movement '{}'".format(
                        plugin_module.get('plugin_id')), message2=str(e), level="exception")
                    # Do not continue with this plugin module's loop
                    continue

                if data.get('copy_file'):
                    # Copy the file
                    self._log("Copying file {} --> {}".format(data.get('file_in'), data.get('file_out')))
                    try:
                        before_checksum = hashlib.md5(open(data.get('file_in'), 'rb').read()).hexdigest()
                        file_in = os.path.abspath(data.get('file_in'))
                        file_out = os.path.abspath((data.get('file_out')))
                        if not os.path.exists(file_in):
                            self._log("Error - file_in path does not exist! '{}'".format(file_in), level="error")
                            time.sleep(1)
                        shutil.copyfile(file_in, file_out)
                        after_checksum = hashlib.md5(open(data.get('file_out'), 'rb').read()).hexdigest()
                        # Compare the checksums on the copied file to ensure it is still correct
                        if before_checksum != after_checksum:
                            # Something went wrong during that file copy
                            self._log("Copy function failed during postprocessor file movement '{}' on file '{}'".format(
                                plugin_module.get('plugin_id'), cache_path), level='warning')
                            file_move_processes_success = False
                        else:
                            destination_files.append(data.get('file_out'))
                    except Exception as e:
                        self._log("Exception while copying file {} to {}:".format(data.get('file_in'), data.get('file_out')),
                                  message2=str(e), level="exception")
                        file_move_processes_success = False

            # Check if the remove source flag is still True after all plugins have run. If so, we will remove the source file
            if data.get('remove_source_file'):
                # Only carry out a source removal if the whole postprocess was successful
                if file_move_processes_success:
                    self._log("Removing source: {}".format(source_data['abspath']))
                    os.remove(source_data['abspath'])

                    # If we need to keep the filename history, do that here
                    if self.settings.get_keep_filename_history():
                        dirname = os.path.dirname(source_data['abspath'])
                        self.keep_filename_history(dirname, destination_data["basename"], source_data["basename"])
                else:
                    self._log(
                        "Keeping source file '{}'. Not all postprocessor file movement functions completed.".format(
                            source_data['abspath']), level="warning")

            if not file_move_processes_success:
                self._log(
                    "Error while running postprocessor file movement on file '{}'. Not all postprocessor file movement functions completed.".format(
                        cache_path), level="error")

        else:
            self._log("Encoded file failed post processing test '{}'".format(cache_path),
                      level='warning')

        # Fetch all 'postprocessor.task_result' plugin modules
        plugin_modules = plugin_handler.get_plugin_modules_by_type('postprocessor.task_result')

        for plugin_module in plugin_modules:
            data = {
                "source_data":                 source_data,
                'task_processing_success':     self.current_task.task.success,
                'file_move_processes_success': file_move_processes_success,
                'destination_files':           destination_files,

            }

            # Run plugin and fetch return data
            plugin_runner = plugin_module.get("runner")
            try:
                plugin_runner(data)
            except Exception as e:
                self._log("Exception while carrying out plugin runner on postprocessor task result '{}'".format(
                    plugin_module.get('plugin_id')), message2=str(e), level="exception")
                continue

        # Cleanup cache files
        task_cache_directory = os.path.dirname(cache_path)
        if os.path.exists(task_cache_directory) and "unmanic_file_conversion" in task_cache_directory:
            for f in os.listdir(task_cache_directory):
                cache_file_path = os.path.join(task_cache_directory, f)
                self._log("Removing task cache directory file '{}'".format(cache_file_path))
                # Remove the cache file
                os.remove(cache_file_path)
            # Remove the directory
            self._log("Removing task cache directory '{}'".format(task_cache_directory))
            os.rmdir(task_cache_directory)

    def validate_streams(self, abspath):
        # Read video information for the input file
        try:
            file_probe = self.ffmpeg.file_probe(abspath)
        except unffmpeg.exceptions.ffprobe.FFProbeError as e:
            self._log("Exception in method validate_streams", str(e), level='exception')
            return False

        # Default errors to true unless we find a stream that matches
        video_errors = True if self.settings.get_enable_video_encoding() else False
        audio_errors = False
        for stream in file_probe['streams']:
            if stream['codec_type'] == 'video':
                if self.settings.get_enable_video_encoding():
                    # Check if this file is the right codec
                    if stream['codec_name'] == self.settings.get_video_codec():
                        video_errors = False
                        continue
                    elif self.settings.get_debugging():
                        self._log(
                            "File is the not correct codec {} - {} :: {}".format(self.settings.get_video_codec(), abspath,
                                                                                 stream['codec_name']))
                    # TODO: Test duration is the same as src
                    # TODO: Add file checksum from before and after move
                else:
                    video_errors = None

        if not video_errors and not audio_errors:
            return True
        return False

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
