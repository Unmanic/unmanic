#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.pending_tasks.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Jul 2021, (6:27 PM)

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

from unmanic.libs import task


def prepare_filtered_pending_tasks_for_table(request_dict):
    """
    Returns a object of records filtered and sorted
    according to the provided request.

    :param request_dict:
    :return:
    """

    # Generate filters for query
    draw = request_dict.get('draw')
    start = request_dict.get('start')
    length = request_dict.get('length')

    search = request_dict.get('search')
    search_value = search.get("value")

    # Force sort order always by ID desc
    order = {
        "column": 'priority',
        "dir":    'desc',
    }

    # Fetch tasks
    task_handler = task.Task()
    # Get total count
    records_total_count = task_handler.get_total_task_list_count()
    # Get quantity after filters (without pagination)
    records_filtered_count = task_handler.get_task_list_filtered_and_sorted(order=order, start=0, length=0,
                                                                            search_value=search_value,
                                                                            status='pending').count()
    # Get filtered/sorted results
    pending_task_results = task_handler.get_task_list_filtered_and_sorted(order=order, start=start, length=length,
                                                                          search_value=search_value, status='pending')

    # Build return data
    return_data = {
        "draw":            draw,
        "recordsTotal":    records_total_count,
        "recordsFiltered": records_filtered_count,
        "successCount":    0,
        "failedCount":     0,
        "data":            []
    }

    # Iterate over tasks and append them to the task data
    for pending_task in pending_task_results:
        # Set params as required in template
        item = {
            'id':       pending_task['id'],
            'selected': False,
            'abspath':  pending_task['abspath'],
            'status':   pending_task['status'],
        }
        return_data["data"].append(item)

    # Return results
    return return_data


def prepare_filtered_pending_tasks(params):
    """
    Returns a object of records filtered and sorted
    according to the provided request.

    :param params:
    :return:
    """
    start = params.get('start', 0)
    length = params.get('length', 0)

    search_value = params.get('search_value', '')

    order = params.get('order', {
        "column": 'priority',
        "dir":    'desc',
    })

    # Fetch tasks
    task_handler = task.Task()
    # Get total count
    records_total_count = task_handler.get_total_task_list_count()
    # Get quantity after filters (without pagination)
    records_filtered_count = task_handler.get_task_list_filtered_and_sorted(order=order, start=0, length=0,
                                                                            search_value=search_value,
                                                                            status='pending').count()
    # Get filtered/sorted results
    pending_task_results = task_handler.get_task_list_filtered_and_sorted(order=order, start=start, length=length,
                                                                          search_value=search_value, status='pending')

    # Build return data
    return_data = {
        "recordsTotal":    records_total_count,
        "recordsFiltered": records_filtered_count,
        "results":         []
    }

    # Iterate over tasks and append them to the task data
    for pending_task in pending_task_results:
        # Set params as required in template
        item = {
            'id':       pending_task['id'],
            'abspath':  pending_task['abspath'],
            'priority': pending_task['priority'],
            'status':   pending_task['status'],
        }
        return_data["results"].append(item)

    # Return results
    return return_data


def remove_pending_tasks(pending_task_ids):
    """
    Removes a list of pending tasks

    :param pending_task_ids:
    :return:
    """
    # Delete by ID
    task_handler = task.Task()
    return task_handler.delete_tasks_recursively(id_list=pending_task_ids)


def reorder_pending_tasks(pending_task_ids, direction="top"):
    """
    Moves a list of pending tasks to either the top of the
    list of bottom depending on the provided direction.

    :param pending_task_ids:
    :param direction:
    :return:
    """
    # Fetch tasks
    task_handler = task.Task()

    return task_handler.reorder_tasks(pending_task_ids, direction)
