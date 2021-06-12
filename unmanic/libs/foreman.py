#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.foreman.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     02 Jan 2019, (7:21 AM)

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
import queue
import time
import sys

from unmanic.libs.plugins import PluginsHandler

try:
    from unmanic.libs import common, history, ffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import common, history


# TODO: Move this WorkerThread class to it's own workers.py file
class WorkerThread(threading.Thread):
    def __init__(self, thread_id, name, settings, data_queues, task_queue, complete_queue):
        super(WorkerThread, self).__init__(name=name)
        self.thread_id = thread_id
        self.settings = settings
        self.data_queues = data_queues
        self.progress_reports = data_queues['progress_reports']
        self.task_queue = task_queue
        self.complete_queue = complete_queue
        self.idle = True
        self.current_task = None
        self.redundant_flag = threading.Event()
        self.redundant_flag.clear()
        self.logger = data_queues["logging"].get_logger(self.name)
        self.start_time = None
        self.finish_time = None
        # Worker handles connection to ffmpeg
        self.ffmpeg = None
        # Record the runners info including all plugins
        self.worker_runners_info = []

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def get_status(self):
        status = {
            'id':                    str(self.thread_id),
            'name':                  self.name,
            'idle':                  self.idle,
            'pid':                   self.ident,
            'progress':              self.get_job_progress(),
            'start_time':            self.start_time,
            'current_file':          "",
            'ffmpeg_log_tail':       [],
            'runners_info':          [],
        }
        if self.current_task:
            # Fetch the current file
            try:
                status['current_file'] = self.current_task.get_source_basename()
            except Exception as e:
                self._log("Exception in fetching the current file of worker {}:".format(self.name), message2=str(e),
                          level="exception")
            # Append the ffmpeg log tail
            try:
                if self.ffmpeg:
                    if self.ffmpeg.ffmpeg_cmd_stdout:
                        status['ffmpeg_log_tail'] = self.ffmpeg.ffmpeg_cmd_stdout[-19:]
            except Exception as e:
                self._log("Exception in fetching ffmpeg log tail of worker {}:".format(self.name), message2=str(e),
                          level="exception")
            # Append the runners info
            try:
                status['runners_info'] = self.worker_runners_info
            except Exception as e:
                self._log("Exception in runners info of worker {}:".format(self.name), message2=str(e),
                          level="exception")
        return status

    def get_job_progress(self):
        progress = {}
        if self.current_task and self.ffmpeg:
            progress['duration'] = str(self.ffmpeg.duration)
            progress['src_fps'] = str(self.ffmpeg.src_fps)
            progress['elapsed'] = str(self.ffmpeg.elapsed)
            progress['time'] = str(self.ffmpeg.time)
            progress['percent'] = str(self.ffmpeg.percent)
            progress['frame'] = str(self.ffmpeg.frame)
            progress['fps'] = str(self.ffmpeg.fps)
            progress['speed'] = str(self.ffmpeg.speed)
            progress['bitrate'] = str(self.ffmpeg.bitrate)
            progress['file_size'] = str(self.ffmpeg.file_size)
        return progress

    def set_current_task(self, current_task):
        self.current_task = current_task

    def unset_current_task(self):
        self.current_task = None
        self.ffmpeg = None
        self.worker_runners_info = {}

    def start_task_stats(self):
        self.start_time = time.time()
        self.finish_time = None
        # Format our starting statistics data
        self.current_task.task.processed_by_worker = self.name
        self.current_task.task.start_time = self.start_time
        self.current_task.task.finish_time = self.finish_time

    def finish_task_stats(self):
        self.finish_time = time.time()
        # Set the finish time in the statistics data
        self.current_task.task.finish_time = self.finish_time

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

    def process_item(self):
        # Reset the ffmpeg class when a new item is received
        self.setup_ffmpeg()

        abspath = self.current_task.get_source_abspath()
        self._log("{} processing job - {}".format(self.name, abspath))

        # # Process item in loop for the default config
        # file_in = abspath
        # file_out = self.current_task.task.cache_path
        # data = self.convert_file(file_in, file_out)

        # Then process the item for for each plugin that configures it

        # Init plugins
        plugin_handler = PluginsHandler()
        plugin_modules = plugin_handler.get_plugin_modules_by_type('worker.process_item')

        # Create dictionary of runners info for the webUI
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

        # Process item in loop.
        # First process the item for for each plugin that configures it, then run the default Unmanic configuration
        task_cache_path = self.current_task.get_cache_path()
        file_in = abspath
        overall_success = True
        current_file_out = ""
        runner_count = 0
        for plugin_module in plugin_modules:
            runner_count += 1
            self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'in_progress'
            self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False
            # Fetch file out details
            # This creates a temp file labeled "WORKING" that will be moved to the cache_path on completion
            tmp_file_out = os.path.splitext(task_cache_path)
            file_out = current_file_out = "{}-{}-{}{}".format(tmp_file_out[0], "WORKING", runner_count, tmp_file_out[1])

            # Fetch initial file probe
            file_probe = self.ffmpeg.file_probe(file_in)
            # Create args from
            ffmpeg_args = self.ffmpeg.generate_ffmpeg_args(file_probe, file_in, file_out)
            initial_data = {
                "exec_ffmpeg":        True,
                "file_probe":         file_probe,
                "ffmpeg_args":        ffmpeg_args,
                "file_in":            file_in,
                "file_out":           file_out,
                "original_file_path": abspath,
            }

            # Run plugin and fetch return data
            plugin_runner = plugin_module.get("runner")
            try:
                data = plugin_runner(initial_data)
            except Exception as e:
                self._log("Exception while carrying out plugin runner on worker process '{}'".format(
                    plugin_module.get('plugin_id')), message2=str(e), level="exception")
                # Skip this plugin module's loop
                self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'complete'
                continue
            self._log("Worker process '{}' (in)".format(plugin_module.get('plugin_id')), data.get("file_in"), level='debug')
            self._log("Worker process '{}' (out)".format(plugin_module.get('plugin_id')), data.get("file_out"), level='debug')

            # Only run the conversion process if "exec_ffmpeg" is True
            if data.get("exec_ffmpeg"):
                self.current_task.save_ffmpeg_log("\n\nRUNNER: \n" + plugin_module.get('name'))

                # Run conversion process
                success = self.convert_file(data, plugin_module.get('plugin_id'))

                if success:
                    # If file conversion was successful
                    self._log("Successfully ran worker process '{}' on file '{}'".format(plugin_module.get('plugin_id'),
                                                                                   data.get("file_in")))
                    # Set the file in as the file out for the next loop
                    file_in = data.get("file_out")
                else:
                    # If file conversion was successful
                    self._log(
                        "Error while running worker process '{}' on file '{}'".format(plugin_module.get('plugin_id'), abspath),
                        level="error")
                    self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False
                    overall_success = False
            else:
                self._log("Worker process '{}' set to not run the FFMPEG command.".format(plugin_module.get('plugin_id')),
                                                                                          level='debug')

            self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = True
            self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'complete'

        if overall_success:
            # If file conversion was successful, we will get here
            self._log("Successfully converted file '{}'".format(abspath))
            try:
                # Move file to original cache path
                self._log("Moving final cache file from '{}' to '{}'".format(current_file_out, task_cache_path))
                current_file_out = os.path.abspath(current_file_out)
                if not os.path.exists(current_file_out):
                    self._log("Error - current_file_out path does not exist! '{}'".format(file_in), level="error")
                    time.sleep(1)
                shutil.move(current_file_out, task_cache_path)
            except Exception as e:
                self._log("Exception in final move operation of file {} to {}:".format(current_file_out, task_cache_path),
                          message2=str(e), level="exception")
                return False
            return True
        self._log("Failed to convert file '{}'".format(abspath), level='warning')
        return False

    def convert_file(self, data, process_id):
        file_in = data.get("file_in")
        file_out = data.get("file_out")
        ffmpeg_args = data.get("ffmpeg_args")

        # Create output path if not exists
        common.ensure_dir(file_out)

        # Convert file
        success = False
        try:
            # Reset to defaults
            self.ffmpeg.set_info_defaults()
            # Fetch source file info
            self.ffmpeg.set_file_in(file_in)
            # Read video information for the input file
            file_probe = self.ffmpeg.file_in['file_probe']
            if not file_probe:
                return False
            if ffmpeg_args:
                success = self.ffmpeg.convert_file_and_fetch_progress(file_in, ffmpeg_args)
            self.current_task.save_ffmpeg_log(self.ffmpeg.ffmpeg_cmd_stdout)

        except ffmpeg.FFMPEGHandleConversionError as e:
            # Fetch ffmpeg stdout and append it to the current task object (to be saved during post process)
            self.current_task.save_ffmpeg_log(self.ffmpeg.ffmpeg_cmd_stdout)
            self._log("Error while executing the FFMPEG command {}. "
                      "Download FFMPEG command dump from history for more information.".format(file_in),
                      message2=str(e), level="error")
        return success

    def process_task_queue_item(self):
        self.idle = False

        abspath = self.current_task.get_source_abspath()
        self._log("{} picked up job - {}".format(self.name, abspath))

        # mark as being "in progress"
        self.current_task.set_status('in_progress')

        # Start current task stats
        self.start_task_stats()

        # Process the file. Will return true if success, otherwise false
        self.current_task.set_success(self.process_item())

        # Mark task completion statistics
        self.finish_task_stats()

        # TODO: Pass file to postprocessor thread with socket the task

        # Log completion of job
        self._log("{} finished job - {}".format(self.name, abspath))
        self.complete_queue.put(self.current_task)

        # Reset the current file info for the next task
        self.unset_current_task()

    def run(self):
        self._log("Starting {}".format(self.name))
        while not self.redundant_flag.is_set():
            self.idle = True
            while not self.redundant_flag.is_set() and not self.task_queue.empty():
                try:
                    self.set_current_task(self.task_queue.get_nowait())
                    self.process_task_queue_item()
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception in processing job with {}:".format(self.name), message2=str(e),
                              level="exception")
            time.sleep(5)
        self._log("Stopping {}".format(self.name))


class Foreman(threading.Thread):
    def __init__(self, data_queues, settings, task_queue):
        super(Foreman, self).__init__(name='Foreman')
        self.settings = settings
        self.task_queue = task_queue
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.workers_pending_task_queue = queue.Queue(maxsize=1)
        self.complete_queue = queue.Queue()
        self.worker_threads = {}
        self.remove_list = []
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()
        # Stop all workers
        for thread in range(len(self.worker_threads)):
            self.mark_worker_thread_as_redundant(thread)

    def init_worker_threads(self):
        # Remove any redundant idle workers from our list
        thread_keys = [t for t in self.worker_threads]
        for thread in thread_keys:
            if thread in self.worker_threads:
                if not self.worker_threads[thread].isAlive():
                    del self.worker_threads[thread]

        # Check that we have enough workers running. Spawn new ones as required.
        if len(self.worker_threads) < int(self.settings.get_number_of_workers()):
            self._log("Foreman Threads under the configured limit. Spawning more...")
            # Not enough workers, create some
            for i in range(int(self.settings.get_number_of_workers())):
                if i not in self.worker_threads:
                    # This worker does not yet exists, create it
                    self.start_worker_thread(i)

        # Check if we have to many workers running and stop the ones that are idle
        if len(self.worker_threads) > int(self.settings.get_number_of_workers()):
            self._log("Foreman Threads exceed the configured limit. Marking some for removal...", level='debug')
            # Too many workers, stop any idle ones
            for thread in self.worker_threads:
                if self.worker_threads[thread].idle:
                    # This thread id is greater than the max number available. We should set it as redundant
                    self.mark_worker_thread_as_redundant(thread)

    def start_worker_thread(self, worker_id):
        thread = WorkerThread(worker_id, "Worker-{}".format(worker_id), self.settings, self.data_queues,
                              self.workers_pending_task_queue, self.complete_queue)
        thread.daemon = True
        thread.start()
        self.worker_threads[worker_id] = thread

    def check_for_idle_workers(self):
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle and self.worker_threads[thread].isAlive():
                return True
        return False

    def mark_worker_thread_as_redundant(self, worker_id):
        self.worker_threads[worker_id].redundant_flag.set()
        self.remove_list.append(worker_id)

    def add_to_task_queue(self, item):
        self.workers_pending_task_queue.put(item)

    def run(self):
        self._log("Starting Foreman Monitor loop")
        while not self.abort_flag.is_set():
            time.sleep(1)

            while not self.abort_flag.is_set() and not self.complete_queue.empty():
                time.sleep(.2)
                try:
                    task_item = self.complete_queue.get_nowait()
                    task_item.set_status('processed')
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception when fetching completed task report from worker", message2=str(e),
                              level="exception")

            # First setup the correct number of workers
            if not self.abort_flag.is_set():
                self.init_worker_threads()

            if not self.abort_flag.is_set() and not self.task_queue.task_list_pending_is_empty():
                time.sleep(.2)

                # Check if there are any free workers
                if not self.check_for_idle_workers():
                    # All workers are currently busy
                    time.sleep(1)
                    continue

                # Check if we are able to start up a worker for another encoding job
                if self.workers_pending_task_queue.full():
                    continue

                next_item_to_process = self.task_queue.get_next_pending_tasks()
                if next_item_to_process:
                    try:
                        self._log("Processing item - {}".format(next_item_to_process.get_source_abspath()))
                    except Exception as e:
                        self._log("Exception in fetching task absolute path", message2=str(e), level="exception")
                    self.add_to_task_queue(next_item_to_process)

            # TODO: Add abort flag to terminate all workers

        self._log("Leaving Foreman Monitor loop...")

    def get_all_worker_status(self):
        all_status = []
        for thread in self.worker_threads:
            all_status.append(self.worker_threads[thread].get_status())
        return all_status

    def get_worker_status(self, worker_id):
        result = {}
        for thread in self.worker_threads:
            if int(worker_id) == int(thread):
                result = self.worker_threads[thread].get_status()
        return result
