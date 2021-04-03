#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.file_test.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     31 Mar 2021, (5:12 PM)

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


class FileTest(PluginType):
    name = "Library Management - File test"
    runner = "on_library_management_file_test"
    runner_docstring = """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:
    """
    data_schema = {
        "path":                      {
            "required": True,
            "type":     str,
        },
        "issues":                    {
            "required": True,
            "type":     list,
        },
        "add_file_to_pending_tasks": {
            "required": True,
            "type":     bool,
        },
    }
    test_data = {
        'path':                      '/library/TEST_FILE.mkv',
        'issues':                    [
            {
                'id':      'format',
                'message': "File is already in target format - '/library/TEST_FILE.mkv'"
            }
        ],
        'add_file_to_pending_tasks': True,
    }
