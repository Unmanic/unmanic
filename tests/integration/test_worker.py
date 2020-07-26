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

try:
    from unmanic.libs import unlogger, foreman, task
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import unlogger, foreman, task


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
        # import config
        from unmanic import config
        self.settings = config.CONFIG(os.path.join(tempfile.mkdtemp(), 'unmanic_test.db'))
        self.settings.DEBUGGING = True

        # Create our test queues
        self.data_queues = {
            "progress_reports": queue.Queue(),
            "logging":          self.logging
        }
        self.task_queue = queue.Queue(maxsize=1)
        self.complete_queue = queue.Queue()

    def setup_test_task(self, pathname):
        # Create a new task and set the source
        self.test_task = task.Task(self.data_queues)
        self.test_task.set_source_data(pathname)
        destination_data = task.prepare_file_destination_data(os.path.abspath(pathname), self.settings.OUT_CONTAINER)
        self.test_task.set_destination_data(destination_data)
        self.test_task.set_cache_path()

    def completed_test_task_is_success(self):
        assert self.completed_test_task.success

    def completed_test_task_data_has_source_abspath(self):
        task_data = self.completed_test_task.__dict__.copy()
        assert 'abspath' in task_data['source']

    def completed_test_task_data_has_source_basename(self):
        task_data = self.completed_test_task.__dict__.copy()
        assert 'basename' in task_data['source']

    def completed_test_task_data_has_source_dirname(self):
        task_data = self.completed_test_task.__dict__.copy()
        assert 'dirname' in task_data['source']

    def completed_test_task_data_has_source_video_codecs(self):
        task_data = self.completed_test_task.__dict__.copy()
        assert 'video_codecs' in task_data['source']

    def completed_test_task_data_has_file_in_probe(self):
        task_data = self.completed_test_task.__dict__.copy()
        assert 'streams' in task_data['ffmpeg'].file_in['file_probe']

    @pytest.mark.integrationtest
    def test_worker_tread_for_conversion_success(self):
        worker_id = 'test'
        worker_thread = foreman.WorkerThread(worker_id, "Foreman-{}".format(worker_id), self.settings, self.data_queues,
                                            self.task_queue, self.complete_queue)
        # Test 2 of the small files
        count = 0
        for video_file in os.listdir(os.path.join(self.tests_videos_dir, 'small')):
            # Create test task
            self.setup_test_task(os.path.join(self.tests_videos_dir, 'small', video_file))
            worker_thread.set_current_task(self.test_task)
            worker_thread.process_task_queue_item()
            # Ensure the completed task was added to the completed queue
            assert not self.complete_queue.empty()
            # Retrieve this task and add it to the global completed_test_task variable
            self.completed_test_task = self.complete_queue.get_nowait()
            # Ensure task was successfully processed
            self.completed_test_task_is_success()
            # Ensure task data has source abspath
            self.completed_test_task_data_has_source_abspath()
            # Ensure task data has source basename
            self.completed_test_task_data_has_source_basename()
            # Ensure task data has source dirname
            self.completed_test_task_data_has_source_dirname()
            # Ensure task data has source video_codecs list
            self.completed_test_task_data_has_source_video_codecs()
            # Ensure task data has source video in file probe data
            self.completed_test_task_data_has_file_in_probe()
            count += 1
            if count >= 2:
                break
