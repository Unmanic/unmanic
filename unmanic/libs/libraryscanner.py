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
        self.scheduler = schedule.Scheduler()

        self.results_manager_threads = {}
        self.files_to_test = queue.Queue()

    def _log(self, message, message2='', level="info"):
        if not self.logger:
            unmanic_logging = unlogger.UnmanicLogger.__call__()
            self.logger = unmanic_logging.get_logger(self.name)
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()
        # Stop all child threads
        self.stop_all_results_manager_threads()

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
                self.scheduler.every(self.interval).minutes.do(self.scheduled_job)
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
                    self.scheduler.run_pending()

                    # If the settings have changed, then break this loop and clear
                    # the scheduled job resetting to the new interval
                    if int(self.settings.get_schedule_full_scan_minutes()) != self.interval:
                        self._log("Resetting LibraryScanner schedule")
                        break
                self.scheduler.clear()

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

    def start_results_manager_thread(self, thread_id, frontend_messages):
        thread = LibraryScanThread("LibraryScanThread-{}".format(thread_id), self.files_to_test,
                                   self.scheduledtasks, frontend_messages)
        thread.daemon = True
        thread.start()
        self.results_manager_threads[thread_id] = thread

    def stop_all_results_manager_threads(self):
        for thread_id in self.results_manager_threads:
            self.results_manager_threads[thread_id].abort_flag.set()

    def scan_library_path(self, search_folder):
        if not os.path.exists(search_folder):
            self._log("Path does not exist - '{}'".format(search_folder), level="warning")
            return
        if self.settings.get_debugging():
            self._log("Scanning directory - '{}'".format(search_folder), level="debug")

        # Push status notification to frontend
        frontend_messages = self.data_queues.get('frontend_messages')

        # Start X number of LibraryScanThread threads (2)
        for results_manager_id in range(2):
            self.start_results_manager_thread(results_manager_id, frontend_messages)

        start_time = time.time()

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

                # Place file's full path in queue to be tested
                self.files_to_test.put(os.path.join(root, file_path))

        # Loop while waiting for all treads to finish
        while not self.abort_is_set():
            # Check if all files have been tested
            if self.files_to_test.empty():
                # There are not more files to test. Mark manager threads as completed
                self.stop_all_results_manager_threads()
                break

        # Wait for threads to finish and
        for thread_id in self.results_manager_threads:
            self.results_manager_threads[thread_id].abort_flag.set()
            self.results_manager_threads[thread_id].join(2)
        self.results_manager_threads = {}

        self._log("Library scan completed in {} seconds".format((time.time() - start_time)), level="warning")

        # Remove frontend status message
        frontend_messages.remove_item('libraryScanProgress')

    def register_unmanic(self):
        from unmanic.libs import session
        s = session.Session()
        s.register_unmanic()


class LibraryScanThread(threading.Thread):
    def __init__(self, name, files_to_test, scheduledtasks, frontend_messages):
        super(LibraryScanThread, self).__init__(name=name)
        self.settings = config.Config()
        self.logger = None
        self.files_to_test = files_to_test
        self.scheduledtasks = scheduledtasks
        self.frontend_messages = frontend_messages
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

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting {}".format(self.name))
        file_test = FileTest()
        while not self.abort_flag.is_set():
            try:
                # Pending task queue has an item available. Fetch it.
                next_file = self.files_to_test.get_nowait()

                self.frontend_messages.update(
                    {
                        'id':      'libraryScanProgress',
                        'type':    'status',
                        'code':    'libraryScanProgress',
                        'message': next_file,
                        'timeout': 0
                    }
                )

                # Test file to be added to task list. Add it if required
                try:
                    result, issues = file_test.should_file_be_added_to_task_list(next_file)
                    # Log any error messages
                    for issue in issues:
                        if type(issue) is dict:
                            self._log(issue.get('message'))
                        else:
                            self._log(issue)
                    # If file needs to be added, then add it
                    if result:
                        self.add_path_to_queue(next_file)
                except UnicodeEncodeError:
                    self._log("File contains Unicode characters that cannot be processed. Ignoring.", level="warning")
                except Exception as e:
                    self._log("Exception testing file path in {}. Ignoring.".format(self.name), message2=str(e),
                              level="exception")
            except queue.Empty:
                time.sleep(.1)
                continue
            except Exception as e:
                self._log("Exception in checking library scan results with {}:".format(self.name), message2=str(e),
                          level="exception")
        self._log("Exiting {}".format(self.name))

    def add_path_to_queue(self, pathname):
        self.scheduledtasks.put(pathname)
