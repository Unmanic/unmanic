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

import tornado.web
import tornado.log
import tornado.routing

from tornado.web import RequestHandler


class BaseApiHandler(RequestHandler):
    routes = []

    def handle_404(self):
        self.set_status(404)
        self.write('404 Not Found')

    def action_route(self):
        for route in self.routes:
            # Check if the rout supports the supported http methods
            supported_methods = route.get("supported_methods")
            if supported_methods and not self.request.method in supported_methods:
                # The request's method is not supported by this route.
                continue

            # If the route does not have any params an it matches the current request URI, then route to that method.
            if list(filter(None, self.request.uri.split('/'))) == list(filter(None, route.get("path_pattern").split('/'))):
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
        self.handle_404()
