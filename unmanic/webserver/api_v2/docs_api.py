#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.docs_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 Jul 2021, (11:31 AM)

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

import tornado.log
from unmanic.libs import session
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiHandler, BaseApiError
from unmanic.webserver.api_v2.schema.schemas import DocumentContentSuccessSchema
from unmanic.webserver.helpers import documents


class ApiDocsHandler(BaseApiHandler):
    session = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/docs/privacypolicy",
            "supported_methods": ["GET"],
            "call_method":       "get_privacy_policy",
        },
        {
            "path_pattern":      r"/docs/logs/zip",
            "supported_methods": ["GET"],
            "call_method":       "get_logs_as_zip",
        },
    ]

    def initialize(self, **kwargs):
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def get_privacy_policy(self):
        """
        Docs - read privacy policy
        ---
        description: Returns the privacy policy.
        responses:
            200:
                description: 'Sample response: Returns the privacy policy.'
                content:
                    application/json:
                        schema:
                            DocumentContentSuccessSchema
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
            privacy_policy_content = []
            privacy_policy_file = os.path.join(os.path.dirname(__file__), '..', 'docs', 'privacy_policy.md')
            if os.path.exists(privacy_policy_file):
                with open(privacy_policy_file, 'r') as f:
                    privacy_policy_content = f.readlines()
            if not privacy_policy_content:
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Unable to read privacy policy.")
                self.write_error()
                return
            else:
                response = self.build_response(
                    DocumentContentSuccessSchema(),
                    {
                        "content": privacy_policy_content,
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

    def get_logs_as_zip(self):
        """
        Docs - get log files as zip
        ---
        description: Returns the all log files as zip.
        responses:
            200:
                description: 'Sample response: Returns the all log files as zip.'
                content:
                    application/octet-stream:
                        schema:
                            type: string
                            format: binary
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
            log_files_zip_path = documents.generate_log_files_zip()

            with open(log_files_zip_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    self.write(chunk)

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename=UnmanicLogs.zip')
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
