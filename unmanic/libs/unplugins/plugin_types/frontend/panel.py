#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.panel.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     26 Aug 2021, (4:24 PM)

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


class DataPanel(PluginType):
    name = "Frontend - Data Panel"
    runner = "render_frontend_panel"
    runner_docstring = """
    Runner function - display a custom data panel in the frontend.

    The 'data' object argument includes:
        content_type                    - The content type to be set when writing back to the browser.
        content                         - The content to print to the browser.
        path                            - The path received after the '/unmanic/panel' path.
        arguments                       - A dictionary of GET arguments received.

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
            "type":     str,
        },
        "path":         {
            "required": False,
            "type":     str,
        },
        "arguments":    {
            "required": False,
            "type":     dict,
        },
    }
    test_data = {
        'content_type': 'text/html',
        'content':      "<!doctype html>"
                        "<html>"
                        "<head></head>"
                        "<body></body>"
                        "</html>",
        'path':         "/ui/ajax",
        'arguments':    {'param': [b'true'], 'foo': [b'ba']},
    }
