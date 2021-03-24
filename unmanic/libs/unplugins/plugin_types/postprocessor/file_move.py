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
    runner = "on_postprocessor_file_movement"
    data_schema = {
        "remove_source_file": {
            "required": True,
            "type":     bool,
        },
        "copy_file":          {
            "required": True,
            "type":     bool,
        },
        "file_in":            {
            "required": True,
            "type":     str,
        },
        "file_out":           {
            "required": True,
            "type":     str,
        },
    }
    test_data = {
        'copy_file':          True,
        'file_in':            '/tmp/unmanic/unmanic_file_conversion-1616581079.6339643/TEST_FILE-1616581079.633973.mp4',
        'file_out':           '/library/TEST_FILE.mp4',
        'remove_source_file': True
    }
