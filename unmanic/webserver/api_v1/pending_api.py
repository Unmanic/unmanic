#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.pending_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     26 Oct 2020, (2:26 PM)

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
import time
import tornado.web
import tornado.log
import tornado.routing

from unmanic import config
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler

from unmanic.libs import task, common


class ApiPendingHandler(BaseApiHandler):
    name = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "supported_methods": ["POST"],
            "call_method":       "create_task_from_path",
            "path_pattern":      r"/api/v1/pending/add/",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "manage_pending_tasks_list",
            "path_pattern":      r"/api/v1/pending/list",
        },
        {
            "supported_methods": ["GET"],
            "call_method":       "trigger_library_rescan",
            "path_pattern":      r"/api/v1/pending/rescan",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'pending_api'
        self.config = config.CONFIG()

        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def get(self, path):
        self.action_route()

    def post(self, path):
        self.action_route()

    def manage_pending_tasks_list(self, *args, **kwargs):
        request_dict = json.loads(self.request.body)

        # Delete a list of tasks.
        #   (on success will continue to return the current list of tasks)
        if request_dict.get("customActionName") == "remove-from-task-list":
            if not self.delete_pending_tasks(request_dict.get("id")):
                self.write(json.dumps({"success": False}))
                return

        # Move a list of tasks to the top of the queue
        if request_dict.get("customActionName") == "move-to-top-of-task-list":
            if not self.reorder_pending_tasks(request_dict.get("id"), "top"):
                self.write(json.dumps({"success": False}))
                return

        # Move a list of tasks to the top of the queue
        if request_dict.get("customActionName") == "move-to-bottom-of-task-list":
            if not self.reorder_pending_tasks(request_dict.get("id"), "bottom"):
                self.write(json.dumps({"success": False}))
                return

        # Return a list of tasks based on the request JSON body
        results = self.prepare_filtered_pending_tasks(request_dict)
        self.write(json.dumps(results))

    def trigger_library_rescan(self):
        """
        Adds a trigger ('library_scan') to the library_scanner_triggers
        data queue.
        This data queue is read by the LibraryScanner service which will
        then execute a library scan.

        :return:
        """
        # Handle request to manually trigger a rescan of the library
        # Check if we are able to start up a worker for another encoding job
        library_scanner_triggers = self.unmanic_data_queues.get('library_scanner_triggers')
        if library_scanner_triggers.full():
            self.write(json.dumps({"success": False}))
            return
        else:
            library_scanner_triggers.put('library_scan')
            self.write(json.dumps({"success": True}))
            return

    def delete_pending_tasks(self, pending_task_ids):
        """
        Deletes a list of pending tasks

        :param pending_task_ids:
        :return:
        """
        # Fetch tasks
        task_handler = task.Task(self.unmanic_data_queues.get('logging').get_logger("UIServer"))
        # Delete by ID
        return task_handler.delete_tasks_recursively(id_list=pending_task_ids)

    def reorder_pending_tasks(self, pending_task_ids, direction="top"):
        """
        Moves a list of pending tasks to either the top of the
        list of bottom depending on the provided direction.

        :param pending_task_ids:
        :param direction:
        :return:
        """
        # Fetch tasks
        task_handler = task.Task(self.unmanic_data_queues.get('logging').get_logger("UIServer"))

        return task_handler.reorder_tasks(pending_task_ids, direction)

    def add_tasks_to_pending_tasks_list(self, *args, **kwargs):
        """
        TODO: Add the given list of tasks to the pending task list

        :param args:
        :param kwargs:
        :return:
        """
        pass

    def create_task_from_path(self, *args, **kwargs):
        """
        Generate a Task object from a pathname

        :param pathname:
        :return:
        """
        request_dict = json.loads(self.request.body)

        # Fetch the abspath name
        abspath = os.path.abspath(request_dict.get("path"))

        # Ensure path exists
        if not os.path.exists(abspath):
            self.write(json.dumps({"success": False}))
            return

        # Create a new task
        new_task = task.Task(tornado.log.app_log)

        # Run a probe on the file for current data
        source_data = common.fetch_file_data_by_path(abspath)

        if not new_task.create_task_by_absolute_path(abspath, self.config, source_data):
            # If file exists in task queue already this will return false.
            # Do not carry on.
            self.write(json.dumps({"success": False}))
            return

        self.write(json.dumps({"success": True}))

    def prepare_filtered_pending_tasks(self, request_dict):
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
        task_handler = task.Task(self.unmanic_data_queues.get('logging').get_logger("UIServer"))
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
            "draw":         draw,
            "recordsTotal": records_total_count,
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
