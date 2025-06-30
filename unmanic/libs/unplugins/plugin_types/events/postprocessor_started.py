#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
    unmanic.postprocessor_started.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 June 2025, (9:39 PM)

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


class PostprocessorStarted(PluginType):
    name = "Events - Postprocessor started"
    runner = "emit_postprocessor_started"
    runner_docstring = """
    Runner function - emit data when the post-processor picks up a task.

    The 'data' object argument includes:
        library_id        - Integer, the ID of the library.
        task_id           - Integer, unique identifier of the new task.
        task_type         - String, "local" or "remote" indicating how this task was processed.
        cache_path        - String, path to the task’s cache file.
        source_data       - Dict, information about the original source file:
                              - abspath: String, absolute source path.
                              - basename: String, filename of the source.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":  {"required": False, "type": int},
        "task_id":     {"required": False, "type": int},
        "task_type":   {"required": False, "type": str},
        "cache_path":  {"required": False, "type": str},
        "source_data": {"required": False, "type": dict},
    }
    test_data = {
        "library_id":  1,
        "task_id":     4321,
        "task_type":   "local",
        "cache_path":  "/path/to/cache/file.mp4",
        "source_data": {
            "abspath":  "/path/to/original/file.mp4",
            "basename": "file.mp4"
        }
    }
