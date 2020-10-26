#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.taskhandler.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 May 2020, (12:22 PM)

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

from unmanic.libs import common, ffmpeg, task
from unmanic.libs.unffmpeg import Info, containers
from unmanic.libs.unmodels.tasks import Tasks


class TaskHandler(threading.Thread):
    """
    TaskHandler

    The TaskHandler reads all items in the queues and passes them to the appropriate locations in the application.
        TODO:
            - All tasks are added to the database tasks table (no key to historical tasks.
                Row to be deleted once task is added to historical record)
            - Task Handler to monitor idle workers rather than idle workers looking for tasks in the TaskQueue object.
                - When a worker thread is idle, the TaskHandler needs to read a select query on the database and add that
                    item to the TaskQueue
            - Workers should request a job from the TaskHandler rather than reading the TaskQueue directly ??
            -
    """

    def __init__(self, data_queues, settings, task_queue):
        super(TaskHandler, self).__init__(name='TaskHandler')
        self.settings = settings
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.task_queue = task_queue
        self.inotifytasks = data_queues["inotifytasks"]
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        # Remove all items from the task list to start with
        self.delete_all_tasks()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self._log("Starting TaskHandler Monitor loop")
        while not self.abort_flag.is_set():
            self.process_scheduledtasks_queue()
            self.process_inotifytasks_queue()
            time.sleep(.2)

        self._log("Leaving TaskHandler Monitor loop...")

    def process_scheduledtasks_queue(self):
        while not self.abort_flag.is_set() and not self.scheduledtasks.empty():
            try:
                pathname = self.scheduledtasks.get_nowait()
                if self.add_path_to_task_queue(pathname):
                    self._log("Adding file to task queue", pathname, level='info')
                else:
                    self._log("Skipping file as it is already in the queue", pathname, level='info')
            except queue.Empty:
                continue
            except Exception as e:
                self._log("Exception in processing scheduledtasks", str(e), level='exception')

    def process_inotifytasks_queue(self):
        while not self.abort_flag.is_set() and not self.inotifytasks.empty():
            try:
                pathname = self.inotifytasks.get_nowait()
                # TODO: Ensure the file is not still being modified at this point.
                #  If it is still being modified here, it is ok to wait for that to finish (should not matter much)
                if self.add_path_to_task_queue(pathname):
                    self._log("Adding inotify job to queue", pathname, level='info')
                else:
                    self._log("Skipping inotify job already in the queue", pathname, level='info')
            except queue.Empty:
                continue
            except Exception as e:
                self._log("Exception in processing inotifytasks", str(e), level='exception')

    def delete_all_tasks(self):
        rows_deleted_count = Tasks.delete().execute()
        self._log("Deleted {} items from tasks list".format(rows_deleted_count), level='debug')

    def add_path_to_task_queue(self, pathname):
        # Check if file exists in task queue based on it's absolute path
        abspath = os.path.abspath(pathname)
        existing_task_query = Tasks.select().where((Tasks.abspath == abspath)).limit(1)
        if existing_task_query.count() > 0:
            return False
        # Create the new task from the provide path
        new_task = self.create_task_from_path(pathname)
        if not new_task:
            return False
        return True

    def create_task_from_path(self, pathname):
        """
        Generate a Task object from a pathname

        :param pathname:
        :return:
        """
        abspath = os.path.abspath(pathname)
        # Create a new task
        new_task = task.Task(self.data_queues["logging"].get_logger("Task"))

        source_data = common.fetch_file_data_by_path(pathname)

        if not new_task.create_task_by_absolute_path(abspath, self.settings, source_data):
            # If file exists in task queue already this will return false.
            # Do not carry on.
            return False

        return new_task
