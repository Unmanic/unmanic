#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Dec 06 2018, (7:21:18 AM)
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



import os, sys, json, time, shutil, importlib

import threading
import queue
import pyinotify
import schedule


sys.path.append('lib')
sys.path.append('webserver')

import config
from lib import common
from lib.uiserver import UIServer
from lib.worker import JobQueue
from lib.worker import Worker
from lib import ffmpeg



threads   = []

# The TaskHandler reads all items in the queues and passes them to the appropriate locations in the application.
# All messages are passed to the logger and all tasks are added to the job queue
class TaskHandler(threading.Thread):
    def __init__(self, data_queues, settings, job_queue):
        super(TaskHandler, self).__init__(name='TaskHandler')
        self.settings       = settings
        self.job_queue      = job_queue
        self.messages       = data_queues["messages"]
        self.inotifytasks   = data_queues["inotifytasks"]
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.abort_flag     = threading.Event()
        self.abort_flag.clear()

    def run(self):
        common._logger("Starting TaskHandler Monitor loop...")
        while not self.abort_flag.is_set():
            while not self.abort_flag.is_set() and not self.messages.empty():
                try:
                    log      = self.messages.get_nowait()
                    message  = None
                    message2 = None
                    level    = "info"
                    if "message" in log:
                        message = log["message"]
                    if "message2" in log:
                        message2 = log["message2"]
                    if "level" in log:
                        level = log["level"]
                    common._logger(message=message, message2=message2, level=level)
                except queue.Empty:
                    continue
                except Exception as e:
                    common._logger("Exception in logging:", message2=str(e), level="exception")
            while not self.abort_flag.is_set() and not self.scheduledtasks.empty():
                try:
                    pathname = self.scheduledtasks.get_nowait()
                    common._logger("Adding job to queue - {}".format(pathname))
                    self.job_queue.addItem(pathname)
                except queue.Empty:
                    continue
                except Exception as e:
                    common._logger("Exception in processing scheduledtasks:", message2=str(e), level="exception")
            time.sleep(.2)
        common._logger("Leaving TaskHandler Monitor loop...")



class LibraryScanner(threading.Thread):
    def __init__(self, data_queues, settings):
        super(LibraryScanner, self).__init__(name='LibraryScanner')
        self.interval       = 0
        self.firstrun       = True
        self.settings       = settings
        self.messages       = data_queues["messages"]
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.abort_flag     = threading.Event()
        self.abort_flag.clear()
        self.ffmpeg         = ffmpeg.FFMPEGHandle(settings, data_queues['messages'])

    def _log(self, message, message2 = '', level = "info"):
        message = "[{}] {}".format(self.name, message)
        self.messages.put({
              "message":message
            , "message2":message2
            , "level":level
        })

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        while not self.abort_flag.is_set():
            # Main loop to configure the scheduler
            if int(self.settings.SCHEDULE_FULL_SCAN_MINS) != self.interval:
                self.interval = int(self.settings.SCHEDULE_FULL_SCAN_MINS)
            if self.interval and self.interval != 0:
                self._log("Starting LibraryScanner schedule to scan every {} mins...".format(self.interval))
                # Configure schedule
                schedule.every(self.interval).minutes.do(self.scheduledJob)

                # First run the task
                if self.settings.RUN_FULL_SCAN_ON_START and self.firstrun:
                    self._log("Running LibraryScanner on start")
                    self.scheduledJob()
                self.firstrun = False

                # Then loop and wait for the schedule
                while not self.abort_flag.is_set():
                    schedule.run_pending()
                    time.sleep(60)
                    if int(self.settings.SCHEDULE_FULL_SCAN_MINS) != self.interval:
                        break
                schedule.clear()
                self._log("Stopping LibraryScanner schedule...")
        time.sleep(5)

    def scheduledJob(self):
        self._log("Running full library scan")
        self.getConvertFiles(self.settings.LIBRARY_PATH)

    def addPathToQueue(self,pathname):
        self.scheduledtasks.put(pathname)

    def fileNotTargetFormat(self,pathname):
        if not self.ffmpeg.checkFileToBeProcessed(pathname):
            if self.settings.DEBUGGING:
                self._log("File does not need to be processed - {}".format(pathname))
            return False
        return True

    def getConvertFiles(self, search_folder):
        self._log(search_folder)
        for root, subFolders, files in os.walk(search_folder):
            if self.settings.DEBUGGING:
                self._log(json.dumps(files,indent=2))
            # Add all files in this path that match our container filter
            for file_path in files:
                if file_path.lower().endswith(self.settings.SUPPORTED_CONTAINERS):
                    pathname = os.path.join(root,file_path)
                    # Check if this file is already the correct format:
                    if self.fileNotTargetFormat(pathname):
                        self.addPathToQueue(pathname)
                else:
                    if self.settings.DEBUGGING:
                        self._log("Ignoring file due to incorrect suffix - '{}'".format(file_path))
                


class EventProcessor(pyinotify.ProcessEvent):
    def __init__(self, data_queues, settings):
        self.name           = "EventProcessor"
        self.settings       = settings
        self.messages       = data_queues["messages"]
        self.inotifytasks   = data_queues["inotifytasks"]
        self.abort_flag     = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2 = '', level = "info"):
        message = "[{}] {}".format(self.name, message)
        self.messages.put({
              "message":message
            , "message2":message2
            , "level":level
        })

    def addPathToQueue(self,pathname):
        self.inotifytasks.put(pathname)

    def process_IN_CLOSE_WRITE(self, event):
        self._log("CLOSE_WRITE event detected:", event.pathname)
        if event.pathname.lower().endswith(self.settings.SUPPORTED_CONTAINERS):
            # Add it to the queue
            self.addPathToQueue(event.pathname)
        else:
            if self.settings.DEBUGGING:
                self._log("Ignoring file due to incorrect suffix - '{}'".format(event.pathname))

    def process_IN_DELETE(self, event):
        self._log("DELETE event detected:", event.pathname)
        self._log("Nothing to do for this event")

    def process_IN_MOVED_FROM(self, event):
        self._log("MOVED_FROM event detected:", event.pathname)
        self._log("Nothing to do for this event")


def start_handler(data_queues, settings, job_queue):
    common._logger("Starting TaskHandler")
    handler = TaskHandler(data_queues, settings, job_queue)
    handler.daemon=True
    handler.start()
    return handler


def start_workers(data_queues, settings, job_queue):
    common._logger("Starting Workers")
    worker = Worker(data_queues, settings, job_queue)
    worker.daemon=True
    worker.start()
    return worker


def start_library_scanner_manager(data_queues, settings):
    common._logger("Starting LibraryScanner")
    scheduler = LibraryScanner(data_queues, settings)
    scheduler.daemon=True
    scheduler.start()
    return scheduler


def start_inotify_watch_manager(data_queues, settings):
    common._logger("Starting EventProcessor")
    wm = pyinotify.WatchManager()
    wm.add_watch(settings.LIBRARY_PATH, pyinotify.ALL_EVENTS, rec=True)
    # event processor
    ep = EventProcessor(data_queues, settings)
    # notifier
    notifier = pyinotify.ThreadedNotifier(wm, ep)
    return notifier


def start_ui_server(data_queues, settings, workerHandle):
    common._logger("Starting UI Server")
    uiserver = UIServer(data_queues, settings, workerHandle)
    uiserver.daemon=True
    uiserver.start()
    return uiserver


def main():
    data_queues = {
          "scheduledtasks":     queue.Queue()
        , "inotifytasks":       queue.Queue()
        , "messages":           queue.Queue()
        , "progress_reports":   queue.Queue()
    }

    settings  = config.CONFIG()
    job_queue = JobQueue(settings, data_queues)

    # Start the worker threads
    workerHandle = start_workers(data_queues, settings, job_queue)

    # Start new thread to handle messages from service
    handler = start_handler(data_queues, settings, job_queue)

    # Start new thread to run the web UI
    uiserver = start_ui_server(data_queues, settings, workerHandle)

    # start scheduled thread
    scheduler = start_library_scanner_manager(data_queues, settings)

    # start inotify watch manager
    notifier = start_inotify_watch_manager(data_queues, settings)
    notifier.loop()
    while True:
        time.sleep(5)

    # stop everything
    common._logger("Stopping all processes")
    scheduler.abort_flag.set()
    handler.abort_flag.set()
    scheduler.join()
    handler.join()
    common._logger("Exit")

if (__name__ == "__main__"):
    main()
