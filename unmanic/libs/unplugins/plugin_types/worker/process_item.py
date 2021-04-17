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
        exec_ffmpeg             - Boolean, should Unmanic run FFMPEG with the data returned from this plugin.
        file_probe              - A dictionary object containing the current file probe state.
        ffmpeg_args             - A list of Unmanic's default FFMPEG args.
        file_in                 - The source file to be processed by the FFMPEG command.
        file_out                - The destination that the FFMPEG command will output.
        original_file_path      - The absolute path to the original library file.

    :param data:
    :return:
    """
    data_schema = {
        "exec_ffmpeg":        {
            "required": True,
            "type":     bool,
        },
        "file_probe":         {
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
        "ffmpeg_args":        {
            "required": True,
            "type":     list,
        },
        "file_in":            {
            "required": True,
            "type":     str,
        },
        "file_out":           {
            "required": True,
            "type":     str,
        },
        "original_file_path": {
            "required": False,
            "type":     str,
        },
    }
    test_data = {
        'exec_ffmpeg':        True,
        'ffmpeg_args':        [
            '-i',
            '/library/TEST_FILE.mkv',
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
            '0:3',
            '-map',
            '0:4',
            '-map',
            '0:5',
            '-map',
            '0:6',
            '-map',
            '0:1',
            '-map',
            '0:2',
            '-c:v:0',
            'copy',
            '-c:v:1',
            'copy',
            '-c:v:2',
            'copy',
            '-c:v:3',
            'copy',
            '-c:v:4',
            'copy',
            '-c:a:0',
            'copy',
            '-c:s:0',
            'mov_text',
            '-y',
            '/tmp/unmanic/unmanic_file_conversion-1616571944.7296784/TEST_FILE-1616571944.7296877-WORKING-1.mp4'
        ],
        'file_in':            '/library/TEST_FILE.mkv',
        'file_out':           '/tmp/unmanic/unmanic_file_conversion-1616571944.7296784/TEST_FILE-1616571944.7296877-WORKING-1.mp4',
        'file_probe':         {
            'format':  {
                'bit_rate':    '5536191',
                'duration':    '4585.462000',
                'filename':    '/library/TEST_FILE.mkv',
                'format_name': 'matroska,webm',
                'nb_programs': 0,
                'nb_streams':  7,
                'probe_score': 100,
                'size':        '3173249493',
                'start_time':  '0.000000',
                'tags':        {
                    'creation_time': '2016-09-05T15:58:56.000000Z',
                    'encoder':       'libebml v1.3.4 + libmatroska '
                                     'v1.4.5',
                    'title':         'VIDEO_TITLE'
                }
            },
            'streams': [
                {
                    'avg_frame_rate':       '24/1',
                    'bits_per_raw_sample':  '8',
                    'chroma_location':      'topleft',
                    'closed_captions':      0,
                    'codec_long_name':      'unknown',
                    'codec_name':           'h264',
                    'codec_tag':            '0x0000',
                    'codec_tag_string':     '[0][0][0][0]',
                    'codec_time_base':      '1/48',
                    'codec_type':           'video',
                    'coded_height':         1088,
                    'coded_width':          1920,
                    'color_primaries':      'bt709',
                    'color_range':          'tv',
                    'color_space':          'bt709',
                    'color_transfer':       'bt709',
                    'display_aspect_ratio': '479:269',
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
                    'field_order':          'progressive',
                    'has_b_frames':         1,
                    'height':               1076,
                    'index':                0,
                    'is_avc':               'true',
                    'level':                40,
                    'nal_length_size':      '4',
                    'pix_fmt':              'yuv420p',
                    'profile':              '100',
                    'r_frame_rate':         '24/1',
                    'refs':                 1,
                    'sample_aspect_ratio':  '1:1',
                    'start_pts':            0,
                    'start_time':           '0.000000',
                    'tags':                 {
                        'language': 'eng',
                        'title':    'VIDEO_TITLE'
                    },
                    'time_base':            '1/1000',
                    'width':                1916
                },
                {
                    'avg_frame_rate':   '0/0',
                    'bit_rate':         '384000',
                    'bits_per_sample':  0,
                    'channel_layout':   '5.1(side)',
                    'channels':         6,
                    'codec_long_name':  'unknown',
                    'codec_name':       'ac3',
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
                    'dmix_mode':        '-1',
                    'index':            1,
                    'loro_cmixlev':     '-1.000000',
                    'loro_surmixlev':   '-1.000000',
                    'ltrt_cmixlev':     '-1.000000',
                    'ltrt_surmixlev':   '-1.000000',
                    'r_frame_rate':     '0/0',
                    'sample_fmt':       'fltp',
                    'sample_rate':      '48000',
                    'start_pts':        0,
                    'start_time':       '0.000000',
                    'tags':             {
                        'language': 'fr',
                        'title':    'VIDEO_TITLE'
                    },
                    'time_base':        '1/1000'
                },
                {
                    'avg_frame_rate':   '0/0',
                    'bit_rate':         '384000',
                    'bits_per_sample':  0,
                    'channel_layout':   '5.1(side)',
                    'channels':         6,
                    'codec_long_name':  'unknown',
                    'codec_name':       'ac3',
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
                    'dmix_mode':        '-1',
                    'index':            2,
                    'loro_cmixlev':     '-1.000000',
                    'loro_surmixlev':   '-1.000000',
                    'ltrt_cmixlev':     '-1.000000',
                    'ltrt_surmixlev':   '-1.000000',
                    'r_frame_rate':     '0/0',
                    'sample_fmt':       'fltp',
                    'sample_rate':      '48000',
                    'start_pts':        0,
                    'start_time':       '0.000000',
                    'tags':             {
                        'language': 'eng',
                        'title':    'VIDEO_TITLE'
                    },
                    'time_base':        '1/1000'
                },
                {
                    'avg_frame_rate':   '0/0',
                    'codec_long_name':  'unknown',
                    'codec_name':       'subrip',
                    'codec_tag':        '0x0000',
                    'codec_tag_string': '[0][0][0][0]',
                    'codec_time_base':  '0/1',
                    'codec_type':       'subtitle',
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
                    'duration':         '4585.462000',
                    'duration_ts':      4585462,
                    'index':            3,
                    'r_frame_rate':     '0/0',
                    'start_pts':        0,
                    'start_time':       '0.000000',
                    'tags':             {
                        'language': 'fr'
                    },
                    'time_base':        '1/1000'
                },
                {
                    'avg_frame_rate':   '0/0',
                    'codec_long_name':  'unknown',
                    'codec_name':       'subrip',
                    'codec_tag':        '0x0000',
                    'codec_tag_string': '[0][0][0][0]',
                    'codec_time_base':  '0/1',
                    'codec_type':       'subtitle',
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
                    'duration':         '4585.462000',
                    'duration_ts':      4585462,
                    'index':            4,
                    'r_frame_rate':     '0/0',
                    'start_pts':        0,
                    'start_time':       '0.000000',
                    'tags':             {
                        'language': 'eng'
                    },
                    'time_base':        '1/1000'
                },
                {
                    'avg_frame_rate':      '0/0',
                    'bits_per_raw_sample': '8',
                    'chroma_location':     'center',
                    'closed_captions':     0,
                    'codec_long_name':     'unknown',
                    'codec_name':          'mjpeg',
                    'codec_tag':           '0x0000',
                    'codec_tag_string':    '[0][0][0][0]',
                    'codec_time_base':     '0/1',
                    'codec_type':          'video',
                    'coded_height':        176,
                    'coded_width':         120,
                    'color_range':         'pc',
                    'color_space':         'bt470bg',
                    'disposition':         {
                        'attached_pic':     1,
                        'clean_effects':    0,
                        'comment':          0,
                        'default':          0,
                        'dub':              0,
                        'forced':           0,
                        'hearing_impaired': 0,
                        'karaoke':          0,
                        'lyrics':           0,
                        'original':         0,
                        'timed_thumbnails': 0,
                        'visual_impaired':  0
                    },
                    'duration':            '4585.462000',
                    'duration_ts':         412691580,
                    'has_b_frames':        0,
                    'height':              176,
                    'index':               5,
                    'level':               -99,
                    'pix_fmt':             'yuvj444p',
                    'profile':             '192',
                    'r_frame_rate':        '90000/1',
                    'refs':                1,
                    'start_pts':           0,
                    'start_time':          '0.000000',
                    'tags':                {
                        'filename': 'small_cover.jpg',
                        'mimetype': 'image/jpeg'
                    },
                    'time_base':           '1/90000',
                    'width':               120
                },
                {
                    'avg_frame_rate':      '0/0',
                    'bits_per_raw_sample': '8',
                    'chroma_location':     'center',
                    'closed_captions':     0,
                    'codec_long_name':     'unknown',
                    'codec_name':          'mjpeg',
                    'codec_tag':           '0x0000',
                    'codec_tag_string':    '[0][0][0][0]',
                    'codec_time_base':     '0/1',
                    'codec_type':          'video',
                    'coded_height':        120,
                    'coded_width':         213,
                    'color_range':         'pc',
                    'color_space':         'bt470bg',
                    'disposition':         {
                        'attached_pic':     1,
                        'clean_effects':    0,
                        'comment':          0,
                        'default':          0,
                        'dub':              0,
                        'forced':           0,
                        'hearing_impaired': 0,
                        'karaoke':          0,
                        'lyrics':           0,
                        'original':         0,
                        'timed_thumbnails': 0,
                        'visual_impaired':  0
                    },
                    'duration':            '4585.462000',
                    'duration_ts':         412691580,
                    'has_b_frames':        0,
                    'height':              120,
                    'index':               6,
                    'level':               -99,
                    'pix_fmt':             'yuvj444p',
                    'profile':             '192',
                    'r_frame_rate':        '90000/1',
                    'refs':                1,
                    'start_pts':           0,
                    'start_time':          '0.000000',
                    'tags':                {
                        'filename': 'small_cover_land.jpg',
                        'mimetype': 'image/jpeg'
                    },
                    'time_base':           '1/90000',
                    'width':               213
                },
                {
                    'avg_frame_rate':      '0/0',
                    'bits_per_raw_sample': '8',
                    'chroma_location':     'center',
                    'closed_captions':     0,
                    'codec_long_name':     'unknown',
                    'codec_name':          'mjpeg',
                    'codec_tag':           '0x0000',
                    'codec_tag_string':    '[0][0][0][0]',
                    'codec_time_base':     '0/1',
                    'codec_type':          'video',
                    'coded_height':        882,
                    'coded_width':         600,
                    'color_range':         'pc',
                    'color_space':         'bt470bg',
                    'disposition':         {
                        'attached_pic':     1,
                        'clean_effects':    0,
                        'comment':          0,
                        'default':          0,
                        'dub':              0,
                        'forced':           0,
                        'hearing_impaired': 0,
                        'karaoke':          0,
                        'lyrics':           0,
                        'original':         0,
                        'timed_thumbnails': 0,
                        'visual_impaired':  0
                    },
                    'duration':            '4585.462000',
                    'duration_ts':         412691580,
                    'has_b_frames':        0,
                    'height':              882,
                    'index':               7,
                    'level':               -99,
                    'pix_fmt':             'yuvj444p',
                    'profile':             '192',
                    'r_frame_rate':        '90000/1',
                    'refs':                1,
                    'start_pts':           0,
                    'start_time':          '0.000000',
                    'tags':                {
                        'filename': 'cover.jpg',
                        'mimetype': 'image/jpeg'
                    },
                    'time_base':           '1/90000',
                    'width':               600
                },
                {
                    'avg_frame_rate':      '0/0',
                    'bits_per_raw_sample': '8',
                    'chroma_location':     'center',
                    'closed_captions':     0,
                    'codec_long_name':     'unknown',
                    'codec_name':          'mjpeg',
                    'codec_tag':           '0x0000',
                    'codec_tag_string':    '[0][0][0][0]',
                    'codec_time_base':     '0/1',
                    'codec_type':          'video',
                    'coded_height':        600,
                    'coded_width':         1067,
                    'color_range':         'pc',
                    'color_space':         'bt470bg',
                    'disposition':         {
                        'attached_pic':     1,
                        'clean_effects':    0,
                        'comment':          0,
                        'default':          0,
                        'dub':              0,
                        'forced':           0,
                        'hearing_impaired': 0,
                        'karaoke':          0,
                        'lyrics':           0,
                        'original':         0,
                        'timed_thumbnails': 0,
                        'visual_impaired':  0
                    },
                    'duration':            '4585.462000',
                    'duration_ts':         412691580,
                    'has_b_frames':        0,
                    'height':              600,
                    'index':               8,
                    'level':               -99,
                    'pix_fmt':             'yuvj444p',
                    'profile':             '192',
                    'r_frame_rate':        '90000/1',
                    'refs':                1,
                    'start_pts':           0,
                    'start_time':          '0.000000',
                    'tags':                {
                        'filename': 'cover_land.jpg',
                        'mimetype': 'image/jpeg'
                    },
                    'time_base':           '1/90000',
                    'width':               1067
                }
            ]
        },
        'original_file_path': '/library/TEST_FILE.mkv',
    }
