#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.workers.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Aug 2021, (12:06 PM)

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
import queue
import shutil
import subprocess
import threading
import time

import psutil as psutil

from unmanic.libs import common, unlogger
from unmanic.libs.plugins import PluginsHandler


def default_progress_parser(line_text):
    return {
        'percent': ''
    }


class WorkerCommandError(Exception):
    def __init___(self, command):
        Exception.__init__(self, "Worker command returned non 0 status. Command: {}".format(command))
        self.command = command


class Worker(threading.Thread):
    idle = True
    paused = False
    current_task = None

    worker_subprocess = {}
    worker_log = None
    percent = None

    start_time = None
    finish_time = None

    worker_runners_info = {}

    def __init__(self, thread_id, name, pending_queue, complete_queue):
        super(Worker, self).__init__(name=name)
        self.thread_id = thread_id
        self.name = name
        self.pending_queue = pending_queue
        self.complete_queue = complete_queue

        # Create 'redundancy' flag. When this is set, the worker should die
        self.redundant_flag = threading.Event()
        self.redundant_flag.clear()

        # Create logger for this worker
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(self.name)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def run(self):
        self._log("Starting worker")
        while not self.redundant_flag.is_set():
            time.sleep(.2)  # Add delay for preventing loop maxing compute resources

            # If the Foreman has paused this worker, then dont do anything
            if self.paused:
                # If the worker is paused, wait for 5 seconds before continuing the loop
                time.sleep(5)
                # TODO: Pause subprocesses
                continue

            # Set the worker as Idle - This will announce to the Foreman that its ready for a task
            self.idle = True

            # Wait for task
            while not self.redundant_flag.is_set() and not self.pending_queue.empty():
                time.sleep(.2)  # Add delay for preventing loop maxing compute resources

                try:
                    # Pending task queue has an item available. Fetch it.
                    next_task = self.pending_queue.get_nowait()

                    # Configure worker for this task
                    self.__set_current_task(next_task)

                    # Process the set task task
                    self.__process_task_queue_item()
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception in processing job with {}:".format(self.name), message2=str(e),
                              level="exception")

        self._log("Stopping worker")

    def get_status(self):
        """
        Fetch the status of this worker.

        TODO: Fetch subprocess pid

        :return:
        """
        status = {
            'id':              str(self.thread_id),
            'name':            self.name,
            'idle':            self.idle,
            'paused':          self.paused,
            'start_time':      self.start_time,
            'current_file':    "",
            'worker_log_tail': [],
            'runners_info':    {},
            'subprocess':      {
                'pid':     self.ident,
                'percent': str(self.worker_subprocess.get('percent', 0)),
                'elapsed': str(self.worker_subprocess.get('elapsed', 0)),
            },
        }
        if self.current_task:
            # Fetch the current file
            try:
                status['current_file'] = self.current_task.get_source_basename()
            except Exception as e:
                self._log("Exception in fetching the current file of worker {}:".format(self.name), message2=str(e),
                          level="exception")

            # Append the worker log tail
            try:
                if self.worker_log and len(self.worker_log) > 20:
                    status['worker_log_tail'] = self.worker_log[-19:]
            except Exception as e:
                self._log("Exception in fetching log tail of worker: ", message2=str(e),
                          level="exception")

            # Append the runners info
            try:
                status['runners_info'] = self.worker_runners_info
            except Exception as e:
                self._log("Exception in runners info of worker {}:".format(self.name), message2=str(e),
                          level="exception")
        return status

    def __set_current_task(self, current_task):
        """Sets the given task to the worker class"""
        self.current_task = current_task
        self.worker_log = []

    def __unset_current_task(self):
        self.current_task = None
        self.worker_runners_info = {}
        self.worker_log = []

    def __process_task_queue_item(self):
        """
        Processes the set task.

        :return:
        """
        # Mark worker as not idle now that it is processing a task
        self.idle = False

        # Log the start of the job
        self._log("Picked up job - {}".format(self.current_task.get_source_abspath()))

        # Mark as being "in progress"
        self.current_task.set_status('in_progress')

        # Start current task stats
        self.__set_start_task_stats()

        # Process the file. Will return true if success, otherwise false
        success = self.__exec_worker_runners_on_set_task()
        # Mark the task as either success or not
        self.current_task.set_success(success)

        # Mark task completion statistics
        self.__set_finish_task_stats()

        # Log completion of job
        self._log("Finished job - {}".format(self.current_task.get_source_abspath()))

        # Place the task into the completed queue
        self.complete_queue.put(self.current_task)

        # Reset the current file info for the next task
        self.__unset_current_task()

    def __set_start_task_stats(self):
        """Sets the initial stats for the start of a task"""
        # Set the start time to now
        self.start_time = time.time()

        # Clear the finish time
        self.finish_time = None

        # Format our starting statistics data
        self.current_task.task.processed_by_worker = self.name
        self.current_task.task.start_time = self.start_time
        self.current_task.task.finish_time = self.finish_time

    def __set_finish_task_stats(self):
        """Sets the final stats for the end of a task"""
        # Set the finish time to now
        self.finish_time = time.time()

        # Set the finish time in the statistics data
        self.current_task.task.finish_time = self.finish_time

    def __exec_worker_runners_on_set_task(self):
        """
        Executes the configured plugin runners against the set task.

        :return:
        """

        # Init plugins
        plugin_handler = PluginsHandler()
        plugin_modules = plugin_handler.get_plugin_modules_by_type('worker.process_item')

        # Create dictionary of runners info for the frontend
        self.worker_runners_info = {}
        for plugin_module in plugin_modules:
            self.worker_runners_info[plugin_module.get('plugin_id')] = {
                'plugin_id':   plugin_module.get('plugin_id'),
                'status':      'pending',
                "name":        plugin_module.get('name'),
                "author":      plugin_module.get('author'),
                "version":     plugin_module.get('version'),
                "icon":        plugin_module.get('icon'),
                "description": plugin_module.get('description'),
            }

        # Set the absolute path to the original file
        original_abspath = self.current_task.get_source_abspath()

        # Process item in loop.
        # First process the item for for each plugin that configures it, then run the default Unmanic configuration
        task_cache_path = self.current_task.get_cache_path()
        # Set the current input file to the original file path
        file_in = original_abspath
        # Mark the overall success of all runners. This will be set to False if any of the runners fails.
        overall_success = True
        # Set the current file out to nothing.
        # This will be configured by each runner.
        # If no runners are configured, then nothing needs to be done.
        current_file_out = original_abspath
        # The number of runners that have been run
        runner_count = 0

        for plugin_module in plugin_modules:
            # Increment the runners count (first runner will be set as #1)
            runner_count += 1

            # Mark the status of the worker for the frontend
            self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'in_progress'
            self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False

            # Fetch file out details
            # This creates a temp file labeled "WORKING" that will be moved to the cache_path on completion
            tmp_file_out = os.path.splitext(task_cache_path)
            file_out = current_file_out = "{}-{}-{}{}".format(tmp_file_out[0], "WORKING", runner_count, tmp_file_out[1])

            # Create initial args for the runner functions
            initial_data = {
                "exec_command":            [],
                "command_progress_parser": default_progress_parser,
                "file_in":                 file_in,
                "file_out":                file_out,
                "original_file_path":      original_abspath,
                "repeat":                  False,
            }
            # Loop over runner. This way we can repeat the function with the same data if requested by the repeat flag
            runner_pass_count = 0
            while not self.redundant_flag.is_set():
                runner_pass_count += 1
                time.sleep(.2)  # Add delay for preventing loop maxing compute resources

                # Run plugin and fetch return data
                plugin_runner = plugin_module.get("runner")
                try:
                    data = initial_data.copy()
                    plugin_runner(data)

                    # Temp condition to enable the default stage
                    # TODO: Deprecate this once Unmanic Settings are removed
                    if plugin_module.get('plugin_id') == 'unmanic_default_stage':
                        data['exec_command'] = ['ffmpeg-default']
                except Exception as e:
                    self._log("Exception while carrying out plugin runner on worker process '{}'".format(
                        plugin_module.get('plugin_id')), message2=str(e), level="exception")
                    # Skip this plugin module's loop
                    self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'complete'
                    continue

                # Log the in and out files returned by the plugin runner for debugging
                self._log("Worker process '{}' (in)".format(plugin_module.get('plugin_id')), data.get("file_in"),
                          level='debug')
                self._log("Worker process '{}' (out)".format(plugin_module.get('plugin_id')), data.get("file_out"),
                          level='debug')

                # Only run the conversion process if "exec_command" is not empty
                if data.get("exec_command"):
                    self.worker_log += ["\n\nRUNNER: \n{} [Pass #{}]".format(plugin_module.get('name'), runner_pass_count)]

                    # Temp function to handle old FFmpeg conversions if the runner ID is 'unmanic_default_stage'
                    # TODO: Deprecate this once Unmanic Settings are removed
                    if plugin_module.get('plugin_id') == 'unmanic_default_stage':
                        success = self.__default_ffmpeg_runner(data)
                    else:
                        success = self.__exec_command_subprocess(data)

                    # Run command. Check if command exited successfully.
                    if success:
                        # If file conversion was successful
                        self._log("Successfully ran worker process '{}' on file '{}'".format(plugin_module.get('plugin_id'),
                                                                                             data.get("file_in")))
                        # Set the file in as the file out for the next loop
                        file_in = data.get("file_out")
                    else:
                        # If file conversion was successful
                        self._log(
                            "Error while running worker process '{}' on file '{}'".format(
                                plugin_module.get('plugin_id'),
                                original_abspath
                            ),
                            level="error")
                        self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False
                        overall_success = False
                else:
                    self._log(
                        "Worker process '{}' did not request to execute a command.".format(plugin_module.get('plugin_id')),
                        level='debug')

                if data.get("repeat"):
                    # Returned data contained the repeat flag, repeat it
                    continue
                break

            self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = True
            self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'complete'

        # Save the completed command log
        self.current_task.save_command_log(self.worker_log)

        # If all plugins that were executed completed successfully, then this was overall a successful task.
        # At this point we need to move the final out file to the original task cache path so the postprocessor can collect it.
        if overall_success:
            # If jobs carried out on this task were all successful, we will get here
            self._log("Successfully converted file '{}'".format(original_abspath))
            try:
                # Move file to original cache path
                self._log("Moving final cache file from '{}' to '{}'".format(current_file_out, task_cache_path))
                current_file_out = os.path.abspath(current_file_out)

                # There is a really odd intermittent bug with the shutil module that is causing it to
                #   sometimes report that the file does not exist.
                # This section adds a small pause and logs the error if that is the case.
                # I have not yet figured out a soltion as this is difficult to reproduce.
                if not os.path.exists(current_file_out):
                    self._log("Error - current_file_out path does not exist! '{}'".format(file_in), level="error")
                    time.sleep(1)

                # Use shutil module to move the file to the final task cache location
                shutil.move(current_file_out, task_cache_path)
            except Exception as e:
                self._log("Exception in final move operation of file {} to {}:".format(current_file_out, task_cache_path),
                          message2=str(e), level="exception")
                return False

            # Return True
            return True

        # If the overall result of the jobs carried out on this task were not successful, we will get here.
        # Log the failure and return False
        self._log("Failed to convert file '{}'".format(original_abspath), level='warning')
        return False

    def __exec_command_subprocess(self, data):
        """
        Executes a command as a shell subprocess.
        Uses the given parser to record progress data from the shell STDOUT.

        :param data:
        :return:
        """
        # Fetch command to execute.
        exec_command = data.get("exec_command", [])

        # Fetch the command progress parser function
        command_progress_parser = data.get("command_progress_parser", default_progress_parser)

        # Log the command for debugging
        self._log("Executing: {}".format(' '.join(exec_command)), level='debug')

        # Append start of command to worker subprocess stdout
        self.worker_log += [
            '\n\n',
            'COMMAND:\n',
            ' '.join(exec_command),
            '\n\n',
            'LOG:\n',
        ]

        # Create output path if not exists
        common.ensure_dir(data.get("file_out"))

        # Convert file
        success = False
        try:
            proc_start_time = time.time()
            # Execute command
            self.worker_subprocess['proc'] = subprocess.Popen(exec_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                              universal_newlines=True, errors='replace')
            # Record PID
            self.worker_subprocess['pid'] = self.worker_subprocess['proc'].pid
            # Fetch process using psutil for control (sending SIGSTOP on windows will not work)
            proc = psutil.Process(pid=self.worker_subprocess['pid'])

            # Poll process for new output until finished
            while not self.redundant_flag.is_set():
                line_text = self.worker_subprocess['proc'].stdout.readline()

                # Fetch command stdout and append it to the current task object (to be saved during post process)
                self.worker_log.append(line_text)

                # Check if the command has completed. If it has, exit the loop
                if line_text == '' and self.worker_subprocess['proc'].poll() is not None:
                    break

                # Parse the progress
                try:
                    progress_dict = command_progress_parser(line_text)
                    self.worker_subprocess['percent'] = progress_dict.get('percent')
                    self.worker_subprocess['elapsed'] = str(time.time() - proc_start_time)
                except Exception as e:
                    # Only need to show any sort of exception if we have debugging enabled.
                    # So we should log it as a debug rather than an exception.
                    self._log("Exception while parsing command progress", str(e), level='debug')

                # Stop the process if the worker is paused
                # Then resume it when the worker is resumed
                if self.paused:
                    proc.suspend()
                    while not self.redundant_flag.is_set():
                        time.sleep(1)
                        if not self.paused:
                            proc.resume()
                            # TODO: elapsed time is used for calculating etc. We should also suspend that somehow here.
                            break
                        continue

            # Get the final output and the exit status
            communicate = self.worker_subprocess['proc'].communicate()[0]
            if self.worker_subprocess['proc'].returncode == 0:
                return True
            else:
                self._log("Command run against '{}' exited with non-zero status. "
                          "Download command dump from history for more information.".format(data.get("file_in")),
                          message2=str(exec_command), level="error")
                return False

        except Exception as e:
            self._log("Error while executing the command {}.".format(data.get("file_in")), message2=str(e), level="error")

    def __default_ffmpeg_runner(self, data):
        """
        Temporary default runner for compatibility with Unmanic's built-in file conversion settings.
        This will be removed once plugins are carrying out all conversion tasks and the Unmanic settings have been refactored.

        :return:
        """
        from unmanic.libs import ffmpeg
        ffmpeg_settings = {
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

        file_in = data.get("file_in")
        file_out = data.get("file_out")

        # Setup FFmpeg handler
        ffmpeg_handle = ffmpeg.FFMPEGHandle(ffmpeg_settings)

        # Fetch initial file probe
        file_probe = ffmpeg_handle.file_probe(file_in)

        # Create args from
        ffmpeg_args = ffmpeg_handle.generate_ffmpeg_args(file_probe, file_in, file_out)

        # Create output path if not exists
        common.ensure_dir(file_out)

        # Append start of command to worker subprocess stdout
        self.worker_log += [
            '\n\n',
            'COMMAND:\n',
            'ffmpeg ' + ' '.join(ffmpeg_args),
            '\n\n',
            'LOG:\n',
        ]

        # Convert file
        success = False
        try:
            # Reset to defaults
            ffmpeg_handle.set_info_defaults()
            # Fetch source file info
            ffmpeg_handle.set_file_in(file_in)
            # Read video information for the input file
            file_probe = ffmpeg_handle.file_in['file_probe']
            if not file_probe:
                return False
            if ffmpeg_args:
                success = ffmpeg_handle.convert_file_and_fetch_progress(file_in, ffmpeg_args)

            self.worker_log += ffmpeg_handle.ffmpeg_cmd_stdout

        except ffmpeg.FFMPEGHandleConversionError as e:
            # Fetch ffmpeg stdout and append it to the current task object (to be saved during post process)
            self.worker_log += ffmpeg_handle.ffmpeg_cmd_stdout
            self._log("Error while executing the FFMPEG command {}. "
                      "Download FFMPEG command dump from history for more information.".format(file_in),
                      message2=str(e), level="error")

        return success
