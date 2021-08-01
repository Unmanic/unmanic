#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.completed_tasks.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     24 Jul 2021, (9:34 AM)

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
import time

from unmanic.libs import common, history, task


def prepare_filtered_completed_tasks(params):
    """
    Returns a object of historical records filtered and sorted
    according to the provided request.

    :param params:
    :return:
    """
    start = params.get('start', 0)
    length = params.get('length', 0)
    search_value = params.get('search_value', '')

    # Force sort order always by ID desc
    order = params.get('order', {
        "column": 'finish_time',
        "dir":    'desc',
    })

    # Fetch historical tasks
    history_logging = history.History()
    # Get total count
    records_total_count = history_logging.get_total_historic_task_list_count()
    # Get total success count
    records_total_success_count = history_logging.get_historic_task_list_filtered_and_sorted(task_success=True).count()
    # Get total failed count
    records_total_failed_count = history_logging.get_historic_task_list_filtered_and_sorted(task_success=False).count()
    # Get quantity after filters (without pagination)
    records_filtered_count = history_logging.get_historic_task_list_filtered_and_sorted(order=order, start=0, length=0,
                                                                                        search_value=search_value).count()
    # Get filtered/sorted results
    task_results = history_logging.get_historic_task_list_filtered_and_sorted(order=order, start=start, length=length,
                                                                              search_value=search_value)

    # Build return data
    return_data = {
        "recordsTotal":    records_total_count,
        "recordsFiltered": records_filtered_count,
        "successCount":    records_total_success_count,
        "failedCount":     records_total_failed_count,
        "results":         []
    }

    # Iterate over tasks and append them to the task data
    for task in task_results:
        # Set params as required in template
        item = {
            'id':           task['id'],
            'task_label':   task['task_label'],
            'task_success': task['task_success'],
            'finish_time':  task['finish_time'],
        }
        return_data["results"].append(item)

    # Return results
    return return_data


def remove_completed_tasks(completed_task_ids):
    """
    Removes a list of completed tasks

    :param completed_task_ids:
    :return:
    """
    # Delete by ID
    task_handler = history.History()
    return task_handler.delete_historic_tasks_recursively(id_list=completed_task_ids)


def add_historic_tasks_to_pending_tasks_list(historic_task_ids, config):
    """
    Adds a list of historical tasks to the pending tasks list.

    :param historic_task_ids:
    :param config:
    :return:
    """
    errors = {}
    # Fetch historical tasks
    history_logging = history.History()
    # Get total count
    records_by_id = history_logging.get_current_path_of_historic_tasks_by_id(id_list=historic_task_ids)
    for record in records_by_id:
        record_errors = []
        # Fetch the abspath name
        abspath = os.path.abspath(record.get("abspath"))

        # Ensure path exists
        if not os.path.exists(abspath):
            errors[record.get("id")] = "Path does not exist - '{}'".format(abspath)
            continue

        # Create a new task
        new_task = task.Task()

        # Run a probe on the file for current data
        source_data = common.fetch_file_data_by_path(abspath)

        if not new_task.create_task_by_absolute_path(abspath, config, source_data):
            # If file exists in task queue already this will return false.
            # Do not carry on.
            errors[record.get("id")] = "File already in task queue - '{}'".format(abspath)

        continue
    return errors
