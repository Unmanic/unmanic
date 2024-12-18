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
import queue
import threading
import time

from unmanic import config
from unmanic.libs.library import Library
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.plugins import PluginsHandler

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

from unmanic.libs.filetest import FileTest


class EventHandler(FileSystemEventHandler):
    """
    Handle any library file modification events

    This watchdog library is not strictly inline with inotify...
    It does not watch MOVED_TO, CREATED, DELETE, MODIFIED, CLOSE_WRITE like the previous library did.
    Instead the outputs for a Unix FS are as follows:
        - Read = []                                             : No events are triggered for reading a file
        - Modify = ["modified", "closed"]                       :
        - Move (atomic) = ["created", "modified"]               :
        - Move (non-atomic) = ["created", "modified", "closed"] : Lots of 'modified' events as the file was "copied"
        - Copy = ["created", "modified", "closed"]              : ^ ditto
        - Create = ["created", "modified", "closed"]            : ^ ditto
        - Delete = ["deleted", "modified"]                      :
        - Hardlink = ["created", "modified"]                    :

    From this, the only event we really need to monitor is the "created" and "closed" events.
    """

    def __init__(self, files_to_test, library_id):
        self.name = __class__.__name__
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self.files_to_test = files_to_test
        self.library_id = library_id
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

    def on_any_event(self, event):
        if event.event_type in ["created", "closed"]:
            # Ensure event was not for a directory
            if event.is_directory:
                self.logger.debug("Detected event is for a directory. Ignoring...")
            else:
                self.logger.info("Detected '%s' event on file path '%s'", event.event_type, event.src_path)
                self.files_to_test.put({
                    'src_path':   event.src_path,
                    'library_id': self.library_id,
                })


class EventMonitorManager(threading.Thread):
    """
    EventMonitorManager

    Manage the EventProcessor thread.
    If the settings for enabling the EventProcessor changes, this manager
    class will stop or start the EventProcessor thread accordingly.

    """

    def __init__(self, data_queues, event):
        super(EventMonitorManager, self).__init__(name='EventMonitorManager')
        self.name = __class__.__name__
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self.data_queues = data_queues
        self.settings = config.Config()
        self.event = event

        # Create an event queue
        self.files_to_test = queue.Queue()

        self.abort_flag = threading.Event()
        self.abort_flag.clear()

        self.event_observer_thread = None
        self.event_observer_threads = []

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self.logger.info("Starting EventMonitorManager loop")
        while not self.abort_flag.is_set():
            self.event.wait(.5)

            if not self.system_configuration_is_valid():
                self.event.wait(2)
                continue

            if not self.files_to_test.empty():
                item = self.files_to_test.get()
                pathname = item.get('src_path')
                library_id = item.get('library_id')
                self.manage_event_queue(pathname, library_id)
                continue

            # Check if monitor is enabled for at least one library
            enable_inotify = False
            for lib_info in Library.get_all_libraries():
                try:
                    library = Library(lib_info['id'])
                except Exception as e:
                    self.logger.exception("Unable to fetch library config for ID %s", lib_info['id'])
                    continue
                # Check if the library is configured for remote files only
                if library.get_enable_remote_only():
                    # This library is configured to receive remote files only... Never enable the file monitor
                    continue
                # Check if file monitor is enabled on any library
                if library.get_enable_inotify():
                    enable_inotify = True

            # If at least library has the monitor enabled, then start it. Otherwise stop the monitor process
            if enable_inotify:
                # If enabled, ensure it is running and start it if it is not
                if not self.event_observer_thread:
                    self.start_event_processor()
            else:
                # If not enabled, ensure the EventProcessor is not running and stop it if it is
                if self.event_observer_thread:
                    self.stop_event_processor()
            # Add delay
            self.event.wait(2)

        self.stop_event_processor()
        self.logger.info("Leaving EventMonitorManager loop...")

    def system_configuration_is_valid(self):
        """
        Check and ensure the system configuration is correct for running

        :return:
        """
        valid = True
        plugin_handler = PluginsHandler()
        if plugin_handler.get_incompatible_enabled_plugins(self.data_queues.get('frontend_messages')):
            valid = False
        if not Library.within_library_count_limits(self.data_queues.get('frontend_messages')):
            valid = False
        return valid

    def start_event_processor(self):
        """
        Start the EventProcessor thread if it is not already running.

        :return:
        """
        if not self.event_observer_thread:
            monitoring_path = False
            self.event_observer_thread = Observer()
            for lib_info in Library.get_all_libraries():
                self.event.wait(.2)
                try:
                    library = Library(lib_info['id'])
                except Exception as e:
                    self.logger.exception("Unable to fetch library config for ID %s", lib_info['id'])
                    continue
                # Check if the library is configured for remote files only
                if library.get_enable_remote_only():
                    # This library is configured to receive remote files only... Never enable the file monitor
                    continue
                # Check if library scanner is enabled on any library
                if library.get_enable_inotify():
                    library_path = library.get_path()
                    if not os.path.exists(library_path):
                        continue
                    self.logger.info("Adding library path to monitor '%s'", library_path)
                    event_handler = EventHandler(self.files_to_test, library.get_id())
                    self.event_observer_thread.schedule(event_handler, library_path, recursive=True)
                    monitoring_path = True
            # Only start observer if a path was added to be monitored
            if monitoring_path:
                self.logger.info("EventMonitorManager spawning EventProcessor thread...")
                self.event_observer_thread.start()
        else:
            self.logger.info("Given signal to start the EventProcessor thread, but it is already running....")

    def stop_event_processor(self):
        """
        Stop the EventProcessor thread if it is running.

        :return:
        """
        if self.event_observer_thread:
            self.logger.info("EventMonitorManager stopping EventProcessor thread...")

            self.logger.info("Sending thread EventProcessor abort signal")
            self.event_observer_thread.stop()

            self.logger.info("Waiting for thread EventProcessor to stop")
            self.event_observer_thread.join()
            self.logger.info("Thread EventProcessor has successfully stopped")
        else:
            self.logger.info("Given signal to stop the EventProcessor thread, but it is not running...")

        self.event_observer_thread = None

    def manage_event_queue(self, pathname, library_id):
        """
        Manage all monitored events

        Unlike the library scanner, all events are processed sequentially one at a time.
        This avoids a file being added twice on 2 events.

        :param pathname:
        :param library_id:
        :return:
        """
        # Test file to be added to task list. Add it if required
        try:
            file_test = FileTest(library_id)
            result, issues, priority_score = file_test.should_file_be_added_to_task_list(pathname)
            # Log any error messages
            for issue in issues:
                if type(issue) is dict:
                    self.logger.info(issue.get('message'))
                else:
                    self.logger.info(issue)
            # If file needs to be added, then add it
            if result:
                self.__add_path_to_queue(pathname, library_id, priority_score)
        except UnicodeEncodeError:
            self.logger.warning("File contains Unicode characters that cannot be processed. Ignoring.")
        except Exception as e:
            self.logger.exception("Exception testing file path in %s. Ignoring.", self.name)

    def __add_path_to_queue(self, pathname, library_id, priority_score):
        """
        Add a given path to the pending task queue

        :param pathname:
        :param library_id:
        :param priority_score:
        :return:
        """
        self.data_queues.get('inotifytasks').put({
            'pathname':       pathname,
            'library_id':     library_id,
            'priority_score': priority_score,
        })
