#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.unmanic.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     01 Aug 2021, (10:35 AM)

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
from tornado.routing import PathMatches
from tornado.web import URLSpec

from apispec import yaml_utils
from apispec.exceptions import APISpecError
from apispec_webframeworks.tornado import TornadoPlugin


class UnmanicSpecPlugin(TornadoPlugin):
    """APISpec plugin for Unmanic"""

    @staticmethod
    def _operations_from_urlspec(urlspec):
        """Generator of operations described in the handler's routes list

        :param urlspec:
        :type urlspec: URLSpec descendant
        """
        handler_class = urlspec.handler_class
        for r in handler_class.routes:
            matcher = PathMatches(r.get('path_pattern'))
            if matcher.regex == urlspec.regex:
                for http_method in r.get('supported_methods', []):
                    method = getattr(handler_class, r.get('call_method'))
                    operation_data = yaml_utils.load_yaml_from_docstring(method.__doc__)
                    if operation_data:
                        operation = {http_method.lower(): operation_data}
                        yield operation

    def path_helper(self, operations, *, urlspec, **kwargs):
        """Path helper that allows passing a Tornado URLSpec or tuple."""
        if not isinstance(urlspec, URLSpec):
            urlspec = URLSpec(*urlspec)
        for operation in self._operations_from_urlspec(urlspec):
            operations.update(operation)
        if not operations:
            raise APISpecError(f"Could not find endpoint for urlspec {urlspec}")
        params_method = getattr(urlspec.handler_class, list(operations.keys())[0])
        operations.update(self._extensions_from_handler(urlspec.handler_class))
        return self.tornadopath2openapi(urlspec, params_method)
