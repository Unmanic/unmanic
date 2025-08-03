#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugin_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2022, (11:38 PM)

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

from ..plugin_type_base import PluginType


class PluginAPI(PluginType):
    name = "Frontend - Plugin API"
    runner = "render_plugin_api"
    runner_docstring = """
    Runner function - provide a custom API endpoint managed by a plugin.

    The 'data' object argument includes:
        content_type                    - The content type to be set when writing back to the browser.
        content                         - The content to print to the browser.
        status                          - The HTTP status code for the response.
        method                          - The request method.
        path                            - The path received after the '/unmanic/panel' path.
        uri                             - The request uri.
        query                           - The request query.
        arguments                       - A dictionary of GET arguments received.
        body                            - A dictionary of body arguments received.

    :param data:
    :return:
    """
    data_schema = {
        "content_type": {
            "required": True,
            "type":     str,
        },
        "content":      {
            "required": True,
            "type":     dict,
        },
        "status":      {
            "required": True,
            "type":     int,
        },
        "method":      {
            "required": False,
            "type":     str,
        },
        "path":         {
            "required": False,
            "type":     str,
        },
        "uri":          {
            "required": False,
            "type":     str,
        },
        "query":        {
            "required": False,
            "type":     str,
        },
        "arguments":    {
            "required": False,
            "type":     dict,
        },
        "body":         {
            "required": False,
            "type":     dict,
        },
    }
    test_data = {
        'content_type': 'application/json',
        'content':      {},
        'status':       200,
        'method':       "GET",
        'path':         "/webhook",
        'arguments':    {'param': [b'true'], 'foo': [b'ba']},
        'body':         {'param': [b'true'], 'foo': [b'ba']},
    }
