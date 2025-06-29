#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 June 2025, (8:32 PM)

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


class ScanComplete(PluginType):
    name = "Events - Scan complete"
    runner = "emit_scan_complete"
    runner_docstring = """
    Runner function - emit data after a library scan completes.

    The 'data' object argument includes:
        library_id              - Integer, the ID of the library scanned.
        library_name            - String, the human-readable name of the library.
        library_path            - String, filesystem path to the library.
        scan_start_time         - Float, UNIX timestamp when the scan started.
        scan_end_time           - Float, UNIX timestamp when the scan ended.
        scan_duration           - Float, duration of the scan in seconds.
        files_scanned_count     - Integer, total number of files scanned.

    :param data:
    :return:
    """
    data_schema = {
        "library_id":          {
            "required": False,
            "type":     int
        },
        "library_name":        {
            "required": False,
            "type":     str
        },
        "library_path":        {
            "required": False,
            "type":     str
        },
        "scan_start_time":     {
            "required": False,
            "type":     float
        },
        "scan_end_time":       {
            "required": False,
            "type":     float
        },
        "scan_duration":       {
            "required": False,
            "type":     float
        },
        "files_scanned_count": {
            "required": False,
            "type":     int
        },
    }
    test_data = {
        "library_id":          1,
        "library_name":        "MyLibrary",
        "library_path":        "/path/to/mylibrary",
        "scan_start_time":     1625078400.0,
        "scan_end_time":       1625078460.0,
        "scan_duration":       60.0,
        "files_scanned_count": 123,
    }
