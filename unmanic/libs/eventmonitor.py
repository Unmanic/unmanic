#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.eventmonitor.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Feb 2021, (10:06 AM)

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
import time

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    event_monitor_module = 'watchdog'
except ImportError:
    class Observer(object):
        pass


    class FileSystemEventHandler(object):
        pass


    event_monitor_module = None

from unmanic.libs import common, unlogger
from unmanic.libs.filetest import FileTest


class EventHandler(FileSystemEventHandler):
    def __init__(self, data_queues, settings):
        self.name = "EventProcessor"
        self.settings = settings
        self.inotifytasks = data_queues["inotifytasks"]
        self.logger = None
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        if not self.logger:
            unmanic_logging = unlogger.UnmanicLogger.__call__()
            self.logger = unmanic_logging.get_logger(self.name)
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __add_path_to_queue(self, pathname):
        self.inotifytasks.put(pathname)

    def __handle_event(self, event):
        # Ensure event was not for a directory
        if event.is_directory:
            self._log("Detected even is for a directory. Ignoring...")
            return

        # Get full path to file
        pathname = event.src_path

        # Test file to be added to task list. Add it if required
        file_test = FileTest(self.settings, pathname)
        result, issues = file_test.should_file_be_added_to_task_list()
        # Log any error messages
        for issue in issues:
            if type(issue) is dict:
                self._log(issue.get('message'))
            else:
                self._log(issue)
        # If file needs to be added, then add it
        if result:
            self.__add_path_to_queue(pathname)

    def on_moved(self, event):
        self._log("MOVED_TO event detected:", event.src_path)
        self.__handle_event(event)

    def on_created(self, event):
        # self._log("CREATED event detected:", event.src_path)
        pass

    def on_deleted(self, event):
        # self._log("DELETE event detected:", event.src_path)
        pass

    def on_modified(self, event):
        # self._log("MODIFIED event detected:", event.src_path)
        pass

    def on_closed(self, event):
        self._log("CLOSE_WRITE event detected:", event.src_path)
        self.__handle_event(event)


class EventMonitorManager(threading.Thread):
    """
    EventMonitorManager

    Manage the EventProcessor thread.
    If the settings for enabling the EventProcessor changes, this manager
    class will stop or start the EventProcessor thread accordingly.

    """

    def __init__(self, data_queues, settings):
        super(EventMonitorManager, self).__init__(name='EventMonitorManager')
        self.name = "EventMonitorManager"
        self.settings = settings
        self.data_queues = data_queues

        self.logger = data_queues["logging"].get_logger(self.name)
        self.inotifytasks = data_queues["inotifytasks"]

        self.abort_flag = threading.Event()
        self.abort_flag.clear()

        self.event_observer_thread = None

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting EventMonitorManager loop")
        while not self.abort_flag.is_set():
            # Check settings to ensure the event monitor should be enabled...
            if self.settings.get_enable_inotify():
                # If enabled, ensure it is running and start it if it is not
                if not self.event_observer_thread:
                    self.start_event_processor()
            else:
                # If not enabled, ensure the EventProcessor is not running and stop it if it is
                if self.event_observer_thread:
                    self.stop_event_processor()
            # Add delay
            time.sleep(.5)

        self.stop_event_processor()
        self._log("Leaving EventMonitorManager loop...")

    def start_event_processor(self):
        """
        Start the EventProcessor thread if it is not already running.

        :return:
        """
        if not self.event_observer_thread:
            library_path = self.settings.get_library_path()
            if not os.path.exists(library_path):
                time.sleep(.1)
                return
            self._log("EventMonitorManager spawning EventProcessor thread...")
            event_handler = EventHandler(self.data_queues, self.settings)

            self.event_observer_thread = Observer()
            self.event_observer_thread.schedule(event_handler, self.settings.get_library_path(), recursive=True)

            self.event_observer_thread.start()
        else:
            self._log("Given signal to start the EventProcessor thread, but it is already running....")

    def stop_event_processor(self):
        """
        Stop the EventProcessor thread if it is running.

        :return:
        """
        if self.event_observer_thread:
            self._log("EventMonitorManager stopping EventProcessor thread...")

            self._log("Sending thread EventProcessor abort signal")
            self.event_observer_thread.stop()

            self._log("Waiting for thread EventProcessor to stop")
            self.event_observer_thread.join()
            self._log("Thread EventProcessor has successfully stopped")
        else:
            self._log("Given signal to stop the EventProcessor thread, but it is not running...")

        self.event_observer_thread = None
