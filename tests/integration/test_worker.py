#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_worker.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 Sep 2019, (9:55 AM)
 
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
import sys
import tempfile

import pytest

from unmanic.libs.unmodels import Settings, Tasks, TaskProbe, TaskProbeStreams, Plugins, PluginFlow, Installation

try:
    from unmanic.libs import unlogger, foreman, task, taskhandler, workers
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import unlogger, foreman, task, taskhandler


class TestClass(object):
    """
    TestClass

    Runs unit tests against the Foreman and Worker Thread classes

    """
    project_dir = None
    settings = None
    logging = None
    logger = None
    worker_threads = None
    test_task = None
    data_queues = None
    task_queue = None
    complete_queue = None
    completed_test_task = None

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.tests_videos_dir = os.path.join(self.project_dir, 'tests', 'support_', 'videos')
        self.tests_tmp_dir = os.path.join(self.project_dir, 'tests', 'tmp', 'py_test_env')
        # sys.path.append(self.project_dir)
        self.logging = unlogger.UnmanicLogger.__call__(False)
        self.logging.get_logger()

        # Create temp config path
        config_path = tempfile.mkdtemp(prefix='unmanic_tests_')

        # Create connection to a test DB
        from unmanic.libs import unmodels
        app_dir = os.path.dirname(os.path.abspath(__file__))
        database_settings = {
            "TYPE":           "SQLITE",
            "FILE":           os.path.join(config_path, 'unmanic.db'),
            "MIGRATIONS_DIR": os.path.join(app_dir, 'migrations'),
        }
        from unmanic.libs.unmodels.lib import Database
        self.db_connection = Database.select_database(database_settings)

        # Create required tables
        self.db_connection.create_tables([Settings, Tasks, TaskSettings, TaskProbe, TaskProbeStreams, Plugins, PluginFlow, Installation])

        # import config
        from unmanic import config
        self.settings = config.Config(config_path=config_path)
        self.settings.set_config_item('debugging', True, save_settings=False)

        # Create our test queues
        self.data_queues = {
            "progress_reports": queue.Queue(),
            "logging":          self.logging
        }
        self.task_queue = queue.Queue(maxsize=1)
        self.complete_queue = queue.Queue()

    def setup_test_task(self, pathname):
        # Create a new task and set the source
        self.test_task = task.Task()

        # Fill test_task with data
        self.test_task.create_task_by_absolute_path(os.path.abspath(pathname), self.settings)

        # Get container extension
        split_file_name = os.path.splitext(os.path.basename(pathname))
        container_extension = split_file_name[1].lstrip('.')

        destination_data = task.prepare_file_destination_data(os.path.abspath(pathname), container_extension)
        self.test_task.set_destination_data(destination_data)
        self.test_task.set_cache_path()

    def completed_test_task_is_success(self):
        completed_test_task_dump = self.completed_test_task.task_dump()
        assert completed_test_task_dump['task_success']

    def completed_test_task_data_has_source_abspath(self):
        completed_test_task_dump = self.completed_test_task.task_dump()
        file_probe_data = completed_test_task_dump['file_probe_data']
        assert 'abspath' in file_probe_data['source']

    def completed_test_task_data_has_source_basename(self):
        completed_test_task_dump = self.completed_test_task.task_dump()
        file_probe_data = completed_test_task_dump['file_probe_data']
        assert 'basename' in file_probe_data['source']

    def completed_test_task_data_has_destination_file_path(self):
        completed_test_task_dump = self.completed_test_task.task_dump()
        assert 'abspath' in completed_test_task_dump['destination']
