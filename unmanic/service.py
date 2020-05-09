#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.service.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2018, (7:21 AM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be includeed in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""

import os
import sys
import json
import time
import threading
import queue
import pyinotify
import schedule
import signal

from unmanic import config
from unmanic.libs import unlogger, common, ffmpeg
from unmanic.libs.jobqueue import JobQueue
from unmanic.libs.postprocessor import PostProcessor
from unmanic.libs.taskhandler import TaskHandler
from unmanic.libs.uiserver import UIServer
from unmanic.libs.worker import Worker

unmanic_logging = unlogger.UnmanicLogger.__call__()
main_logger = unmanic_logging.get_logger()


class LibraryScanner(threading.Thread):
    def __init__(self, data_queues, settings):
        super(LibraryScanner, self).__init__(name='LibraryScanner')
        self.interval = 0
        self.firstrun = True
        self.settings = settings
        self.logger = data_queues["logging"].get_logger(self.name)
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting LibraryScanner Monitor loop")
        while not self.abort_flag.is_set():
            # Main loop to configure the scheduler
            if int(self.settings.SCHEDULE_FULL_SCAN_MINUTES) != self.interval:
                self.interval = int(self.settings.SCHEDULE_FULL_SCAN_MINUTES)
            if self.interval and self.interval != 0:
                self._log("Setting LibraryScanner schedule to scan every {} mins...".format(self.interval))
                # Configure schedule
                schedule.every(self.interval).minutes.do(self.scheduled_job)

                # First run the task
                if self.settings.RUN_FULL_SCAN_ON_START and self.firstrun:
                    self._log("Running LibraryScanner on start")
                    self.scheduled_job()
                self.firstrun = False

                # Then loop and wait for the schedule
                while not self.abort_flag.is_set():
                    # TODO: Dont run scheduler if we already have a full queue
                    schedule.run_pending()
                    time.sleep(1)
                    # If the settings have changed, then break this loop and clear
                    # the scheduled job resetting to the new interval
                    if int(self.settings.SCHEDULE_FULL_SCAN_MINUTES) != self.interval:
                        self._log("Resetting LibraryScanner schedule")
                        break
                schedule.clear()

        self._log("Leaving LibraryScanner Monitor loop...")

    def scheduled_job(self):
        self._log("Running full library scan")
        self.get_convert_files(self.settings.LIBRARY_PATH)

    def add_path_to_queue(self, pathname):
        self.scheduledtasks.put(pathname)

    def file_not_target_format(self, pathname):
        # Reset file in
        self.ffmpeg.file_in = {}
        # Check if file matches configured codec and format
        if not self.ffmpeg.check_file_to_be_processed(pathname):
            if self.settings.DEBUGGING:
                self._log("File does not need to be processed - {}".format(pathname))
            return False
        return True

    def get_convert_files(self, search_folder):
        if self.settings.DEBUGGING:
            self._log("Scanning directory - '{}'".format(search_folder))
        for root, subFolders, files in os.walk(search_folder):
            if self.settings.DEBUGGING:
                self._log(json.dumps(files, indent=2))
            # Add all files in this path that match our container filter
            for file_path in files:
                if self.settings.file_ends_in_allowed_search_extensions(file_path):
                    pathname = os.path.join(root, file_path)
                    # Check if this file is already the correct format:
                    if self.file_not_target_format(pathname):
                        self.add_path_to_queue(pathname)
                    elif self.settings.DEBUGGING:
                        self._log("Ignoring file due to already correct format - '{}'".format(file_path))
                elif self.settings.DEBUGGING:
                    self._log("Ignoring file due to incorrect suffix - '{}'".format(file_path))


class EventProcessor(pyinotify.ProcessEvent):
    def __init__(self, data_queues, settings):
        self.name = "EventProcessor"
        self.settings = settings
        self.logger = data_queues["logging"].get_logger(self.name)
        self.inotifytasks = data_queues["inotifytasks"]
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def inotify_enabled(self):
        if self.settings.ENABLE_INOTIFY:
            return True
        return False

    def add_path_to_queue(self, pathname):
        self.inotifytasks.put(pathname)

    def file_not_target_format(self, pathname):
        # Reset file in
        self.ffmpeg.file_in = {}
        # Check if file matches configured codec and format
        if not self.ffmpeg.check_file_to_be_processed(pathname):
            if self.settings.DEBUGGING:
                self._log("File does not need to be processed - {}".format(pathname))
            return False
        return True

    def process_IN_CLOSE_WRITE(self, event):
        if self.inotify_enabled():
            self._log("CLOSE_WRITE event detected:", event.pathname)
            if self.settings.file_ends_in_allowed_search_extensions(event.pathname):
                # Add it to the queue
                if self.file_not_target_format(event.pathname):
                    self.add_path_to_queue(event.pathname)
                elif self.settings.DEBUGGING:
                    self._log("Ignoring file due to already correct format - '{}'".format(event.pathname))
            elif self.settings.DEBUGGING:
                self._log("Ignoring file due to incorrect suffix - '{}'".format(event.pathname))

    def process_IN_MOVED_TO(self, event):
        if self.inotify_enabled():
            self._log("MOVED_TO event detected:", event.pathname)
            if self.settings.file_ends_in_allowed_search_extensions(event.pathname):
                # Add it to the queue
                if self.file_not_target_format(event.pathname):
                    self.add_path_to_queue(event.pathname)
                elif self.settings.DEBUGGING:
                    self._log("Ignoring file due to already correct format - '{}'".format(event.pathname))
            elif self.settings.DEBUGGING:
                self._log("Ignoring file due to incorrect suffix - '{}'".format(event.pathname))

    def process_IN_DELETE(self, event):
        if self.inotify_enabled():
            self._log("DELETE event detected:", event.pathname)
            self._log("Nothing to do for this event")

    def process_default(self, event):
        pass


class Service:

    def __init__(self):
        self.threads = []
        self.run_threads = True

    def start_handler(self, data_queues, settings, job_queue):
        main_logger.info("Starting TaskHandler")
        handler = TaskHandler(data_queues, settings, job_queue)
        handler.daemon = True
        handler.start()
        self.threads.append({
            'name':   'TaskHandler',
            'thread': handler
        })
        return handler

    def start_post_processor(self, data_queues, settings, job_queue):
        main_logger.info("Starting PostProcessor")
        postprocessor = PostProcessor(data_queues, settings, job_queue)
        postprocessor.daemon = True
        postprocessor.start()
        self.threads.append({
            'name':   'PostProcessor',
            'thread': postprocessor
        })
        return postprocessor

    def start_workers(self, data_queues, settings, job_queue):
        main_logger.info("Starting Workers")
        worker = Worker(data_queues, settings, job_queue)
        worker.daemon = True
        worker.start()
        self.threads.append({
            'name':   'Workers',
            'thread': worker
        })
        return worker

    def start_library_scanner_manager(self, data_queues, settings):
        main_logger.info("Starting LibraryScanner")
        scheduler = LibraryScanner(data_queues, settings)
        scheduler.daemon = True
        scheduler.start()
        self.threads.append({
            'name':   'LibraryScanner',
            'thread': scheduler
        })
        return scheduler

    def start_inotify_watch_manager(self, data_queues, settings):
        main_logger.info("Starting EventProcessor")
        wm = pyinotify.WatchManager()
        wm.add_watch(settings.LIBRARY_PATH, pyinotify.ALL_EVENTS, rec=True)
        # event processor
        ep = EventProcessor(data_queues, settings)
        # notifier
        notifier = pyinotify.ThreadedNotifier(wm, ep)
        notifier.start()
        self.threads.append({
            'name':   'EventProcessor',
            'thread': notifier
        })
        return notifier

    def start_ui_server(self, data_queues, settings, worker_handle):
        main_logger.info("Starting UIServer")
        uiserver = UIServer(data_queues, settings, worker_handle)
        uiserver.daemon = True
        uiserver.start()
        self.threads.append({
            'name':   'UIServer',
            'thread': uiserver
        })
        return uiserver

    def sig_handle(self, a, b):
        main_logger.info("SIGTERM Received")
        self.run_threads = False

    def run(self):
        # Read settings
        settings = config.CONFIG()

        # Create our data queues
        data_queues = {
            "scheduledtasks":   queue.Queue(),
            "inotifytasks":     queue.Queue(),
            "progress_reports": queue.Queue(),
            "logging":          unmanic_logging
        }

        # Clear cache directory
        common.clean_files_in_dir(settings.CACHE_PATH)

        # Setup job queue
        job_queue = JobQueue(settings, data_queues)

        # Setup post-processor thread
        self.start_post_processor(data_queues, settings, job_queue)

        # Start the worker threads
        worker_handle = self.start_workers(data_queues, settings, job_queue)

        # Start new thread to handle messages from service
        self.start_handler(data_queues, settings, job_queue)

        # Start new thread to run the web UI
        self.start_ui_server(data_queues, settings, worker_handle)

        # Start scheduled thread
        self.start_library_scanner_manager(data_queues, settings)

        # Start inotify watch manager
        self.start_inotify_watch_manager(data_queues, settings)

        # Watch for the term signal
        signal.signal(signal.SIGINT, self.sig_handle)
        signal.signal(signal.SIGTERM, self.sig_handle)
        while self.run_threads:
            signal.pause()

        # Received term signal. Stop everything
        main_logger.info("Stopping all threads")
        for thread in self.threads:
            main_logger.info("Sending thread {} abort signal".format(thread['name']))
            thread['thread'].stop()
            main_logger.info("Waiting for thread {} to stop".format(thread['name']))
            thread['thread'].join()
        main_logger.info("Exit Unmanic")


def main():
    service = Service()
    service.run()


if __name__ == "__main__":
    main()
