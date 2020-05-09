#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.ffprobe_mp4.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Sep 2019, (8:29 AM)
 
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

mp4_dd_plus_audio_ffprobe = {
    "streams": [
        {
            "index":                0,
            "codec_name":           "h264",
            "codec_long_name":      "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
            "profile":              "Constrained Baseline",
            "codec_type":           "video",
            "codec_time_base":      "50/2997",
            "codec_tag_string":     "avc1",
            "codec_tag":            "0x31637661",
            "width":                1280,
            "height":               720,
            "coded_width":          1280,
            "coded_height":         720,
            "has_b_frames":         0,
            "sample_aspect_ratio":  "1:1",
            "display_aspect_ratio": "16:9",
            "pix_fmt":              "yuv420p",
            "level":                31,
            "color_range":          "tv",
            "chroma_location":      "left",
            "refs":                 1,
            "is_avc":               "true",
            "nal_length_size":      "4",
            "r_frame_rate":         "2997/100",
            "avg_frame_rate":       "2997/100",
            "time_base":            "1/29970",
            "start_pts":            0,
            "start_time":           "0.000000",
            "duration_ts":          2450000,
            "duration":             "81.748415",
            "bit_rate":             "2533754",
            "bits_per_raw_sample":  "8",
            "nb_frames":            "2450",
            "disposition":          {
                "default":          1,
                "dub":              0,
                "original":         0,
                "comment":          0,
                "lyrics":           0,
                "karaoke":          0,
                "forced":           0,
                "hearing_impaired": 0,
                "visual_impaired":  0,
                "clean_effects":    0,
                "attached_pic":     0,
                "timed_thumbnails": 0
            },
            "tags":                 {
                "creation_time": "2011-09-22T00:28:51.000000Z",
                "language":      "und",
                "handler_name":  "video handler"
            }
        },
        {
            "index":            1,
            "codec_name":       "eac3",
            "codec_long_name":  "ATSC A/52B (AC-3, E-AC-3)",
            "codec_type":       "audio",
            "codec_time_base":  "1/48000",
            "codec_tag_string": "ec-3",
            "codec_tag":        "0x332d6365",
            "sample_fmt":       "fltp",
            "sample_rate":      "48000",
            "channels":         6,
            "channel_layout":   "5.1(side)",
            "bits_per_sample":  0,
            "dmix_mode":        "-1",
            "ltrt_cmixlev":     "-1.000000",
            "ltrt_surmixlev":   "-1.000000",
            "loro_cmixlev":     "-1.000000",
            "loro_surmixlev":   "-1.000000",
            "r_frame_rate":     "0/0",
            "avg_frame_rate":   "0/0",
            "time_base":        "1/48000",
            "start_pts":        0,
            "start_time":       "0.000000",
            "duration_ts":      3933696,
            "duration":         "81.952000",
            "bit_rate":         "224000",
            "nb_frames":        "2561",
            "disposition":      {
                "default":          1,
                "dub":              0,
                "original":         0,
                "comment":          0,
                "lyrics":           0,
                "karaoke":          0,
                "forced":           0,
                "hearing_impaired": 0,
                "visual_impaired":  0,
                "clean_effects":    0,
                "attached_pic":     0,
                "timed_thumbnails": 0
            },
            "tags":             {
                "creation_time": "2011-09-22T00:28:51.000000Z",
                "language":      "und",
                "handler_name":  "sound handler"
            },
            "side_data_list":   [
                {
                    "side_data_type": "Audio Service Type"
                }
            ]
        }
    ],
    "format":  {
        "filename":         "some_file_name.mp4",
        "nb_streams":       2,
        "nb_programs":      0,
        "format_name":      "mov,mp4,m4a,3gp,3g2,mj2",
        "format_long_name": "QuickTime / MOV",
        "start_time":  "0.000000",
        "duration":    "81.951667",
        "size":        "28210534",
        "bit_rate":    "2753870",
        "probe_score": 100,
        "tags":        {
            "major_brand":       "dby1",
            "minor_version":     "0",
            "compatible_brands": "isommp42dby1",
            "creation_time":     "2011-09-22T00:28:51.000000Z",
            "encoder":           "Audio: Dolby Digital Plus Encoder 2.2.2 "
                                 "Video: Dolby Impact H.264 Encoder 2.4.7.26 (win64)"
        }
    }
}
