#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.workers_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Aug 2021, (10:41 AM)

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
from unmanic.libs.uiserver import UnmanicDataQueues, UnmanicRunningTreads
from unmanic.webserver.api_v2.base_api_handler import BaseApiHandler, BaseApiError
from unmanic.webserver.api_v2.schema.schemas import RequestWorkerByIdSchema, WorkerStatusSuccessSchema
from unmanic.webserver.helpers import workers


class ApiWorkersHandler(BaseApiHandler):
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/workers/worker/pause",
            "supported_methods": ["POST"],
            "call_method":       "pause_worker",
        },
        {
            "path_pattern":      r"/workers/worker/pause/all",
            "supported_methods": ["POST"],
            "call_method":       "pause_all_workers",
        },
        {
            "path_pattern":      r"/workers/worker/resume",
            "supported_methods": ["POST"],
            "call_method":       "resume_worker",
        },
        {
            "path_pattern":      r"/workers/worker/resume/all",
            "supported_methods": ["POST"],
            "call_method":       "resume_all_workers",
        },
        {
            "path_pattern":      r"/workers/worker/terminate",
            "supported_methods": ["DELETE"],
            "call_method":       "terminate_worker",
        },
        {
            "path_pattern":      r"/workers/worker/terminate/all",
            "supported_methods": ["DELETE"],
            "call_method":       "terminate_all_workers",
        },
        {
            "path_pattern":      r"/workers/status",
            "supported_methods": ["GET"],
            "call_method":       "workers_status",
        },
    ]

    def initialize(self, **kwargs):
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        urt = UnmanicRunningTreads()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()
        self.foreman = urt.get_unmanic_running_thread('foreman')

    def pause_worker(self):
        """
        Workers - Pause worker by ID
        ---
        description: Pauses a worker by its ID.
        requestBody:
            description: Requested a worker be paused by its ID.
            required: True
            content:
                application/json:
                    schema:
                        RequestWorkerByIdSchema
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
            json_request = self.read_json_request(RequestWorkerByIdSchema())

            if not workers.pause_worker_by_id(json_request.get('worker_id')):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to pause worker")
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

    def pause_all_workers(self):
        """
        Workers - Pause all workers
        ---
        description: Pause all workers.
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
            if not workers.pause_all_workers():
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to pause all workers")
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

    def resume_worker(self):
        """
        Workers - Resume worker by ID
        ---
        description: Resumes a worker by its ID.
        requestBody:
            description: Requested a worker be resumed by its ID.
            required: True
            content:
                application/json:
                    schema:
                        RequestWorkerByIdSchema
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
            json_request = self.read_json_request(RequestWorkerByIdSchema())

            if not workers.resume_worker_by_id(json_request.get('worker_id')):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to resume worker")
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

    def resume_all_workers(self):
        """
        Workers - Resume all workers
        ---
        description: Resumes all workers.
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
            if not workers.resume_all_workers():
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to resume all workers")
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

    def terminate_worker(self):
        """
        Workers - Terminate worker by ID
        ---
        description: Terminates a worker by its ID.
        requestBody:
            description: Requested a worker be terminated by its ID.
            required: True
            content:
                application/json:
                    schema:
                        RequestWorkerByIdSchema
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
            json_request = self.read_json_request(RequestWorkerByIdSchema())

            if not workers.terminate_worker_by_id(json_request.get('worker_id')):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to resume worker")
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

    def terminate_all_workers(self):
        """
        Workers - Terminate all workers
        ---
        description: Terminate all workers.
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
            if not workers.terminate_all_workers():
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to terminate all workers")
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

    def workers_status(self):
        """
        Workers - Return the status of all workers
        ---
        description: Returns the status of all workers.
        responses:
            200:
                description: 'Sample response: Returns the status of all workers.'
                content:
                    application/json:
                        schema:
                            WorkerStatusSuccessSchema
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
            workers_status = self.foreman.get_all_worker_status()

            response = self.build_response(
                WorkerStatusSuccessSchema(),
                {
                    'workers_status': workers_status,
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
