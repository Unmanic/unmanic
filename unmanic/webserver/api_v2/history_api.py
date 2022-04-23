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

from unmanic import config
from unmanic.libs import session
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiError, BaseApiHandler
from unmanic.webserver.api_v2.schema.schemas import CompletedTasksLogRequestSchema, CompletedTasksLogSchema, \
    CompletedTasksSchema, \
    RequestHistoryTableDataSchema, \
    RequestAddCompletedToPendingTasksSchema, RequestTableUpdateByIdList
from unmanic.webserver.helpers import completed_tasks


class ApiHistoryHandler(BaseApiHandler):
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
        },
        {
            "path_pattern":      r"/history/reprocess",
            "supported_methods": ["POST"],
            "call_method":       "add_completed_tasks_to_pending_list",
        },
        {
            "path_pattern":      r"/history/task/log",
            "supported_methods": ["POST"],
            "call_method":       "get_completed_task_log",
        }
    ]

    def initialize(self, **kwargs):
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()
        self.config = config.Config()

    def get_completed_tasks(self):
        """
        History - list tasks
        ---
        description: Returns a list of completed tasks.
        requestBody:
            description: Returns a list of completed tasks.
            required: True
            content:
                application/json:
                    schema:
                        RequestHistoryTableDataSchema
        responses:
            200:
                description: 'Sample response: Returns a list of completed tasks.'
                content:
                    application/json:
                        schema:
                            CompletedTasksSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestHistoryTableDataSchema())

            params = {
                'start':        json_request.get('start'),
                'length':       json_request.get('length'),
                'search_value': json_request.get('search_value'),
                'status':       json_request.get('status'),
                'after':        json_request.get('after'),
                'before':       json_request.get('before'),
                'order':        {
                    "column": json_request.get('order_by', 'finish_time'),
                    "dir":    json_request.get('order_direction', 'desc'),
                }
            }
            task_list = completed_tasks.prepare_filtered_completed_tasks(params)

            response = self.build_response(
                CompletedTasksSchema(),
                {
                    "recordsTotal":    task_list.get('recordsTotal'),
                    "recordsFiltered": task_list.get('recordsFiltered'),
                    "successCount":    task_list.get('successCount'),
                    "failedCount":     task_list.get('failedCount'),
                    "results":         task_list.get('results'),
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def delete_completed_tasks(self):
        """
        History - delete
        ---
        description: Delete a list of completed tasks.
        requestBody:
            description: Requested list of items to delete.
            required: True
            content:
                application/json:
                    schema:
                        RequestTableUpdateByIdList
        responses:
            200:
                description: 'Successful request; Returns success status'
                content:
                    application/json:
                        schema:
                            BaseSuccessSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestTableUpdateByIdList())

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

    def add_completed_tasks_to_pending_list(self):
        """
        History - reprocess
        ---
        description: Add a list of completed tasks back to the Pending Tasks queue.
        requestBody:
            description: Requested list of items to reprocess.
            required: True
            content:
                application/json:
                    schema:
                        RequestAddCompletedToPendingTasksSchema
        responses:
            200:
                description: 'Successful request; Returns success status'
                content:
                    application/json:
                        schema:
                            BaseSuccessSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestAddCompletedToPendingTasksSchema())
            id_list = json_request.get('id_list', [])
            library_id = json_request.get('library_id')

            errors = completed_tasks.add_historic_tasks_to_pending_tasks_list(id_list, library_id=library_id)
            if errors:
                failed_ids = ''
                for task_id in errors:
                    failed_ids += " {}".format(task_id)
                    tornado.log.app_log.error(
                        "ApiHistoryHandler.{}: {}".format(self.route.get('call_method'), errors.get(task_id)))
                self.set_status(self.STATUS_ERROR_INTERNAL,
                                reason="Failed to add the provided completed tasks to the pending task list: '{}'".format(
                                    failed_ids))
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

    def get_completed_task_log(self):
        """
        History - details
        ---
        description: Request the details of a completed task.
        requestBody:
            description: Requested the details of a completed task.
            required: True
            content:
                application/json:
                    schema:
                        CompletedTasksLogRequestSchema
        responses:
            200:
                description: 'Success: The details of a requested completed task.'
                content:
                    application/json:
                        schema:
                            CompletedTasksLogSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(CompletedTasksLogRequestSchema())

            command_log = completed_tasks.read_command_log_for_task(json_request.get('task_id'))

            response = self.build_response(
                CompletedTasksLogSchema(),
                {
                    'command_log':       command_log.get('command_log', ''),
                    'command_log_lines': command_log.get('command_log_lines', []),
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
