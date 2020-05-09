#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_taskhandler.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 May 2020, (12:28 PM)

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
import pytest
import time

from tests.support_.test_data import data_queues, mock_config_class, mock_jobqueue_class
from unmanic.libs.taskhandler import TaskHandler


class TestClass(object):
    """
    TestClass

    Test the TaskHandler object

    """

    def setup_class(self):
        """
        Setup the class state for pytest

        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_queues = data_queues.data_queues
        self.scheduledtasks = self.data_queues["scheduledtasks"]
        self.inotifytasks = self.data_queues["inotifytasks"]
        self.progress_reports = self.data_queues["progress_reports"]
        self.settings = mock_config_class.MockConfig()
        self.job_queue = mock_jobqueue_class.MockJobQueue()
        self.task_handler = None

    def teardown_class(self):
        """
        Teardown any state that was previously setup with a call to
        setup_class.

        :return:
        """
        pass

    def setup_method(self):
        """
        Setup any state tied to the execution of the given method in a
        class.
        setup_method is invoked for every test method of a class.

        :return:
        """
        self.task_handler = TaskHandler(self.data_queues, self.settings, self.job_queue)
        self.task_handler.daemon = True
        self.task_handler.start()
        self.job_queue.added_item = None

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        call.

        :return:
        """
        self.task_handler.stop()
        self.task_handler.join()

    @pytest.mark.unittest
    def test_task_handler_runs_as_a_thread(self):
        assert self.task_handler.is_alive()

    @pytest.mark.unittest
    def test_task_handler_thread_can_stop_in_less_than_one_second(self):
        self.task_handler.stop()
        time.sleep(1)
        assert not self.task_handler.is_alive()

    @pytest.mark.unittest
    def test_task_handler_can_process_scheduled_tasks_queue(self):
        test_path_string = 'scheduledtasks'
        self.scheduledtasks.put(test_path_string)
        self.task_handler.process_scheduledtasks_queue()
        assert (test_path_string == self.job_queue.added_item)

    @pytest.mark.unittest
    def test_task_handler_can_process_inotify_tasks_queue(self):
        test_path_string = '/home/josh5/dev/mystuff/unmanic/tests/support_/videos/small/big_buck_bunny_144p_1mb.3gp'
        self.inotifytasks.put(test_path_string)
        self.task_handler.process_inotifytasks_queue()
        assert (test_path_string == self.job_queue.added_item)


if __name__ == '__main__':
    pytest.main(['-s', '--log-cli-level=INFO', __file__])
