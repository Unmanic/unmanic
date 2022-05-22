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
import os

from unmanic.libs import task
from unmanic.libs.library import Library


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


def prepare_filtered_pending_tasks(params, include_library=False):
    """
    Returns a object of records filtered and sorted
    according to the provided request.

    :param params:
    :param include_library:
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
            'type':     pending_task['type'],
            'status':   pending_task['status'],
        }
        if include_library:
            # Get library
            library = Library(pending_task['library_id'])
            item['library_id'] = library.get_id()
            item['library_name'] = library.get_name()
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


def add_remote_tasks(pathname):
    """
    Adds an upload file path to the pending task list as a 'remote' task
    Returns the task ID

    :param pathname:
    :return:
    """
    abspath = os.path.abspath(pathname)

    # Create a new task
    new_task = task.Task()

    if not new_task.create_task_by_absolute_path(abspath, task_type='remote'):
        # File was not created.
        # Do not carry on.
        return False
    return new_task.get_task_data()


def update_pending_tasks_status(pending_task_ids, status='pending'):
    """
    Updates the status of a number pending tasks given their table IDs

    :param pending_task_ids:
    :param status:
    :return:
    """
    # Update tasks
    return task.Task.set_tasks_status(pending_task_ids, status)


def update_pending_tasks_library(pending_task_ids, library_name):
    """
    Updates the status of a number pending tasks given their table IDs

    :param pending_task_ids:
    :param library_name:
    :return:
    """
    # Fetch Library ID by it's name
    library_id = None
    libraries = Library.get_all_libraries()
    for library in libraries:
        if library.get('name') == library_name:
            library_id = library.get('id')
            break
    # Ensure a library was found matching the name
    if library_id is None:
        return False
    # Update the tasks
    return task.Task.set_tasks_library_id(pending_task_ids, library_id)


def fetch_tasks_status(pending_task_ids):
    """
    Fetch the status of a number of pending remote tasks given their table IDs

    :param pending_task_ids:
    :return:
    """
    # Fetch tasks
    task_handler = task.Task()
    remote_pending_tasks = task_handler.get_task_list_filtered_and_sorted(id_list=pending_task_ids)

    # Iterate over tasks and append them to the task data
    return_data = []
    for pending_task in remote_pending_tasks:
        # Set params as required in template
        item = {
            'id':       pending_task['id'],
            'abspath':  pending_task['abspath'],
            'priority': pending_task['priority'],
            'type':     pending_task['type'],
            'status':   pending_task['status'],
        }
        return_data.append(item)
    return return_data


def check_if_task_exists_matching_path(abspath):
    from unmanic.libs.taskhandler import TaskHandler
    if TaskHandler.check_if_task_exists_matching_path(abspath):
        return True
    return False


def create_task(abspath, library_id=1, library_name=None, task_type='local', priority_score=0):
    """
    Create a pending task given the path to a file and a library ID or name

    :param abspath:
    :param library_id:
    :param library_name:
    :param task_type:
    :param priority_score:
    :return:
    """
    if library_name is not None:
        for library in Library.get_all_libraries():
            if library_name == library.get('name'):
                library_id = library.get('id')

    # Ensure the library provided exists (prevents errors as the task library_id column is not a foreign key
    library = Library(library_id)

    # Create a new task
    new_task = task.Task()

    # Create the task as a local task as the path provided is local
    if not new_task.create_task_by_absolute_path(abspath, task_type=task_type, library_id=library.get_id(),
                                                 priority_score=priority_score):
        # File was not created.
        # Do not carry on.
        return False

    # Return task info (same as the data returned in a file upload
    task_info = new_task.get_task_data()
    return {
        "id":         task_info.get('id'),
        "abspath":    task_info.get('abspath'),
        "priority":   task_info.get('priority'),
        "type":       task_info.get('type'),
        "status":     task_info.get('status'),
        "library_id": task_info.get('library_id'),
    }
