#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.filebrowser_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     13 Aug 2021, (2:37 PM)

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
from unmanic.webserver.api_v2.schema.schemas import DirectoryListingResultsSchema, DocumentContentSuccessSchema, \
    RequestDirectoryListingDataSchema
from unmanic.webserver.helpers.filebrowser import DirectoryListing


class ApiFilebrowserHandler(BaseApiHandler):
    session = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/filebrowser/list",
            "supported_methods": ["POST"],
            "call_method":       "fetch_directory_listing",
        }
    ]

    def initialize(self, **kwargs):
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def fetch_directory_listing(self):
        """
        Filebrowser - List files and/or subdirectories in a given directory
        ---
        description: Returns a list of files and/or subdirectories in a given directory.
        requestBody:
            description: Requested a list of files and/or subdirectories in a given directory.
            required: True
            content:
                application/json:
                    schema:
                        RequestDirectoryListingDataSchema
        responses:
            200:
                description: 'Sample response: Returns a list of files and/or subdirectories in a given directory.'
                content:
                    application/json:
                        schema:
                            DirectoryListingResultsSchema
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
            json_request = self.read_json_request(RequestDirectoryListingDataSchema())

            directory_listing = DirectoryListing(json_request.get('list_type', 'all'))
            path_data = directory_listing.fetch_path_data(json_request.get('current_path', '/'))

            response = self.build_response(
                DirectoryListingResultsSchema(),
                {
                    'directories': path_data.get('directories', []),
                    'files':       path_data.get('files', []),
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
