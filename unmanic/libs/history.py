#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Jun 2019, (10:42 AM)
 
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
import json
from operator import attrgetter

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.unmodels import CompletedTasks, CompletedTasksCommandLogs

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class History(object):
    """
    History

    Record statistical data for historical jobs
    """

    def __init__(self):
        self.name = 'History'
        self.settings = config.Config()

    def _log(self, message, message2='', level="info"):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(self.name)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.name))

    def get_historic_task_list(self, limit=None):
        """
        Read all historic tasks entries

        :return:
        """
        try:
            # Fetch a single row (get() will raise DoesNotExist exception if no results are found)
            if limit:
                historic_tasks = CompletedTasks.select().order_by(CompletedTasks.id.desc()).limit(limit)
            else:
                historic_tasks = CompletedTasks.select().order_by(CompletedTasks.id.desc())
        except CompletedTasks.DoesNotExist:
            # No historic entries exist yet
            self._log("No historic tasks exist yet.", level="warning")
            historic_tasks = []

        return historic_tasks.dicts()

    def get_total_historic_task_list_count(self):
        query = CompletedTasks.select().order_by(CompletedTasks.id.desc())
        return query.count()

    def get_historic_task_list_filtered_and_sorted(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                                   task_success=None, after_time=None, before_time=None):
        try:
            query = (CompletedTasks.select())

            if id_list:
                query = query.where(CompletedTasks.id.in_(id_list))

            if search_value:
                query = query.where(CompletedTasks.task_label.contains(search_value))

            if task_success is not None:
                query = query.where(CompletedTasks.task_success.in_([task_success]))

            if after_time is not None:
                query = query.where(CompletedTasks.finish_time >= after_time)

            if before_time is not None:
                query = query.where(CompletedTasks.finish_time <= before_time)

            # Get order by
            if order:
                if order.get("dir") == "asc":
                    order_by = attrgetter(order.get("column"))(CompletedTasks).asc()
                else:
                    order_by = attrgetter(order.get("column"))(CompletedTasks).desc()

                query = query.order_by(order_by)

            if length:
                query = query.limit(length).offset(start)

        except CompletedTasks.DoesNotExist:
            # No historic entries exist yet
            self._log("No historic tasks exist yet.", level="warning")
            query = []

        return query.dicts()

    def get_current_path_of_historic_tasks_by_id(self, id_list=None):
        """
        Returns a list of CompletedTasks filtered by id_list and joined with the current absolute path of that file.
        For failures this will be the the source path
        For success, this will be the destination path

        :param id_list:
        :return:
        """
        """
            SELECT
                t1.*,
                t2.type,
                t2.abspath
            FROM completedtasks AS "t1"
            WHERE t1.id IN ( %s)
        """
        query = (
            CompletedTasks.select(CompletedTasks.id, CompletedTasks.task_label, CompletedTasks.task_success,
                                  CompletedTasks.abspath)
        )

        if id_list:
            query = query.where(CompletedTasks.id.in_(id_list))

        return query.dicts()

    def get_historic_tasks_list_with_source_probe(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                                  task_success=None, abspath=None):
        """
        Return a list of matching historic tasks with their source file's ffmpeg probe.

        :param order:
        :param start:
        :param length:
        :param search_value:
        :param id_list:
        :param task_success:
        :param abspath:
        :return:
        """
        query = (
            CompletedTasks.select(CompletedTasks.id, CompletedTasks.task_label, CompletedTasks.task_success,
                                  CompletedTasks.abspath))

        if id_list:
            query = query.where(CompletedTasks.id.in_(id_list))

        if search_value:
            query = query.where(CompletedTasks.task_label.contains(search_value))

        if task_success is not None:
            query = query.where(CompletedTasks.task_success.in_([task_success]))

        if abspath:
            query = query.where(CompletedTasks.abspath.in_([abspath]))

        return query.dicts()

    def get_historic_task_data_dictionary(self, task_id):
        """
        Read all data for a task and return a dictionary of that data

        :return:
        """
        # Get historic task matching the id
        try:
            # Fetch the historic task (get() will raise DoesNotExist exception if no results are found)
            historic_tasks = CompletedTasks.get_by_id(task_id)
        except CompletedTasks.DoesNotExist:
            self._log("Failed to retrieve historic task from database for id {}.".format(task_id), level="exception")
            return False
        # Get all saved data for this task and create dictionary of task data
        historic_task = historic_tasks.model_to_dict()
        # Return task data dictionary
        return historic_task

    def delete_historic_tasks_recursively(self, id_list=None):
        """
        Deletes a given list of historic tasks based on their IDs

        :param id_list:
        :return:
        """
        # Prevent running if no list of IDs was given
        if not id_list:
            return False

        try:
            query = (CompletedTasks.select())

            if id_list:
                query = query.where(CompletedTasks.id.in_(id_list))

            for historic_task_id in query:
                try:
                    historic_task_id.delete_instance(recursive=True)
                except Exception as e:
                    # Catch delete exceptions
                    self._log("An error occurred while deleting historic task ID: {}.".format(historic_task_id), str(e),
                              level="exception")
                    return False

            return True

        except CompletedTasks.DoesNotExist:
            # No historic entries exist yet
            self._log("No historic tasks exist yet.", level="warning")

    def save_task_history(self, task_data):
        """
        Record a task's data and state to the database.

        :param task_data:
        :return:
        """
        try:
            # Create the new historical task entry
            new_historic_task = self.create_historic_task_entry(task_data)
            # Create an entry of the data from the source ffprobe
            self.create_historic_task_ffmpeg_log_entry(new_historic_task, task_data.get('log', ''))
        except Exception as error:
            self._log("Failed to save historic task entry to database.", str(error), level="exception")
            return False
        return True

    @staticmethod
    def create_historic_task_ffmpeg_log_entry(historic_task, log):
        """
        Create an entry of the stdout log from the ffmpeg command

        :param historic_task:
        :param log:
        :return:
        """
        CompletedTasksCommandLogs.create(
            completedtask_id=historic_task,
            dump=log
        )

    def create_historic_task_entry(self, task_data):
        """
        Create a historic task entry

        Required task_data params:
            - task_label
            - task_success
            - start_time
            - finish_time
            - processed_by_worker

        :param task_data:
        :return:
        """
        if not task_data:
            self._log('Task data param empty', json.dumps(task_data), level="debug")
            raise Exception('Task data param empty. This should not happen - Something has gone really wrong.')

        new_historic_task = CompletedTasks.create(task_label=task_data['task_label'],
                                                  abspath=task_data['abspath'],
                                                  task_success=task_data['task_success'],
                                                  start_time=task_data['start_time'],
                                                  finish_time=task_data['finish_time'],
                                                  processed_by_worker=task_data['processed_by_worker'])
        return new_historic_task
