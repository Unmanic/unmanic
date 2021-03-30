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
    runner = "on_postprocessor_task_results"
    data_schema = {
        "task_processing_success":     {
            "required": False,
            "type":     bool,
        },
        "file_move_processes_success": {
            "required": False,
            "type":     bool,
        },
        "destination_files": {
            "required": False,
            "type":     list,
        },
        "source_data": {
            "required": False,
            "type":     list,
        },
    }
    test_data = {
        'task_processing_success':     True,
        'file_move_processes_success': True,
        'destination_files':           [
            '/tmp/TEST_FILE-UNMANIC.mkv',
        ],
        'source_data':                 {
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
        },
    }
