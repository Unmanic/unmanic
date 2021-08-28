#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.libraryscanner.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     20 Aug 2021, (5:37 PM)

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
import json
import os
import queue
import threading
import time

import schedule

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.filetest import FileTest


class LibraryScannerManager(threading.Thread):
    def __init__(self, data_queues):
        super(LibraryScannerManager, self).__init__(name='LibraryScannerManager')
        self.interval = 0
        self.firstrun = True
        self.data_queues = data_queues
        self.settings = config.Config()
        self.logger = None
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.library_scanner_triggers = data_queues["library_scanner_triggers"]
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        if not self.logger:
            unmanic_logging = unlogger.UnmanicLogger.__call__()
            self.logger = unmanic_logging.get_logger(self.name)
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def abort_is_set(self):
        # Check if the abort flag is set
        if self.abort_flag.is_set():
            # Return True straight away if it is
            return True

        # Sleep for a fraction of a second to prevent CPU pinning
        time.sleep(.1)

        # Return False
        return False

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting LibraryScanner Monitor loop")
        while not self.abort_is_set():
            time.sleep(.2)

            # Main loop to configure the scheduler
            if int(self.settings.get_schedule_full_scan_minutes()) != self.interval:
                self.interval = int(self.settings.get_schedule_full_scan_minutes())
            if self.interval and self.interval != 0:
                self._log("Setting LibraryScanner schedule to scan every {} mins...".format(self.interval))
                # Configure schedule
                schedule.every(self.interval).minutes.do(self.scheduled_job)
                # Register application
                self.register_unmanic()

                # First run the task
                if self.settings.get_run_full_scan_on_start() and self.firstrun:
                    self._log("Running LibraryScanner on start")
                    self.scheduled_job()
                self.firstrun = False

                # Then loop and wait for the schedule
                while not self.abort_is_set():
                    # Delay for 1 second before checking again.
                    time.sleep(1)

                    # Check if a manual library scan was triggered
                    try:
                        if not self.library_scanner_triggers.empty():
                            trigger = self.library_scanner_triggers.get_nowait()
                            if trigger == "library_scan":
                                self.scheduled_job()
                                break
                    except queue.Empty:
                        continue
                    except Exception as e:
                        self._log("Exception in retrieving library scanner trigger {}:".format(self.name), message2=str(e),
                                  level="exception")

                    # Check if library scanner is enabled
                    if not self.settings.get_enable_library_scanner():
                        # The library scanner is not enabled. Dont run anything
                        continue

                    # Check if scheduled task is due
                    schedule.run_pending()

                    # If the settings have changed, then break this loop and clear
                    # the scheduled job resetting to the new interval
                    if int(self.settings.get_schedule_full_scan_minutes()) != self.interval:
                        self._log("Resetting LibraryScanner schedule")
                        break
                schedule.clear()

        self._log("Leaving LibraryScanner Monitor loop...")

    def scheduled_job(self):
        from unmanic.libs.plugins import PluginsHandler
        plugin_handler = PluginsHandler()
        incompatible_plugins = plugin_handler.get_incompatible_enabled_plugins(self.data_queues.get('frontend_messages'))
        if incompatible_plugins:
            self._log("Skipping library scanner due incompatible plugins.", level='warning')
            for incompatible_plugin in incompatible_plugins:
                self._log("Found incompatible plugin '{}'".format(incompatible_plugin.get('plugin_id')), level='warning')
            return
        if not plugin_handler.within_enabled_plugin_limits(self.data_queues.get('frontend_messages')):
            return
        self._log("Running full library scan")
        self.scan_library_path(self.settings.get_library_path())

    def add_path_to_queue(self, pathname):
        self.scheduledtasks.put(pathname)

    def scan_library_path(self, search_folder):
        if not os.path.exists(search_folder):
            self._log("Path does not exist - '{}'".format(search_folder), level="warning")
            return
        if self.settings.get_debugging():
            self._log("Scanning directory - '{}'".format(search_folder), level="debug")

        # Push status notification to frontend
        frontend_messages = self.data_queues.get('frontend_messages')

        follow_symlinks = self.settings.get_follow_symlinks()
        for root, subFolders, files in os.walk(search_folder, followlinks=follow_symlinks):
            if self.abort_flag.is_set():
                break
            if self.settings.get_debugging():
                self._log(json.dumps(files, indent=2), level="debug")
            # Add all files in this path that match our container filter
            for file_path in files:
                if self.abort_flag.is_set():
                    break

                # Get full path to file
                pathname = os.path.join(root, file_path)

                frontend_messages.update(
                    {
                        'id':      'libraryScanProgress',
                        'type':    'status',
                        'code':    'libraryScanProgress',
                        'message': pathname,
                        'timeout': 0
                    }
                )

                # Test file to be added to task list. Add it if required
                try:
                    file_test = FileTest(pathname)
                    result, issues = file_test.should_file_be_added_to_task_list()
                    # Log any error messages
                    for issue in issues:
                        if type(issue) is dict:
                            self._log(issue.get('message'))
                        else:
                            self._log(issue)
                    # If file needs to be added, then add it
                    if result:
                        self.add_path_to_queue(pathname)
                except UnicodeEncodeError:
                    self._log("File contains Unicode characters that cannot be processed. Ignoring.", level="warning")
                except Exception as e:
                    self._log("Exception testing file path in {}. Ignoring.".format(self.name), message2=str(e),
                              level="exception")

        # Remove frontend status message
        frontend_messages.remove_item('libraryScanProgress')

    def register_unmanic(self):
        from unmanic.libs import session
        s = session.Session()
        s.register_unmanic()
