#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.file_move.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     24 Mar 2021, (9:42 PM)

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


class FileMove(PluginType):
    name = "Post-processor - File movements"
    runner = "on_postprocessor_file_movement"
    runner_docstring = """
    Runner function - configures additional postprocessor file movements during the postprocessor stage of a task.

    The 'data' object argument includes:
        library_id              - Integer, the library that the current task is associated with.
        source_data             - Dictionary, data pertaining to the original source file.
        remove_source_file      - Boolean, should Unmanic remove the original source file after all copy operations are complete. (default: 'True' if file name has changed)
        copy_file               - Boolean, should Unmanic run a copy operation with the returned data variables. (default: 'False')
        file_in                 - String, the converted cache file to be copied by the postprocessor.
        file_out                - String, the destination file that the file will be copied to.
        run_default_file_copy   - Boolean, should Unmanic run the default post-process file movement. (default: 'True')

    :param data:
    :return:
    """
    data_schema = {
        "library_id":            {
            "required": True,
            "type":     int,
        },
        "source_data":           {
            "required": True,
            "type":     dict,
        },
        "remove_source_file":    {
            "required": True,
            "type":     bool,
        },
        "copy_file":             {
            "required": True,
            "type":     bool,
        },
        "file_in":               {
            "required": True,
            "type":     str,
        },
        "file_out":              {
            "required": True,
            "type":     str,
        },
        "run_default_file_copy": {
            "required": True,
            "type":     bool,
        },
    }
    test_data = {
        'library_id':            1,
        'copy_file':             True,
        'file_in':               '{cache_path}/{test_file_out}',
        'file_out':              '{library_path}/{test_file_in}',
        'remove_source_file':    True,
        'run_default_file_copy': True,
        'source_data':           {
            'abspath':  '{library_path}/{test_file_in}',
            'basename': '{test_file_in}',
        }
    }
