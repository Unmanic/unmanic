#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.api_request_router.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Oct 2020, (8:26 PM)

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

import importlib
import tornado.web
import tornado.log

from unmanic import config


class Handle404(tornado.web.RequestHandler):
    def get(self):
        self.set_status(404)
        self.write('404 Not Found')


class APIRequestRouter(tornado.routing.Router):
    app = None
    config = None

    def __init__(self, app, **kwargs):
        self.app = app
        self.config = config.CONFIG()

    def find_handler(self, request, **kwargs):
        api_version = request.path.split('/')[2]  # Set API version
        endpoint = request.path.split('/')[3]  # Set the endpoint
        params = list(filter(None, request.path.split('/')[4:]))  # Set the request params

        endpoint_handler = 'Api%sHandler' % endpoint.title()

        # Check if the handler exists - Otherwise set it to 404
        try:
            # Fetch handler class from api module matching api version
            handler = getattr(importlib.import_module("unmanic.webserver.api_{}".format(api_version)), endpoint_handler)
        except KeyError:
            tornado.log.app_log.warning("Unable to find handler for path: {}".format(endpoint_handler), exc_info=True)
            handler = Handle404

        # Return handler
        return self.app.get_handler_delegate(request, handler,
                                             target_kwargs=dict(
                                                 params=params,
                                             ),
                                             path_args=[request.path])
