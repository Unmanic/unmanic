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
from datetime import date, datetime

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
    status = params.get('status', 'all')

    order = params.get('order', {
        "column": 'finish_time',
        "dir":    'desc',
    })

    # Define filters
    task_success = None
    if status == 'success':
        task_success = True
    elif status == 'failed':
        task_success = False

    after_time = None
    if params.get('after'):
        after_time = datetime.strptime(params.get('after'), '%Y-%m-%dT%H:%M:%S').timestamp()

    before_time = None
    if params.get('before'):
        before_time = datetime.strptime(params.get('before'), '%Y-%m-%dT%H:%M:%S').timestamp()

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
                                                                                        search_value=search_value,
                                                                                        task_success=task_success,
                                                                                        after_time=after_time,
                                                                                        before_time=before_time).count()
    # Get filtered/sorted results
    task_results = history_logging.get_historic_task_list_filtered_and_sorted(order=order, start=start, length=length,
                                                                              search_value=search_value,
                                                                              task_success=task_success, after_time=after_time,
                                                                              before_time=before_time)

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


def add_historic_tasks_to_pending_tasks_list(historic_task_ids, library_id=None):
    """
    Adds a list of historical tasks to the pending tasks list.

    :param historic_task_ids:
    :param library_id:
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

        if not new_task.create_task_by_absolute_path(abspath, library_id=library_id):
            # If file exists in task queue already this will return false.
            # Do not carry on.
            errors[record.get("id")] = "File already in task queue - '{}'".format(abspath)

        continue
    return errors


def read_command_log_for_task(task_id):
    data = {
        'command_log':       '',
        'command_log_lines': [],
    }
    task_handler = history.History()
    task_data = task_handler.get_historic_task_data_dictionary(task_id=task_id)
    if not task_data:
        return data

    for command_log in task_data.get('completedtaskscommandlogs_set', []):
        data['command_log'] += command_log['dump']
        data['command_log_lines'] += format_ffmpeg_log_text(command_log['dump'].split("\n"))

    return data


def format_ffmpeg_log_text(log_lines):
    return_list = []
    pre_text = False
    headers = ['RUNNER:', 'COMMAND:', 'LOG:', 'WORKER TERMINATED!', 'PLUGIN FAILED!', 'REMOTE TASK FAILED!',
               'REMOTE LINK MANAGER TERMINATED!']
    for i, line in enumerate(log_lines):
        line_text = line

        # Add PRE to lines
        if line_text and pre_text and line_text.rstrip() not in headers:
            line_text = '<pre>{}</pre>'.format(line_text)

        # Add bold to headers
        if line_text.rstrip() not in headers:
            line_text = line_text
        else:
            if line_text.rstrip() in ['WORKER TERMINATED!', 'PLUGIN FAILED!', 'REMOTE TASK FAILED!',
                                      'REMOTE LINK MANAGER TERMINATED!']:
                line_text = '<b><span class="terminated">{}</span></b>'.format(line_text)
            else:
                line_text = '<b>{}</b>'.format(line_text)

        # Replace leading whitespace
        stripped = line.lstrip()
        line_text = "&nbsp;" * (len(line) - len(stripped)) + line_text

        # If log section is COMMAND:
        if 'RUNNER:' in line_text:
            # prepend a horizontal rule
            return_list.append("<hr>")
            pre_text = False
        elif 'COMMAND:' in line_text:
            pre_text = True
        elif 'LOG:' in line_text:
            pre_text = False
        return_list.append(line_text)
    return return_list
