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
    runner = "on_worker_process"
    data_schema = {
        "exec_ffmpeg": {
            "required": True,
            "type":     bool,
        },
        "file_probe":  {
            "required": True,
            "type":     dict,
            "children": {
                "streams": {
                    "required": True,
                    "type":     list,
                },
                "format":  {
                    "required": True,
                    "type":     dict,
                },
            },
        },
        "ffmpeg_args": {
            "required": True,
            "type":     list,
        },
        "file_in":     {
            "required": True,
            "type":     str,
        },
        "file_out":    {
            "required": True,
            "type":     str,
        },
    }
    test_data = {
        "exec_ffmpeg": True,
        "ffmpeg_args": [
            '-i',
            '/library/test_file.mkv',
            '-hide_banner',
            '-loglevel',
            'info',
            '-strict',
            '-2',
            '-max_muxing_queue_size',
            '512',
            '-map',
            '0:0',
            '-map',
            '0:1',
            '-c:v:0',
            'libx264',
            '-c:a:0',
            'copy',
            '-y',
            '/tmp/unmanic/unmanic_file_conversion-1615778539.3000267/test_file-1615778539.3000503.mp4'
        ],
        "file_in":     "/library/test_file.mkv",
        "file_out":    "/tmp/unmanic/unmanic_file_conversion-1615778539.3000267/test_file-1615778539.3000503.mp4",
        "file_probe":  {
            'format':  {
                'bit_rate':    '376719',
                'duration':    '1384.507000',
                'filename':    '/library/test_file.mkv',
                'format_name': 'matroska,webm',
                'nb_programs': 0,
                'nb_streams':  2,
                'probe_score': 100,
                'size':        '65196385',
                'start_time':  '0.000000',
                'tags':        {'ENCODER': 'Lavf58.20.100', 'JUNK': ''}
            },
            'streams': [
                {
                    'avg_frame_rate':       '27021/1127',
                    'chroma_location':      'left',
                    'closed_captions':      0,
                    'codec_long_name':      'unknown',
                    'codec_name':           'hevc',
                    'codec_tag':            '0x0000',
                    'codec_tag_string':     '[0][0][0][0]',
                    'codec_time_base':      '417083/10000000',
                    'codec_type':           'video',
                    'coded_height':         480,
                    'coded_width':          640,
                    'color_range':          'tv',
                    'display_aspect_ratio': '4:3',
                    'disposition':          {
                        'attached_pic':     0,
                        'clean_effects':    0,
                        'comment':          0,
                        'default':          1,
                        'dub':              0,
                        'forced':           0,
                        'hearing_impaired': 0,
                        'karaoke':          0,
                        'lyrics':           0,
                        'original':         0,
                        'timed_thumbnails': 0,
                        'visual_impaired':  0
                    },
                    'has_b_frames':         2,
                    'height':               480,
                    'index':                0,
                    'level':                90,
                    'pix_fmt':              'yuv420p',
                    'profile':              '1',
                    'r_frame_rate':         '27021/1127',
                    'refs':                 1,
                    'sample_aspect_ratio':  '1:1',
                    'start_pts':            42,
                    'start_time':           '0.042000',
                    'tags':                 {
                        'DURATION': '00:23:04.507000000',
                        'ENCODER':  'Lavc58.35.100 libx265'
                    },
                    'time_base':            '1/1000',
                    'width':                640
                },
                {
                    'avg_frame_rate':   '0/0',
                    'bit_rate':         '128000',
                    'bits_per_sample':  0,
                    'channel_layout':   'stereo',
                    'channels':         2,
                    'codec_long_name':  'unknown',
                    'codec_name':       'mp3',
                    'codec_tag':        '0x0000',
                    'codec_tag_string': '[0][0][0][0]',
                    'codec_time_base':  '1/48000',
                    'codec_type':       'audio',
                    'disposition':      {
                        'attached_pic':     0,
                        'clean_effects':    0,
                        'comment':          0,
                        'default':          1,
                        'dub':              0,
                        'forced':           0,
                        'hearing_impaired': 0,
                        'karaoke':          0,
                        'lyrics':           0,
                        'original':         0,
                        'timed_thumbnails': 0,
                        'visual_impaired':  0
                    },
                    'index':            1,
                    'r_frame_rate':     '0/0',
                    'sample_fmt':       'fltp',
                    'sample_rate':      '48000',
                    'start_pts':        0,
                    'start_time':       '0.000000',
                    'tags':             {
                        'DURATION': '00:23:04.488000000',
                        'title':    'final'
                    },
                    'time_base':        '1/1000'
                }
            ]
        },
    }
