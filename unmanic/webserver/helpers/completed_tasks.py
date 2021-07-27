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
import time

from unmanic.libs import history


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
        "successCount":    records_filtered_count,
        "failedCount":     records_filtered_count,
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

        # Increment counters
        if task['task_success']:
            return_data["successCount"] += 1
        else:
            return_data["failedCount"] += 1

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
