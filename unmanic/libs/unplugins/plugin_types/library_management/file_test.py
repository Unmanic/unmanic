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
        library_id                      - The library that the current task is associated with
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.
        priority_score                  - Integer, an additional score that can be added to set the position of the new task in the task queue.
        shared_info                     - Dictionary, information provided by previous plugin runners. This can be appended to for subsequent runners.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":                {
            "required": True,
            "type":     int,
        },
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
        "priority_score":            {
            "required": True,
            "type":     int,
        },
        "shared_info":               {
            "required": False,
            "type":     dict,
        },
    }
    test_data = {
        'library_id':                1,
        'path':                      '{library_path}/{test_file_in}',
        'issues':                    [
            {
                'id':      'format',
                'message': "File is already in target format - '{library_path}/{test_file_in}'"
            }
        ],
        'add_file_to_pending_tasks': True,
        'priority_score':            0,
        'shared_info':               {},
    }
