#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.api_history_handler.py

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
import time
import tornado.web
import tornado.log

from unmanic.libs import history


class ApiHistoryHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["GET", "POST"]
    name = None
    config = None

    def initialize(self, **kwargs):
        self.name = 'api'
        self.config = kwargs.get("settings")

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def post(self, path):
        request_dict = json.loads(self.request.body)
        results = self.fetch_filtered_historic_tasks(request_dict)
        self.write(json.dumps(results))

    def fetch_filtered_historic_tasks(self, request_dict):
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
        order = {
            "column": filter_order.get('column'),
            "dir":    filter_order.get('dir'),
        }
        for column in request_dict.get('columns'):
            column_name = column.get("name")
            if column_name == order["column"]:
                order["column"] = column.get("data")

        # Fetch historical tasks
        history_logging = history.History(self.config)
        # Get total count
        records_total_count = history_logging.get_total_historic_task_list_count()
        # Get quantity after filters (without pagination)
        records_filtered_count = history_logging.get_historic_task_list_filtered_and_sorted(0, 0, order, search_value).count()
        # Get filtered/sorted results
        task_results = history_logging.get_historic_task_list_filtered_and_sorted(start, length, order, search_value)
        tornado.log.app_log.warning(search, exc_info=True)

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
