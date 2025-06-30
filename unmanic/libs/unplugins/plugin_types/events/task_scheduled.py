#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
    unmanic.task_scheduled.py

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


class TaskScheduled(PluginType):
    name = "Events - Task scheduled"
    runner = "emit_task_scheduled"
    runner_docstring = """
    Runner function - emit data when a task is scheduled for execution on a worker.

    The 'data' object argument includes:
        library_id                - Integer, the ID of the library.
        task_id                   - Integer, unique identifier of the task.
        task_type                 - String, "local" or "remote". Indicates how this task is going to be processed.
        task_schedule_type        - String, either "local" or "remote". Where are we scheduling this task?
        remote_installation_info  - Dict, for remote tasks contains:
                                      - uuid:    String, the installation UUID.
                                      - address: String, the remote worker address.
                                    Empty dict for local tasks.
        source_data               - Dict, details of the task being scheduled:
                                      - abspath: String, absolute path to the file.
                                      - basename: String, file name.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":               {"required": False, "type": int},
        "task_id":                  {"required": False, "type": int},
        "task_type":                {"required": False, "type": str},
        "task_schedule_type":       {"required": False, "type": str},
        "remote_installation_info": {"required": False, "type": dict},
        "source_data":              {"required": False, "type": dict},
    }
    test_data = {
        "library_id":               1,
        "task_id":                  4321,
        "task_type":                "local",
        "task_schedule_type":       "local",
        "remote_installation_info": {},
        "source_data":              {
            "abspath":  "/path/to/media/file.mp4",
            "basename": "file.mp4"
        }
    }
