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
        source_data             - Dictionary containing data pertaining to the original source file.
        remove_source_file      - Boolean, should Unmanic remove the original source file after all copy operations are complete.
        copy_file               - Boolean, should Unmanic run a copy operation with the returned data variables.
        file_in                 - The converted cache file to be copied by the postprocessor.
        file_out                - The destination file that the file will be copied to.

    :param data:
    :return:
    """
    data_schema = {
        "source_data":        {
            "required": True,
            "type":     dict,
        },
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
        'file_in':            '/tmp/unmanic/unmanic_file_conversion-1616581079.6339643/TEST_FILE-1616581079.633973.mkv',
        'file_out':           '/library/TEST_FILE.mkv',
        'remove_source_file': True,
        'source_data':        {
            'abspath':          '/tmp/TEST_FILE.mp4',
            'basename':         'TEST_FILE.mp4',
            'bit_rate':         '2753870',
            'duration':         '81.951667',
            'format_long_name': '',
            'format_name':      'mov,mp4,m4a,3gp,3g2,mj2',
            'id':               1,
            'size':             '28210534',
            'streams':          [
                {
                    'avg_frame_rate':  '2997/100',
                    'bit_rate':        '2533754',
                    'channel_layout':  '',
                    'channels':        '',
                    'codec_long_name': 'unknown',
                    'codec_type':      'video',
                    'coded_height':    '720',
                    'coded_width':     '1280',
                    'duration':        '81.748415',
                    'height':          '720',
                    'id':              1,
                    'width':           '1280'
                },
                {
                    'avg_frame_rate':  '0/0',
                    'bit_rate':        '224000',
                    'channel_layout':  '5.1(side)',
                    'channels':        '6',
                    'codec_long_name': 'unknown',
                    'codec_type':      'audio',
                    'coded_height':    '',
                    'coded_width':     '',
                    'duration':        '81.952000',
                    'height':          '',
                    'id':              2,
                    'width':           ''
                }
            ]
        }
    }
