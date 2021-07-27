#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     24 Jul 2021, (9:31 AM)

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

import tornado.log

from unmanic.libs import session
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiError, BaseApiHandler
from unmanic.webserver.helpers import completed_tasks


class ApiHistoryHandler(BaseApiHandler):
    name = None
    session = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/history/tasks",
            "supported_methods": ["POST"],
            "call_method":       "get_completed_tasks",
        },
        {
            "path_pattern":      r"/history/tasks",
            "supported_methods": ["DELETE"],
            "call_method":       "delete_completed_tasks",
            "parameters":        [
                {
                    "key":      "id_list",
                    "required": True,
                }
            ],
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'session_api'
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def get_completed_tasks(self, *args, **kwargs):
        try:
            json_request = self.read_json_request()

            params = {
                'start':        json_request.get('start', '0'),
                'length':       json_request.get('length', '10'),
                'search_value': json_request.get('search_value', ''),
                'order':        {
                    "column": json_request.get('order_by', 'finish_time'),
                    "dir":    json_request.get('order_direction', 'desc'),
                }
            }
            task_list = completed_tasks.prepare_filtered_completed_tasks(params)

            self.write_success({
                "recordsTotal":    task_list.get('recordsTotal'),
                "recordsFiltered": task_list.get('recordsFiltered'),
                "successCount":    task_list.get('successCount'),
                "failedCount":     task_list.get('failedCount'),
                "results":         task_list.get('results'),
            })
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def delete_completed_tasks(self, *args, **kwargs):
        try:
            json_request = self.read_json_request()

            if not completed_tasks.remove_completed_tasks(json_request.get('id_list', [])):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to delete the completed tasks by their IDs")
                self.write_error()
                return

            self.write_success()
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
