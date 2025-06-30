#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
    unmanic.postprocessor_complete.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 June 2025, (9:47 PM)

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


class PostprocessorComplete(PluginType):
    name = "Events - Postprocessor complete"
    runner = "emit_postprocessor_complete"
    runner_docstring = """
    Runner function - emit data when a task has been fully post-processed and recorded in history.

    The 'data' object argument includes:
        library_id           - Integer, the ID of the library.
        task_id              - Integer, unique identifier of the task.
        task_type            - String, "local" or "remote".
        source_data          - Dict, information about the source file for the task, e.g.:
                                 - abspath: String, absolute path to the file.
                                 - basename: String, file name.
        destination_data     - Dict, information about the final output file after postprocessing for the task, e.g.:
                                 - abspath: String, absolute path to the file.
                                 - basename: String, file name.
        task_success         - Boolean, True if the task succeeded.
        start_time           - Float, UNIX timestamp when the task began.
        finish_time          - Float, UNIX timestamp when the task completed.
        processed_by_worker  - String, identifier of the worker that processed it.
        log                  - String, full text of the task log.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":          {"required": False, "type": int},
        "task_id":             {"required": False, "type": int},
        "task_type":           {"required": False, "type": str},
        "source_data":         {"required": False, "type": dict},
        "destination_data":    {"required": False, "type": dict},
        "task_success":        {"required": False, "type": bool},
        "start_time":          {"required": False, "type": float},
        "finish_time":         {"required": False, "type": float},
        "processed_by_worker": {"required": False, "type": str},
        "log":                 {"required": False, "type": str},
    }
    test_data = {
        "library_id":          1,
        "task_id":             4321,
        "task_type":           "local",
        "source_data":         {
            "abspath":  "/path/to/media/file.mp4",
            "basename": "file.mp4"
        },
        "destination_data":    {
            "abspath":  "/path/to/media/file.mkv",
            "basename": "file.mkv"
        },
        "task_success":        True,
        "start_time":          1625080000.0,
        "finish_time":         1625080050.0,
        "processed_by_worker": "worker-42",
        "log":                 "RUNNER: Transcode Video Files [Pass #1]\nPost-processor complete\n",
    }
