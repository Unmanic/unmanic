#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.task_result.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Mar 2021, (12:50 AM)

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


class TaskResult(PluginType):
    name = "Post-processor - Marking task success/failure"
    runner = "on_postprocessor_task_results"
    runner_docstring = """
    Runner function - provides a means for additional postprocessor functions based on the task success.

    The 'data' object argument includes:
        library_id                      - The library that the current task is associated with.
        task_id                         - Integer, unique identifier of the task.
        task_type                       - String, "local" or "remote".
        final_cache_path                - The path to the final cache file that was then used as the source for all destination files.
        task_processing_success         - Boolean, did all task processes complete successfully.
        file_move_processes_success     - Boolean, did all postprocessor movement tasks complete successfully.
        destination_files               - List containing all file paths created by postprocessor file movements.
        source_data                     - Dictionary containing data pertaining to the original source file.
        start_time                      - Float, UNIX timestamp when the task began.
        finish_time                     - Float, UNIX timestamp when the task completed.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":                  {"required": False, "type": int},
        "task_id":                     {"required": False, "type": int},
        "task_type":                   {"required": False, "type": str},
        "final_cache_path":            {"required": False, "type": str},
        "task_processing_success":     {"required": False, "type": bool},
        "file_move_processes_success": {"required": False, "type": bool},
        "destination_files":           {"required": False, "type": list},
        "source_data":                 {"required": False, "type": dict},
    }
    test_data = {
        'library_id':                  1,
        "task_id":                     4321,
        "task_type":                   "local",
        'final_cache_path':            '{cache_path}/{test_file_out}',
        'task_processing_success':     True,
        'file_move_processes_success': True,
        'destination_files':           [
            '{library_path}/complete/library/{test_file_in}',
        ],
        'source_data':                 {
            'abspath':  '{library_path}/{test_file_in}',
            'basename': '{test_file_in}',
        },
    }
