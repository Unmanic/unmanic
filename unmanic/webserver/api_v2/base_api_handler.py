#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.base_api_handler.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     26 Oct 2020, (12:15 PM)

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
import re
import sys
import traceback
from typing import (
    Any,
)

import tornado.web
import tornado.log
import tornado.routing

from tornado.web import RequestHandler


class BaseApiHandler(RequestHandler):
    api_version = 2
    routes = []

    """
    Valid API return status codes:
    """
    STATUS_SUCCESS = 200
    STATUS_ERROR_EXTERNAL = 400
    STATUS_ERROR_MISSING = 404
    STATUS_ERROR_INTERNAL = 500

    def set_default_headers(self):
        """
        Set the default response header to be JSON.
        This overwrites the RequestHandler method.

        :return:
        """
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def write_success(self, data):
        """
        Write data out as HTTP code 200
        Finishes this response, ending the HTTP request.

        :param data:
        :return:
        """
        self.set_status(self.STATUS_SUCCESS)
        self.finish(data)

    def write_error(self, status_code: int = 500, **kwargs: Any) -> None:
        """
        Set the default error message.
        This overwrites the RequestHandler method.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception (including
        HTTPError), an ``exc_info`` triple will be available as
        ``kwargs["exc_info"]``.  Note that this exception may not be
        the "current" exception for purposes of methods like
        ``sys.exc_info()`` or ``traceback.format_exc``.

        :param status_code:
        :param kwargs:
        :return:
        """
        if self.settings.get("serve_traceback"):
            exc_info = kwargs.get('exc_info')
            if not exc_info:
                exc_info = sys.exc_info()
            # in debug mode, try to send a traceback
            traceback_lines = []
            for line in traceback.format_exception(*exc_info):
                traceback_lines.append(line)
            self.finish({
                'error':     "%(code)d: %(message)s" % {"code": status_code, "message": self._reason},
                'traceback': traceback_lines,
            })
        else:
            self.finish({
                'error': "%(code)d: %(message)s" % {"code": status_code, "message": self._reason},
            })

    def handle_missing_endpoint(self):
        """
        Return a JSON 404 error message.
        Finishes this response, ending the HTTP request.

        :return:
        """
        self.set_status(self.STATUS_ERROR_MISSING)
        self.finish({'error': 'Endpoint not found'})

    def action_route(self):
        """
        Determine the handler method for the route.
        Execute that handler method.
        If not method if found to handle this route,
        return 404 by exec 'handle_missing_endpoint()' method.

        :return:
        """
        request_api_endpoint = re.sub('^\/api\/v\d', '', self.request.uri)
        for route in self.routes:
            # Check if the rout supports the supported http methods
            supported_methods = route.get("supported_methods")
            if supported_methods and not self.request.method in supported_methods:
                # The request's method is not supported by this route.
                continue

            # If the route does not have any params an it matches the current request URI, then route to that method.
            if list(filter(None, request_api_endpoint.split('/'))) == list(filter(None, route.get("path_pattern").split('/'))):
                tornado.log.app_log.debug("Routing API to {}.{}()".format(self.__class__.__name__, route.get("call_method")),
                                          exc_info=True)
                getattr(self, route.get("call_method"))()
                return

            # Fetch the path match from this route's path pattern
            path_match = tornado.routing.PathMatches(route.get("path_pattern"))

            # Check if the path matches, and get any params from a match
            params = path_match.match(self.request)

            # If we have a match and were returned some params, load that method
            if params:
                tornado.log.app_log.debug(
                    "Routing API to {}.{}(*args={}, **kwargs={})".format(self.__class__.__name__, route.get("call_method"),
                                                                         params["path_args"], params["path_kwargs"]),
                    exc_info=True)
                getattr(self, route.get("call_method"))(*params["path_args"], **params["path_kwargs"])
                return

        # If we got this far, then the URI does not match any of our configured routes.
        tornado.log.app_log.warning("No match found for API route: {}".format(self.request.uri), exc_info=True)
        self.handle_missing_endpoint()

    def get(self, path):
        """
        Route all GET requests to the 'action_route()' method

        :param path:
        :return:
        """
        self.action_route()

    def post(self, path):
        """
        Route all POST requests to the 'action_route()' method

        :param path:
        :return:
        """
        self.action_route()
