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

from peewee import OperationalError

from unmanic import config
from unmanic.libs import common, task
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.plugins import PluginsHandler
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

    def __init__(self, data_queues, task_queue, event):
        super(TaskHandler, self).__init__(name='TaskHandler')
        self.settings = config.Config()
        self.event = event
        self.data_queues = data_queues
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self.task_queue = task_queue
        self.inotifytasks = data_queues["inotifytasks"]
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        # Remove all items from the task list to start with
        self.clear_tasks_on_startup()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self._log("Starting TaskHandler Monitor loop")
        while not self.abort_flag.is_set():
            self.event.wait(2)
            self.process_scheduledtasks_queue()
            self.process_inotifytasks_queue()

        self._log("Leaving TaskHandler Monitor loop...")

    def process_scheduledtasks_queue(self):
        while not self.abort_flag.is_set() and not self.scheduledtasks.empty():
            # Do not sleep at all here. Process this loop as quick as possible
            try:
                item = self.scheduledtasks.get_nowait()
                pathname = item['pathname']
                library_id = item['library_id']
                priority_score = item.get('priority_score', 0)
                if self.add_path_to_task_queue(pathname, library_id, priority_score=priority_score):
                    self._log("Adding file to task queue", pathname, level='info')
                else:
                    self._log("Skipping file as it is already in the queue", pathname, level='info')
            except queue.Empty:
                continue
            except Exception as e:
                self._log("Exception in processing scheduledtasks", str(e), level='exception')

    def process_inotifytasks_queue(self):
        while not self.abort_flag.is_set() and not self.inotifytasks.empty():
            # Do not sleep at all here. Process this loop as quick as possible
            try:
                item = self.inotifytasks.get_nowait()
                pathname = item['pathname']
                library_id = item['library_id']
                priority_score = item.get('priority_score', 0)
                # TODO: Ensure the file is not still being modified at this point.
                #  If it is still being modified here, it is ok to wait for that to finish (should not matter much)
                if self.add_path_to_task_queue(pathname, library_id, priority_score=priority_score):
                    self._log("Adding inotify job to queue", pathname, level='info')
                else:
                    self._log("Skipping inotify job already in the queue", pathname, level='info')
            except queue.Empty:
                continue
            except Exception as e:
                self._log("Exception in processing inotifytasks", str(e), level='exception')

    def clear_tasks_on_startup(self):
        clear_pending = self.settings.get_clear_pending_tasks_on_restart()
        self._log("Starting task cleanup on startup", f"clear_pending_tasks={clear_pending}", level='info')

        try:
            # First, let's see what tasks exist before cleanup
            all_tasks = Tasks.select()
            self._log(f"Tasks before cleanup: total={all_tasks.count()}", level='debug')

            # Log breakdown by status
            for status in ['pending', 'in_progress', 'processed', 'complete']:
                status_count = Tasks.select().where(Tasks.status == status).count()
                self._log(f"  Status '{status}': {status_count} tasks", level='debug')

            # Step 1: Reset in_progress tasks back to pending (worker crashed while processing)
            self._log("Step 1: Resetting in_progress tasks to pending", level='info')
            in_progress_tasks = Tasks.select().where(Tasks.status == 'in_progress')
            if in_progress_tasks.count() > 0:
                self._log(f"Found {in_progress_tasks.count()} in_progress tasks that will be reset to pending", level='warning')
                for task_obj in in_progress_tasks:
                    self._log(f"  Resetting task {task_obj.id}: {task_obj.abspath} (was in_progress)", level='debug')
                    # Reset to pending so it can be picked up again
                    task_obj.status = 'pending'
                    task_obj.processed_by_worker = None  # Clear worker assignment
                    task_obj.save()

            # Step 2: Handle processed tasks based on configuration
            self._log("Step 2: Cleaning processed and remote tasks", level='info')
            delete_query = Tasks.delete()

            if not clear_pending:
                # Delete processed tasks and remote tasks (they don't get reprocessed)
                delete_where_clause = (Tasks.status == 'processed') | (Tasks.type == 'remote')
                delete_query = delete_query.where(delete_where_clause)
                self._log("Task cleanup will DELETE processed and remote tasks", level='warning')
            else:
                # Delete ALL remaining tasks except in_progress (which we just reset)
                delete_where_clause = (Tasks.status != 'in_progress')  # Note: already reset to pending above
                delete_query = delete_query.where(delete_where_clause)
                self._log("Task cleanup will DELETE ALL tasks (clear_pending_tasks is enabled)", level='warning')

            # Get all task IDs to be deleted
            tasks_to_delete = list(Tasks.select(Tasks.id).where(delete_where_clause).tuples())
            if tasks_to_delete:
                self._log(f"Tasks to be deleted: {len(tasks_to_delete)}", level='warning')
                for (task_id,) in tasks_to_delete:
                    try:
                        task_obj = Tasks.get_by_id(task_id)
                        self._log(f"  Deleting task {task_id}: {task_obj.abspath} (status={task_obj.status}, type={task_obj.type})", level='debug')
                    except:
                        pass

                # Remove any task data associated with the tasks
                for (task_id,) in tasks_to_delete:
                    task.TaskDataStore.clear_task(task_id)

                # Delete the tasks
                rows_deleted_count = delete_query.execute()
                self._log(f"Deleted {rows_deleted_count} items from tasks list", level='info')
            else:
                self._log("No tasks marked for deletion", level='debug')

            # Log final state
            all_tasks_after = Tasks.select()
            self._log(f"Tasks after cleanup: total={all_tasks_after.count()}", level='debug')
            for status in ['pending', 'in_progress', 'processed', 'complete']:
                status_count = Tasks.select().where(Tasks.status == status).count()
                self._log(f"  Status '{status}': {status_count} tasks", level='debug')

        except OperationalError as error:
            self._log("Skipping task cleanup at startup; tasks table missing", str(error), level='debug')

    @staticmethod
    def check_if_task_exists_matching_path(abspath):
        """
        Check if a task already exists matching the given path

        :param abspath:
        :return:
        """
        existing_task_query = Tasks.select().where((Tasks.abspath == abspath)).limit(1)
        exists = existing_task_query.count() > 0
        if exists:
            task_obj = existing_task_query.first()
            logger = UnmanicLogging.get_logger(name='TaskHandler')
            logger.debug(f"Task already exists for {abspath} (id={task_obj.id}, status={task_obj.status})")
        return exists

    def add_path_to_task_queue(self, pathname, library_id, priority_score=0):
        """
        Add the path to the task queue ensuring that the path is only added once

        :param pathname:
        :param library_id:
        :param priority_score:
        :return:
        """
        # Check if file exists in task queue based on it's absolute path
        abspath = os.path.abspath(pathname)
        self._log(f"Adding path to task queue", f"abspath={abspath}, library_id={library_id}, priority={priority_score}", level='debug')

        if self.check_if_task_exists_matching_path(abspath):
            self._log(f"Skipping - task already exists", abspath, level='debug')
            return False

        # Create the new task from the provide path
        self._log(f"Creating new task", abspath, level='debug')
        new_task = self.create_task_from_path(pathname, library_id, priority_score=priority_score)
        if not new_task:
            self._log(f"Failed to create task", abspath, level='warning')
            return False

        self._log(f"Successfully created task {new_task.get_task_id()}", abspath, level='info')

        # Execute event plugin runners
        plugin_handler = PluginsHandler()
        plugin_handler.run_event_plugins_for_plugin_type('events.task_queued', {
            'library_id':  library_id,
            'task_id':     new_task.get_task_id(),
            'task_type':   new_task.get_task_type(),
            'source_data': new_task.get_source_data(),
        })

        return True

    def create_task_from_path(self, pathname, library_id, priority_score=0):
        """
        Generate a Task object from a pathname

        :param pathname:
        :param library_id:
        :param priority_score:
        :return:
        """
        abspath = os.path.abspath(pathname)
        # Create a new task
        new_task = task.Task()

        if not new_task.create_task_by_absolute_path(abspath, library_id=library_id, priority_score=priority_score):
            # If file exists in task queue already this will return false.
            # Do not carry on.
            return False

        return new_task
