#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.task.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     27 Apr 2019, (2:08 PM)
 
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
import shutil
import time
from operator import attrgetter

from playhouse.shortcuts import model_to_dict

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.library import Library
from unmanic.libs.unmodels.tasks import IntegrityError, Tasks


def prepare_file_destination_data(pathname, file_extension):
    basename = os.path.basename(pathname)
    dirname = os.path.dirname(os.path.abspath(pathname))
    # Fetch the file's name without the file extension (this is going to be reset)
    file_name_without_extension = os.path.splitext(basename)[0]

    # Set destination dict
    basename = "{}.{}".format(file_name_without_extension, file_extension)
    abspath = os.path.join(dirname, basename)
    file_data = {
        'basename': basename,
        'abspath':  abspath
    }

    return file_data


class Task(object):
    """
    Task

    Contains the stage and all data pertaining to a transcode task

    """

    def __init__(self):
        self.name = 'Task'
        self.task = None
        self.task_dict = None
        self.settings = config.Config()
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)
        self.statistics = {}
        self.errors = []

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def set_cache_path(self, cache_directory=None, file_extension=None):
        if not self.task:
            raise Exception('Unable to set cache path. Task has not been set!')
        # Fetch the file's name without the file extension (this is going to be reset)
        split_file_name = os.path.splitext(self.get_source_basename())
        file_name_without_extension = split_file_name[0]

        if not file_extension:
            # Get file extension
            file_extension = split_file_name[1].lstrip('.')

        # Parse an output cache path
        random_string = '{}-{}'.format(common.random_string(), int(time.time()))
        out_file = "{}-{}.{}".format(file_name_without_extension, random_string, file_extension)
        if not cache_directory:
            out_folder = "unmanic_file_conversion-{}".format(random_string)
            cache_directory = os.path.join(self.settings.get_cache_path(), out_folder)

        # Set cache path class attribute
        self.task.cache_path = os.path.join(cache_directory, out_file)

    def get_cache_path(self):
        if not self.task:
            raise Exception('Unable to fetch cache path. Task has not been set!')
        if not self.task.cache_path:
            raise Exception('Unable to fetch cache path. Task cache path has not been set!')
        return self.task.cache_path

    def get_task_data(self):
        if not self.task:
            raise Exception('Unable to fetch task dictionary. Task has not been set!')
        self.task_dict = model_to_dict(self.task, backrefs=True)
        return self.task_dict

    def get_task_id(self):
        if not self.task:
            raise Exception('Unable to fetch task ID. Task has not been set!')
        return self.task.id

    def get_task_type(self):
        if not self.task:
            raise Exception('Unable to fetch task type. Task has not been set!')
        return self.task.type

    def get_task_library_id(self):
        if not self.task:
            raise Exception('Unable to fetch task library ID. Task has not been set!')
        return self.task.library_id

    def get_task_library_name(self):
        if not self.task:
            raise Exception('Unable to fetch task library ID. Task has not been set!')
        library = Library(self.task.library_id)
        return library.get_name()

    def get_task_library_priority_score(self):
        if not self.task:
            raise Exception('Unable to fetch task library ID. Task has not been set!')
        library = Library(self.task.library_id)
        return library.get_priority_score()

    def get_destination_data(self):
        if not self.task:
            raise Exception('Unable to fetch destination data. Task has not been set!')

        cache_path = self.get_cache_path()

        # Get the current cache path's file extension
        split_file_name = os.path.splitext(os.path.basename(cache_path))
        file_extension = split_file_name[1].lstrip('.')

        return prepare_file_destination_data(self.task.abspath, file_extension)

    def get_source_data(self):
        if not self.task:
            raise Exception('Unable to fetch source absolute path. Task has not been set!')
        if not self.task.abspath:
            raise Exception('Unable to fetch source absolute path. Task absolute path has not been set!')
        return {
            'abspath':  self.task.abspath,
            'basename': os.path.basename(self.task.abspath),
        }

    def get_source_basename(self):
        return self.get_source_data().get('basename')

    def get_source_abspath(self):
        return self.get_source_data().get('abspath')

    def task_dump(self):
        # Generate a copy of this class as a dict
        task_dict = {
            'task_label':          self.get_source_basename(),
            'abspath':             self.get_source_abspath(),
            'task_success':        self.task.success,
            'start_time':          self.task.start_time,
            'finish_time':         self.task.finish_time,
            'processed_by_worker': self.task.processed_by_worker,
            'errors':              self.errors,
            'log':                 self.task.log,
        }
        return task_dict

    def read_and_set_task_by_absolute_path(self, abspath):
        """
        Sets the task by it's absolute path.
        If the task already exists in the list, then return that task.
        If the task does not yet exist in the list, create it first.

        :param abspath:
        :return:
        """
        # Get task matching the abspath
        self.task = Tasks.get(abspath=abspath)

    def create_task_by_absolute_path(self, abspath, task_type='local', library_id=1, priority_score=0):
        """
        Creates the task by it's absolute path.
        If the task already exists in the list, then this will throw an exception and return false

        Calls to read_and_set_task_by_absolute_path() to read back all data out of the database.

        :param abspath:
        :param task_type:
        :param library_id:
        :param priority_score:
        :return:
        """
        try:
            self.task = Tasks.create(abspath=abspath, status='creating', library_id=library_id)
            self.save()
            self._log("Created new task with ID: {} for {}".format(self.task, abspath), level="debug")

            # Set the cache path to use during the transcoding
            self.set_cache_path()

            # Fetch the library priority score also for this task
            library_priority_score = self.get_task_library_priority_score()

            # Set the default priority to the ID of the task
            self.task.priority = int(self.task.id) + int(library_priority_score) + int(priority_score)

            # Set the task type
            self.task.type = task_type

            # Only local tasks should be progressed automatically
            # Remote tasks need to be progressed to pending by a remote trigger
            if task_type == 'local':
                # Now set the status to pending. Only then will it be picked up by a worker.
                # This will also save the task.
                self.set_status('pending')
            else:
                # Save the tasks updates without settings status to pending
                self.save()

            return True
        except IntegrityError as e:
            self._log("Cancel creating new task for {} - {}".format(abspath, e), level="info")
            return False

    def set_status(self, status):
        """
        Sets the task status to either 'pending', 'in_progress', 'processed' or 'complete'

        :param status:
        :return:
        """
        allowed = ['pending', 'in_progress', 'processed', 'complete']
        if status not in allowed:
            raise Exception('Unable to set status to "{}". Status must be one of [{}].'.format(status, ', '.join(allowed)))
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        self.task.status = status
        self.save()

    def set_success(self, success):
        """
        Sets the task success flag to either 'true' or 'false'

        :param success:
        :return:
        """
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        if success:
            self.task.success = True
        else:
            self.task.success = False
        self.save()

    def modify_path(self, new_path):
        """
        Modifies the abspath attribute of this task

        :param new_path:
        :return:
        """
        if not self.task:
            raise Exception('Unable to update abspath. Task has not been set!')
        self.task.abspath = new_path
        self.save()

    def save_command_log(self, log):
        """
        Sets the task command log

        :param log:
        :return:
        """
        if not self.task:
            raise Exception('Unable to set status. Task has not been set!')
        self.task.log += ''.join(log)
        self.save()

    def save(self):
        """
        Save task model object

        :return:
        """
        if not self.task:
            raise Exception('Unable to save Task. Task has not been set!')
        self.task.save()

    def delete(self):
        """
        Delete a task model object

        :return:
        """
        if not self.task:
            raise Exception('Unable to save Task. Task has not been set!')
        self.task.delete_instance()

    def get_total_task_list_count(self):
        task_query = Tasks.select().order_by(Tasks.id.desc())
        return task_query.count()

    def get_task_list_filtered_and_sorted(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                          status=None, task_type=None):
        try:
            query = (Tasks.select())

            if id_list:
                query = query.where(Tasks.id.in_(id_list))

            if search_value:
                query = query.where(Tasks.abspath.contains(search_value))

            if status:
                query = query.where(Tasks.status.in_([status]))

            if task_type:
                query = query.where(Tasks.type.in_([task_type]))

            # Get order by
            order_by = None
            if order:
                if order.get("dir") == "asc":
                    order_by = attrgetter(order.get("column"))(Tasks).asc()
                else:
                    order_by = attrgetter(order.get("column"))(Tasks).desc()

            if order_by and length:
                query = query.order_by(order_by).limit(length).offset(start)

        except Tasks.DoesNotExist:
            # No task entries exist yet
            self._log("No tasks exist yet.", level="warning")
            query = []

        return query.dicts()

    def delete_tasks_recursively(self, id_list):
        """
        Deletes a given list of tasks based on their IDs

        :param id_list:
        :return:
        """
        # Prevent running if no list of IDs was given
        if not id_list:
            return False

        try:
            query = (Tasks.select())

            if id_list:
                query = query.where(Tasks.id.in_(id_list))

            for task_id in query:
                try:
                    # Remote tasks need to be cleaned up from the cache partition also
                    if task_id.type == 'remote':
                        remote_task_dirname = task_id.abspath
                        if os.path.exists(task_id.abspath) and "unmanic_remote_pending_library" in remote_task_dirname:
                            self._log("Removing remote pending library task '{}'.".format(remote_task_dirname))
                            shutil.rmtree(os.path.dirname(remote_task_dirname))

                    task_id.delete_instance(recursive=True)
                except Exception as e:
                    # Catch delete exceptions
                    self._log("An error occurred while deleting task ID: {}.".format(task_id), str(e), level="exception")
                    return False

            return True

        except Tasks.DoesNotExist:
            # No task entries exist yet
            self._log("No tasks currently exist.", level="warning")

    def reorder_tasks(self, id_list, direction):
        # Get the task with the highest ID
        order = {
            "column": 'priority',
            "dir":    'desc',
        }
        pending_task_results = self.get_task_list_filtered_and_sorted(order=order, start=0, length=1,
                                                                      search_value=None, id_list=None, status=None)

        task_top_priority = 1
        for pending_task_result in pending_task_results:
            task_top_priority = pending_task_result.get('priority')
            break

        # Add 500 to that number to offset it above all others.
        new_priority_offset = (int(task_top_priority) + 500)

        # Update the list of tasks by ID from the database adding the priority offset to their current priority
        # If the direction is to send it to the bottom, then set the priority as 0
        query = Tasks.update(priority=Tasks.priority + new_priority_offset if (direction == "top") else 0).where(
            Tasks.id.in_(id_list))
        return query.execute()

    @staticmethod
    def set_tasks_status(id_list, status):
        """
        Updates the task status for a given list of tasks by ID

        :param id_list:
        :param status:
        :return:
        """
        query = Tasks.update(status=status).where(Tasks.id.in_(id_list))
        return query.execute()

    @staticmethod
    def set_tasks_library_id(id_list, library_id):
        """
        Updates the task library_id for a given list of tasks by ID

        :param id_list:
        :param library_id:
        :return:
        """
        query = Tasks.update(library_id=library_id).where(Tasks.id.in_(id_list))
        return query.execute()
