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

from unmanic import config
from unmanic.libs import history, common, unlogger
from unmanic.libs.plugins import PluginsHandler


class FileTest(object):
    """
    FileTest

    Object to manage tests carried out on files discovered
    during a library scan or inode event

    """

    def __init__(self, path):
        self.settings = config.Config()
        self.path = path
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def file_failed_in_history(self):
        """
        Check if file has already failed in history

        :return:
        """
        # Fetch historical tasks
        history_logging = history.History()
        task_results = history_logging.get_historic_tasks_list_with_source_probe(abspath=self.path, task_success=False)
        if not task_results:
            # No results were found matching that pathname
            return False
        # That pathname was found in the results of failed historic tasks
        return True

    def file_in_unmanic_ignore_lockfile(self):
        """
        Check if folder contains a '.unmanicignore' lockfile

        :return:
        """
        # Get file basename
        basename = os.path.basename(self.path)
        # Get file parent directory
        dirname = os.path.dirname(self.path)
        # Check if lockfile (.unmanicignore) exists
        unmanic_ignore_file = os.path.join(dirname, '.unmanicignore')
        if os.path.exists(unmanic_ignore_file):
            # Read the file and check for any entry with this file name
            with open(unmanic_ignore_file) as f:
                for line in f:
                    if basename in line:
                        return True
        return False

    def should_file_be_added_to_task_list(self):
        """
        Test if this file needs to be added to the task list

        :return:
        """
        return_value = None
        file_issues = []

        # Init plugins
        plugin_handler = PluginsHandler()
        plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type('library_management.file_test')

        # TODO: Remove this
        if self.file_in_unmanic_ignore_lockfile():
            file_issues.append({
                'id':      'unmanicignore',
                'message': "File found in unmanic ignore file - '{}'".format(self.path),
            })
            return_value = False

        # Check if file has failed in history.
        if self.file_failed_in_history():
            file_issues.append({
                'id':      'blacklisted',
                'message': "File found already failed in history - '{}'".format(self.path),
            })
            return_value = False

        # Only run checks with plugins if other tests were not conclusive
        if return_value is None:
            # Run tests against plugins
            for plugin_module in plugin_modules:
                data = {
                    'path':                      self.path,
                    'issues':                    file_issues.copy(),
                    'add_file_to_pending_tasks': None,
                }

                # Run plugin to update data
                if not plugin_handler.exec_plugin_runner(data, plugin_module.get('plugin_id'), 'library_management.file_test'):
                    continue

                # Append any file issues found during previous tests
                file_issues = data.get('issues')

                # Set the return_value based on the plugin results
                # If the add_file_to_pending_tasks returned an answer (True/False) then break the loop.
                # No need to continue.
                if data.get('add_file_to_pending_tasks') is not None:
                    return_value = data.get('add_file_to_pending_tasks')
                    break

        return return_value, file_issues
