#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
    unmanic.file_queued.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 June 2025, (9:32 PM)

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


class FileQueued(PluginType):
    name = "Events - File queued"
    runner = "emit_file_queued"
    runner_docstring = """
    Runner function - emit data when a file has been tested and marked to be added to the pending task queue.

    The 'data' object argument includes:
        library_id      - Integer, the ID of the library.
        file_path       - String, the full path to the file being queued.
        priority_score  - Integer, the priority score assigned to this task.
        issues          - List, any file issues that were raised.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":     {"required": False, "type": int},
        "file_path":      {"required": False, "type": str},
        "priority_score": {"required": False, "type": int},
        "issues":         {"required": False, "type": list},
    }
    test_data = {
        "library_id":     1,
        "file_path":      "/path/to/media/file.mp4",
        "priority_score": 0,
        "issues":         [
            {"id": "format", "message": "File is already in target format."}
        ],
    }
