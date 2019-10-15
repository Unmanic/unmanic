#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.worker.py

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
import threading
import queue
import time
import sys

try:
    from lib import common, history, ffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from lib import common, history


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

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def get_status(self):
        status = {
            'id':           str(self.thread_id),
            'name':         self.name,
            'idle':         self.idle,
            'pid':          self.ident,
            'progress':     self.get_job_progress(),
            'current_file': "",
            'start_time':   self.start_time
        }
        if self.current_task:
            status['current_file'] = self.current_task.get_source_basename()
        return status

    def get_job_progress(self):
        progress = {}
        if self.current_task:
            progress['duration'] = str(self.current_task.ffmpeg.duration)
            progress['src_fps'] = str(self.current_task.ffmpeg.src_fps)
            progress['elapsed'] = str(self.current_task.ffmpeg.elapsed)
            progress['time'] = str(self.current_task.ffmpeg.time)
            progress['percent'] = str(self.current_task.ffmpeg.percent)
            progress['frame'] = str(self.current_task.ffmpeg.frame)
            progress['fps'] = str(self.current_task.ffmpeg.fps)
            progress['speed'] = str(self.current_task.ffmpeg.speed)
            progress['bitrate'] = str(self.current_task.ffmpeg.bitrate)
            progress['file_size'] = str(self.current_task.ffmpeg.file_size)
        return progress

    def set_current_task(self, current_task):
        self.current_task = current_task

    def unset_current_task(self):
        self.current_task = None

    def start_task_stats(self):
        self.start_time = time.time()
        self.finish_time = None
        # Format our final statistics data
        statistics = {
            'processed_by_worker': self.name,
            'start_time':          self.start_time,
            'finish_time':         self.finish_time,
            'video_encoder':       self.settings.get_configured_video_encoder(),
            'audio_encoder':       self.settings.get_configured_audio_encoder()
        }
        # TODO: If this was a clone/copy, add clone/copied encoder info to stats
        # Send statistic data to task to be applied
        self.current_task.set_task_stats(statistics)

    def finish_task_stats(self):
        self.finish_time = time.time()
        # Format our final statistics data
        statistics = {
            'processed_by_worker': self.name,
            'start_time':          self.start_time,
            'finish_time':         self.finish_time
        }
        # Send statistic data to task to be applied
        self.current_task.set_task_stats(statistics)

    def process_item(self):
        abspath = self.current_task.get_source_abspath()
        self._log("{} processing job - {}".format(self.name, abspath))

        # Create output path if not exists
        common.ensure_dir(self.current_task.cache_path)

        # Convert file
        success = False
        try:
            ffmpeg_args = self.current_task.ffmpeg.generate_ffmpeg_args()
            if ffmpeg_args:
                success = self.current_task.ffmpeg.convert_file_and_fetch_progress(abspath,
                                                                                   self.current_task.cache_path,
                                                                                   ffmpeg_args)
            self.current_task.ffmpeg_log = self.current_task.ffmpeg.ffmpeg_cmd_stdout

        except ffmpeg.FFMPEGHandleConversionError as e:
            # Fetch ffmpeg stdout and append it to the current task object (to be saved during post process)
            self.current_task.ffmpeg_log = self.current_task.ffmpeg.ffmpeg_cmd_stdout
            self._log("Error while executing the FFMPEG command {}. "
                      "Download FFMPEG command dump from history for more information.".format(abspath),
                      message2=str(e), level="error")

        if success:
            # If file conversion was successful, we will get here
            self._log("Successfully converted file '{}'".format(abspath))
            return True
        self._log("Failed to convert file '{}'".format(abspath), level='warning')
        return False

    def process_task_queue_item(self):
        self.idle = False
        abspath = self.current_task.get_source_abspath()
        self._log("{} picked up job - {}".format(self.name, abspath))

        # Start current task stats
        self.start_task_stats()

        # Process the file. Will return true if success, otherwise false
        self.current_task.success = self.process_item()

        # Mark task completion statistics
        self.finish_task_stats()

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


class Worker(threading.Thread):
    def __init__(self, data_queues, settings, job_queue):
        super(Worker, self).__init__(name='Worker')
        self.settings = settings
        self.job_queue = job_queue
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.task_queue = queue.Queue(maxsize=1)
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
        if len(self.worker_threads) < int(self.settings.NUMBER_OF_WORKERS):
            self._log("Worker Threads under the configured limit. Spawning more...")
            # Not enough workers, create some
            for i in range(int(self.settings.NUMBER_OF_WORKERS)):
                if i not in self.worker_threads:
                    # This worker does not yet exists, create it
                    self.start_worker_thread(i)

        # Check if we have to many workers running and stop the ones that are idle
        if len(self.worker_threads) > int(self.settings.NUMBER_OF_WORKERS):
            self._log("Worker Threads exceed the configured limit. Marking some for removal...")
            # Too many workers, stop any idle ones
            for thread in self.worker_threads:
                if self.worker_threads[thread].idle:
                    # This thread id is greater than the max number available. We should set it as redundant
                    self.mark_worker_thread_as_redundant(thread)

    def start_worker_thread(self, worker_id):
        thread = WorkerThread(worker_id, "Worker-{}".format(worker_id), self.settings, self.data_queues,
                              self.task_queue, self.complete_queue)
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
        self.task_queue.put(item)

    def run(self):
        self._log("Starting Worker Monitor loop")
        while not self.abort_flag.is_set():
            time.sleep(1)

            while not self.abort_flag.is_set() and not self.complete_queue.empty():
                time.sleep(.2)
                try:
                    task_item = self.complete_queue.get_nowait()
                    self.job_queue.mark_item_as_processed(task_item)
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception when fetching completed task report from worker", message2=str(e),
                              level="exception")

            # First setup the correct number of workers
            self.init_worker_threads()

            # Check if there are any free workers
            if not self.check_for_idle_workers():
                # All workers are currently busy
                time.sleep(5)
                continue

            if not self.job_queue.incoming_is_empty():
                time.sleep(.2)
                # Check if we are able to start up a worker for another encoding job
                if self.task_queue.full():
                    continue
                next_item_to_process = self.job_queue.get_next_incoming_item()
                if next_item_to_process:
                    self._log("Processing item - {}".format(next_item_to_process.get_source_abspath()))
                    self.add_to_task_queue(next_item_to_process)

            # TODO: Add abort flag to terminate all workers

        self._log("Leaving Worker Monitor loop...")

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
