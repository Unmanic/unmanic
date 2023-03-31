#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.process_item.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (8:05 PM)

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


class ProcessItem(PluginType):
    name = "Worker - Processing file"
    runner = "on_worker_process"
    runner_docstring = """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        worker_log              - Array, the log lines that are being tailed by the frontend. Can be left empty.
        library_id              - Number, the library that the current task is associated with.
        exec_command            - Array, a subprocess command that Unmanic should execute. Can be empty.
        command_progress_parser - Function, a function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - String, the source file to be processed by the command.
        file_out                - String, the destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - String, the absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:
    """
    data_schema = {
        "worker_log":              {
            "required": True,
            "type":     list,
        },
        "library_id":              {
            "required": True,
            "type":     int,
        },
        "exec_command":            {
            "required": True,
            "type":     [list, str],
        },
        "command_progress_parser": {
            "required": True,
            "type":     ['callable', None],
        },
        "file_in":                 {
            "required": True,
            "type":     str,
        },
        "file_out":                {
            "required": True,
            "type":     str,
        },
        "original_file_path":      {
            "required": False,
            "type":     str,
        },
        "repeat":                  {
            "required": False,
            "type":     bool,
        },
    }
    test_data = {
        'worker_log':              [],
        'library_id':              1,
        'exec_command':            [],
        'command_progress_parser': None,
        'file_in':                 '{library_path}/{test_file_in}',
        'file_out':                '{cache_path}/{test_file_out}',
        'original_file_path':      '{library_path}/{test_file_in}',
        'repeat':                  False,
    }
