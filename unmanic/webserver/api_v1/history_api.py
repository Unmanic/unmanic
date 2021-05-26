#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Oct 2020, (8:49 PM)

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
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler

from unmanic.libs import history, task, common


class ApiHistoryHandler(BaseApiHandler):
    name = None
    config = None
    params = None

    routes = [
        {
            "supported_methods": ["GET", "POST"],
            "call_method":       "fetch_by_id",
            "path_pattern":      r"/api/v1/history/id/(?P<id>[0-9]+)?",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "manage_historic_tasks_list",
            "path_pattern":      r"/api/v1/history/list",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'history_api'
        self.config = config.CONFIG()
        self.params = kwargs.get("params")

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def post(self, path):
        self.action_route()

    def fetch_by_id(self, *args, **kwargs):
        # TODO: add ability to fetch by id
        pass

    def manage_historic_tasks_list(self, *args, **kwargs):
        request_dict = json.loads(self.request.body)

        # Return a list of historical tasks to the pending task list.
        #   (on success will continue to return the current list of historical tasks)
        if request_dict.get("customActionName") == "add-to-pending":
            success = self.add_historic_tasks_to_pending_tasks_list(request_dict.get("id"))
            if not success:
                self.write(json.dumps({"success": False}))
                return

        # Delete a list of historical tasks.
        #   (on success will continue to return the current list of historical tasks)
        if request_dict.get("customActionName") == "delete-from-history":
            success = self.delete_historic_tasks(request_dict.get("id"))
            if not success:
                self.write(json.dumps({"success": False}))
                return

        # Return a list of historical tasks based on the request JSON body
        results = self.prepare_filtered_historic_tasks(request_dict)
        self.write(json.dumps(results))

    def delete_historic_tasks(self, historic_task_ids):
        """
        Deletes a list of historic tasks

        :param historic_task_ids:
        :return:
        """
        # Fetch historical tasks
        history_logging = history.History(self.config)
        # Delete by ID
        return history_logging.delete_historic_tasks_recursively(id_list=historic_task_ids)

    def add_historic_tasks_to_pending_tasks_list(self, historic_task_ids):
        """
        Adds a list of historical tasks to the pending tasks list.

        :param historic_task_ids:
        :return:
        """
        success = True
        # Fetch historical tasks
        history_logging = history.History(self.config)
        # Get total count
        records_by_id = history_logging.get_current_path_of_historic_tasks_by_id(id_list=historic_task_ids)
        # records_by_id = history_logging.get_historic_task_list_filtered_and_sorted(id_list=historic_task_ids)
        for record in records_by_id:
            # Fetch the abspath name
            abspath = os.path.abspath(record.get("abspath"))

            # Ensure path exists
            if not os.path.exists(abspath):
                success = False
                continue

            # Create a new task
            new_task = task.Task(tornado.log.app_log)

            # Run a probe on the file for current data
            source_data = common.fetch_file_data_by_path(abspath)

            if not new_task.create_task_by_absolute_path(abspath, self.config, source_data):
                # If file exists in task queue already this will return false.
                # Do not carry on.
                success = False

            continue
        return success

    def prepare_filtered_historic_tasks(self, request_dict):
        """
        Returns a object of historical records filtered and sorted
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

        # Get sort order
        filter_order = request_dict.get('order')[0]
        order_direction = filter_order.get('dir')
        columns = request_dict.get('columns')
        order_column_name = columns[filter_order.get('column')].get('name')
        order = {
            "column": order_column_name,
            "dir":    order_direction,
        }

        # Fetch historical tasks
        history_logging = history.History(self.config)
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
            "draw":            draw,
            "recordsTotal":    records_total_count,
            "recordsFiltered": records_filtered_count,
            "successCount":    0,
            "failedCount":     0,
            "data":            []
        }

        # Iterate over historical tasks and append them to the task data
        for task in task_results:
            # Set params as required in template
            item = {
                'id':           task['id'],
                'selected':     False,
                'finish_time':  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task['finish_time'])),
                'task_label':   task['task_label'],
                'task_success': task['task_success'],
            }
            # Increment counters
            if item['task_success']:
                return_data["successCount"] += 1
            else:
                return_data["failedCount"] += 1
            return_data["data"].append(item)

        # Return results
        return return_data
