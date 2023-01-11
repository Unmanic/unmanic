#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.filetest.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     28 Mar 2021, (7:28 PM)

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
from copy import deepcopy

from unmanic import config
from unmanic.libs import history, common, unlogger
from unmanic.libs.plugins import PluginsHandler


class FileTest(object):
    """
    FileTest

    Object to manage tests carried out on files discovered
    during a library scan or inode event

    """

    def __init__(self, library_id: int):
        self.settings = config.Config()
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

        # Init plugins
        self.library_id = library_id
        self.plugin_handler = PluginsHandler()
        self.plugin_modules = self.plugin_handler.get_enabled_plugin_modules_by_type('library_management.file_test',
                                                                                     library_id=library_id)

        # List of filed tasks
        self.failed_paths = []

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def set_file(self):
        pass

    def file_failed_in_history(self, path):
        """
        Check if file has already failed in history

        :return:
        """
        # Fetch historical tasks
        history_logging = history.History()
        if not self.failed_paths:
            failed_tasks = history_logging.get_historic_tasks_list_with_source_probe(task_success=False)
            for task in failed_tasks:
                self.failed_paths.append(task.get('abspath'))
        if path in self.failed_paths:
            # That pathname was found in the results of failed historic tasks
            return True
        # No results were found matching that pathname
        return False

    def file_in_unmanic_ignore_lockfile(self, path):
        """
        Check if folder contains a '.unmanicignore' lockfile

        :return:
        """
        # Get file parent directory
        dirname = os.path.dirname(path)
        # Check if lockfile (.unmanicignore) exists
        unmanic_ignore_file = os.path.join(dirname, '.unmanicignore')
        if os.path.exists(unmanic_ignore_file):
            # Get file basename
            basename = os.path.basename(path)
            # Read the file and check for any entry with this file name
            with open(unmanic_ignore_file) as f:
                for line in f:
                    if basename in line:
                        return True
        return False

    def should_file_be_added_to_task_list(self, path):
        """
        Test if this file needs to be added to the task list

        :return:
        """
        return_value = None
        file_issues = []

        # TODO: Remove this
        if self.file_in_unmanic_ignore_lockfile(path):
            file_issues.append({
                'id':      'unmanicignore',
                'message': "File found in unmanic ignore file - '{}'".format(path),
            })
            return_value = False

        # Check if file has failed in history.
        if self.file_failed_in_history(path):
            file_issues.append({
                'id':      'blacklisted',
                'message': "File found already failed in history - '{}'".format(path),
            })
            return_value = False

        # Only run checks with plugins if other tests were not conclusive
        priority_score_modification = 0
        if return_value is None:
            # Set the initial data with just the priority score.
            data = {
                'priority_score': 0,
                'shared_info':    {},
            }
            # Run tests against plugins
            for plugin_module in self.plugin_modules:
                data['library_id'] = self.library_id
                data['path'] = path
                data['issues'] = deepcopy(file_issues)
                data['add_file_to_pending_tasks'] = None

                # Run plugin to update data
                if not self.plugin_handler.exec_plugin_runner(data, plugin_module.get('plugin_id'),
                                                              'library_management.file_test'):
                    continue

                # Append any file issues found during previous tests
                file_issues = data.get('issues')

                # Set the return_value based on the plugin results
                # If the add_file_to_pending_tasks returned an answer (True/False) then break the loop.
                # No need to continue.
                if data.get('add_file_to_pending_tasks') is not None:
                    return_value = data.get('add_file_to_pending_tasks')
                    break
            # Set the priority score modification
            priority_score_modification = data.get('priority_score', 0)

        return return_value, file_issues, priority_score_modification


class FileTesterThread(threading.Thread):
    def __init__(self, name, files_to_test, files_to_process, status_updates, library_id, event):
        super(FileTesterThread, self).__init__(name=name)
        self.settings = config.Config()
        self.logger = None
        self.event = event
        self.files_to_test = files_to_test
        self.files_to_process = files_to_process
        self.library_id = library_id
        self.status_updates = status_updates
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
        self._log("Starting {}".format(self.name))
        file_test = FileTest(self.library_id)
        while not self.abort_flag.is_set():
            try:
                # Pending task queue has an item available. Fetch it.
                next_file = self.files_to_test.get_nowait()
                self.status_updates.put(next_file)
            except queue.Empty:
                self.event.wait(2)
                continue
            except Exception as e:
                self._log("Exception in fetching library scan result for path {}:".format(self.name), message2=str(e),
                            level="exception")

            # Test file to be added to task list. Add it if required
            try:
                result, issues, priority_score = file_test.should_file_be_added_to_task_list(next_file)
                # Log any error messages
                for issue in issues:
                    if type(issue) is dict:
                        self._log(issue.get('message'))
                    else:
                        self._log(issue)
                # If file needs to be added, then add it
                if result:
                    self.add_path_to_queue({
                        'path':           next_file,
                        'priority_score': priority_score,
                    })
            except UnicodeEncodeError:
                self._log("File contains Unicode characters that cannot be processed. Ignoring.", level="warning")
            except Exception as e:
                self._log("Exception testing file path in {}. Ignoring.".format(self.name), message2=str(e),
                            level="exception")

        self._log("Exiting {}".format(self.name))

    def add_path_to_queue(self, item):
        self.files_to_process.put(item)
