#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.pending_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Jul 2021, (10:16 AM)

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
import os.path

import tornado.log
from unmanic.libs import session
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiHandler, BaseApiError
from unmanic.webserver.api_v2.schema.schemas import RequestPendingTasksReorderSchema, PendingTasksSchema, \
    RequestPendingTableDataSchema, RequestTableUpdateByIdList, TaskDownloadLinkSchema
from unmanic.webserver.downloads import DownloadsLinks
from unmanic.webserver.helpers import pending_tasks


class ApiPendingHandler(BaseApiHandler):
    session = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/pending/tasks",
            "supported_methods": ["POST"],
            "call_method":       "get_pending_tasks",
        },
        {
            "path_pattern":      r"/pending/tasks",
            "supported_methods": ["DELETE"],
            "call_method":       "delete_pending_tasks",
        },
        {
            "path_pattern":      r"/pending/reorder",
            "supported_methods": ["POST"],
            "call_method":       "reorder_pending_tasks",
        },
        {
            "path_pattern":      r"/pending/status/get",
            "supported_methods": ["POST"],
            "call_method":       "get_pending_status_of_tasks",
        },
        {
            "path_pattern":      r"/pending/status/set/ready",
            "supported_methods": ["POST"],
            "call_method":       "set_pending_status_as_ready",
        },
        {
            "path_pattern":      r"/pending/download/file/id/(?P<task_id>[0-9]+)?",
            "supported_methods": ["GET"],
            "call_method":       "gen_download_link_pending_task_file",
        },
        {
            "path_pattern":      r"/pending/download/data/id/(?P<task_id>[0-9]+)?",
            "supported_methods": ["GET"],
            "call_method":       "gen_download_link_pending_task_data",
        },

    ]

    def initialize(self, **kwargs):
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def get_pending_tasks(self):
        """
        Pending - list tasks
        ---
        description: Returns a list of pending tasks.
        requestBody:
            description: Returns a list of pending tasks.
            required: True
            content:
                application/json:
                    schema:
                        RequestPendingTableDataSchema
        responses:
            200:
                description: 'Sample response: Returns a list of pending tasks.'
                content:
                    application/json:
                        schema:
                            PendingTasksSchema
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
            json_request = self.read_json_request(RequestPendingTableDataSchema())

            params = {
                'start':        json_request.get('start', '0'),
                'length':       json_request.get('length', '10'),
                'search_value': json_request.get('search_value', ''),
                'order':        {
                    "column": json_request.get('order_by', 'priority'),
                    "dir":    json_request.get('order_direction', 'desc'),
                }
            }
            task_list = pending_tasks.prepare_filtered_pending_tasks(params)

            response = self.build_response(
                PendingTasksSchema(),
                {
                    "recordsTotal":    task_list.get('recordsTotal'),
                    "recordsFiltered": task_list.get('recordsFiltered'),
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

    def delete_pending_tasks(self):
        """
        Pending - delete
        ---
        description: Delete a list of pending tasks.
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

            if not pending_tasks.remove_pending_tasks(json_request.get('id_list', [])):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to delete the pending tasks by their IDs")
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

    def reorder_pending_tasks(self):
        """
        Pending - reorder
        ---
        description: Reorder a list of pending tasks.
        requestBody:
            description: Requested list of items to reorder.
            required: True
            content:
                application/json:
                    schema:
                        RequestPendingTasksReorderSchema
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
            json_request = self.read_json_request(RequestPendingTasksReorderSchema())

            if not pending_tasks.reorder_pending_tasks(json_request.get('id_list', []), json_request.get('position', 'top')):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to save new order")
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

    def get_pending_status_of_tasks(self):
        """
        Pending - get status of tasks
        ---
        description: Set the status of a list of pending tasks
        requestBody:
            description: Set the status of a list of pending tasks.
            required: True
            content:
                application/json:
                    schema:
                        RequestTableUpdateByIdList
        responses:
            200:
                description: 'Sample response: Returns a list of tasks with their status.'
                content:
                    application/json:
                        schema:
                            PendingTasksTableResultsSchema
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

            status_results = pending_tasks.fetch_tasks_status(json_request.get('id_list', []))
            if not status_results:
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to fetch pending tasks status")
                self.write_error()
                return

            response = self.build_response(
                PendingTasksSchema(),
                {
                    "results": status_results,
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

    def set_pending_status_as_ready(self):
        """
        Pending - set status as ready
        ---
        description: Set the status of a list of created pending tasks as ready for processing
        requestBody:
            description: Set the status of a list of created pending tasks as ready for processing.
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

            if not pending_tasks.update_pending_tasks_status(json_request.get('id_list', []), status='pending'):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to update pending tasks status")
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

    def gen_download_link_pending_task_file(self, task_id=None):
        """
        Pending - request a link for downloading a task file
        ---
        description: Request a link for downloading a task file
        responses:
            200:
                description: 'Successful request; Returns download link ID'
                content:
                    application/json:
                        schema:
                            TaskDownloadLinkSchema
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
            status_results = pending_tasks.fetch_tasks_status([task_id])
            if not status_results:
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to fetch pending tasks status")
                self.write_error()
                return

            # Set file details
            abspath = status_results[0].get('abspath', '')
            basename = os.path.basename(abspath)

            # Generate download link
            link_data = {
                'abspath':  abspath,
                'basename': basename,
            }
            download_links = DownloadsLinks()
            link_id = download_links.generate_download_link(link_data)

            response = self.build_response(
                TaskDownloadLinkSchema(),
                {
                    "link_id": link_id,
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

    def gen_download_link_pending_task_data(self, task_id=None):
        """
        Pending - request a link for downloading a task data
        ---
        description: Request a link for downloading a task data
        responses:
            200:
                description: 'Successful request; Returns download link ID'
                content:
                    application/json:
                        schema:
                            TaskDownloadLinkSchema
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
            status_results = pending_tasks.fetch_tasks_status([task_id])
            if not status_results:
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to fetch pending tasks status")
                self.write_error()
                return

            if not status_results[0].get('status') == 'complete':
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Pending tasks status is not 'complete'")
                self.write_error()
                return

            # Set file details
            abspath = status_results[0].get('abspath', '')
            basename = 'data.json'
            data_file = os.path.join(os.path.dirname(abspath), basename)

            # Generate download link
            link_data = {
                'abspath':  data_file,
                'basename': basename,
            }
            download_links = DownloadsLinks()
            link_id = download_links.generate_download_link(link_data)

            response = self.build_response(
                TaskDownloadLinkSchema(),
                {
                    "link_id": link_id,
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
