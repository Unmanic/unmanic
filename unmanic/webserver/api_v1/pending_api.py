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
import time
import tornado.web
import tornado.log
import tornado.routing

from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler

from unmanic.libs import task, common


class ApiPendingHandler(BaseApiHandler):
    SUPPORTED_METHODS = ["GET", "POST"]
    name = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "method":       "add_tasks_to_pending_tasks_list",
            "path_pattern": r"/api/v1/pending/add/",
        },
        {
            "method":       "manage_pending_tasks_list",
            "path_pattern": r"/api/v1/pending/list",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'pending_api'
        self.config = kwargs.get("settings")
        self.unmanic_data_queues = kwargs.get("unmanic_data_queues")
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def post(self, path):
        self.action_route()

    def manage_pending_tasks_list(self, *args, **kwargs):
        request_dict = json.loads(self.request.body)

        # Delete a list of historical tasks.
        #   (on success will continue to return the current list of historical tasks)
        if request_dict.get("customActionName") == "remove-from-task-list":
            success = self.delete_pending_tasks(request_dict.get("id"))
            if not success:
                self.write(json.dumps({"success": False}))
                return

        # Return a list of historical tasks based on the request JSON body
        results = self.prepare_filtered_pending_tasks(request_dict)
        self.write(json.dumps(results))

    def delete_pending_tasks(self, pending_task_ids):
        """
        Deletes a list of pending tasks

        :param pending_task_ids:
        :return:
        """
        # Fetch tasks
        task_handler = task.Task(self.config)
        # Delete by ID
        return task_handler.delete_tasks_recursively(id_list=pending_task_ids)

    def add_tasks_to_pending_tasks_list(self, *args, **kwargs):
        """
        TODO: Add the given list of tasks to the pending task list

        :param args:
        :param kwargs:
        :return:
        """
        pass

    def create_task_from_path(self, pathname):
        """
        TODO: Generate a Task object from a pathname

        :param pathname:
        :return:
        """
        pass

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
            "column": 'id',
            "dir":    'desc',
        }

        # Fetch tasks
        task_handler = task.Task(self.config)
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
