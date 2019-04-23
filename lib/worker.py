#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jan 02 2019, (7:21:18 AM)
#
#   Copyright:
#          Copyright (C) Josh Sunnex - All Rights Reserved
#
#          Permission is hereby granted, free of charge, to any person obtaining a copy
#          of this software and associated documentation files (the "Software"), to deal
#          in the Software without restriction, including without limitation the rights
#          to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#          copies of the Software, and to permit persons to whom the Software is
#          furnished to do so, subject to the following conditions:
# 
#          The above copyright notice and this permission notice shall be included in all
#          copies or substantial portions of the Software.
# 
#          THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#          EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#          MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#          IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#          DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#          OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#          OR OTHER DEALINGS IN THE SOFTWARE.
#
#
###################################################################################################


import threading
import queue
import time

from lib import ffmpeg, common


class WorkerThread(threading.Thread):
    def __init__(self, threadID, name, logger, settings, data_queues, task_queue, complete_queue):
        super(WorkerThread, self).__init__(name=name)
        self.threadID           = threadID
        self.data_queues        = data_queues
        self.progress_reports   = data_queues['progress_reports']
        self.task_queue         = task_queue
        self.complete_queue     = complete_queue
        self.idle               = True
        self.current_file_info  = {}
        self.ffmpeg             = ffmpeg.FFMPEGHandle(settings, data_queues['logging'])
        self.redundant_flag     = threading.Event()
        self.redundant_flag.clear()
        self.logger             = data_queues["logging"].get_logger(self.name)

    def _log(self, message, message2 = '', level = "info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def getStatus(self):
        status = {}
        status['id']                = str(self.threadID)
        status['name']              = self.name
        status['idle']              = self.idle
        status['pid']               = self.ident
        status['progress']          = self.getJobProgress()
        status['current_file_info'] = self.current_file_info
        if 'basename' in self.current_file_info:
            status['current_file']  = self.current_file_info['basename']
        return status

    def getJobProgress(self):
        progress = {}
        progress['duration']    = str(self.ffmpeg.duration)
        progress['src_fps']     = str(self.ffmpeg.src_fps)
        progress['elapsed']     = str(self.ffmpeg.elapsed)
        progress['time']        = str(self.ffmpeg.time)
        progress['percent']     = str(self.ffmpeg.percent)
        progress['frame']       = str(self.ffmpeg.frame)
        progress['fps']         = str(self.ffmpeg.fps)
        progress['speed']       = str(self.ffmpeg.speed)
        progress['bitrate']     = str(self.ffmpeg.bitrate)
        progress['file_size']   = str(self.ffmpeg.file_size)
        return progress

    def processItem(self, pathname):
        self._log("{} running job - {}".format(self.name, pathname))
        #import random
        #number = random.randint(1,4)
        #time.sleep(number)
        #if (number > 14):
        #    return True
        #return False
        return self.ffmpeg.process_file(pathname)

    def run(self):
        self._log("Starting {}".format(self.name))
        while not self.redundant_flag.is_set():
            self.idle = True
            while not self.redundant_flag.is_set() and not self.task_queue.empty():
                try:
                    self.idle = False
                    self.current_file_info = self.task_queue.get_nowait()
                    self._log("{} picked up job - {}".format(self.name, self.current_file_info['abspath']))

                    # Process the file. Will return true if success, otherwise false
                    self.current_file_info['success'] = self.processItem(self.current_file_info['abspath'])

                    # Set the file probe data for file in and out to the current file info
                    self.current_file_info['file_in'] = self.ffmpeg.file_in
                    self.current_file_info['file_out'] = self.ffmpeg.file_out

                    # Log completion of job
                    self._log("{} finished job - {}".format(self.name, self.current_file_info['abspath']))
                    self.complete_queue.put(self.current_file_info)

                    # Reset the current file info for the next task
                    self.current_file_info = {}
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception in processing job with {}:".format(self.name), message2=str(e), level="exception")
            time.sleep(5)
        self._log("Stopping {}".format(self.name))


class Worker(threading.Thread):
    def __init__(self, data_queues, settings, job_queue):
        super(Worker, self).__init__(name='Worker')
        self.settings       = settings
        self.job_queue      = job_queue
        self.data_queues    = data_queues
        self.logger         = data_queues["logging"].get_logger(self.name)
        self.task_queue     = queue.Queue(maxsize=1)
        self.complete_queue = queue.Queue()
        self.worker_threads = {}
        self.remove_list    = []
        self.abort_flag     = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2 = '', level = "info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def initWorkerThreads(self):
        # Remove any redundant idle workers from our list
        for thread in range(len(self.worker_threads)):
            if not self.worker_threads[thread].isAlive():
                del self.worker_threads[thread]
        if len(self.worker_threads) < int(self.settings.NUMBER_OF_WORKERS):
            self._log("Worker Threads under the configured limit. Spawning more...")
            # Not enough workers, create some
            for i in range(int(self.settings.NUMBER_OF_WORKERS)):
                if not i in self.worker_threads:
                    # This worker does not yet exists, create it
                    self.startWorkerThread(i)
        # Check if we have to many workers running and stop the ones with id's higher than our configured number
        if len(self.worker_threads) > int(self.settings.NUMBER_OF_WORKERS):
            self._log("Worker Threads exceed the configured limit. Marking some for removal...")
            # Too many workers, stop any idle ones
            for thread in range(len(self.worker_threads)):
                if self.worker_threads[thread].threadID >= int(self.settings.NUMBER_OF_WORKERS):
                    # This thread id is greater than the max number available. We should set it as redundant
                    self.worker_threads[thread].redundant_flag.set()
                    self.remove_list.append(thread)
            time.sleep(2)

    def startWorkerThread(self, worker_id):
        thread = WorkerThread(worker_id, "Worker-{}".format(worker_id), self._log, self.settings, self.data_queues, self.task_queue, self.complete_queue)
        thread.start()
        self.worker_threads[worker_id] = thread

    def checkForIdleWorkers(self):
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle:
                return True
        return False

    def addToTaskQueue(self, item):
        self.task_queue.put(item)

    def run(self):
        self._log("Starting Worker Monitor loop...")
        while not self.abort_flag.is_set():
            time.sleep(1)

            # First setup the correct number of workers
            self.initWorkerThreads()

            # Check if there are any free workers
            if not self.checkForIdleWorkers():
                # All workers are currently busy
                time.sleep(5)
                continue

            while not self.abort_flag.is_set() and not self.complete_queue.empty():
                time.sleep(.2)
                try:
                    file_info = self.complete_queue.get_nowait()
                    self.job_queue.remove_completed_item(file_info)
                    self.settings.write_history_log(file_info)
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception when fetching completed task report from worker", message2=str(e), level="exception")

            while not self.abort_flag.is_set() and not self.job_queue.incoming_is_empty():
                time.sleep(.2)
                # Ensure we have the correct number of workers running
                self.initWorkerThreads()
                # Check if we are able to start up a worker for another encoding job
                if self.task_queue.full():
                    break
                next_item_to_process = self.job_queue.get_next_incoming_item()
                if next_item_to_process:
                    self._log("Processing item - {}".format(next_item_to_process['abspath']))
                    self.addToTaskQueue(next_item_to_process)

            # TODO: Add abort flag to terminate all workers

        self._log("Leaving Worker Monitor loop...")

    def getAllWorkerStatus(self):
        all_status = []
        for thread in self.worker_threads:
            all_status.append(self.worker_threads[thread].getStatus())
        return all_status

    def getAllHistoricalTasks(self):
        return self.settings.read_history_log()



