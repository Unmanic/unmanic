#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.ffprobe_mkv.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     19 Sep 2019, (6:59 PM)
 
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

mkv_multiple_subtitles_ffprobe = {
    "streams": [
        {
            "index":                0,
            "codec_name":           "h264",
            "codec_long_name":      "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
            "profile":              "High",
            "codec_type":           "video",
            "codec_time_base":      "1001/48000",
            "codec_tag_string":     "[0][0][0][0]",
            "codec_tag":            "0x0000",
            "width":                1920,
            "height":               1080,
            "coded_width":          1920,
            "coded_height":         1088,
            "has_b_frames":         2,
            "sample_aspect_ratio":  "1:1",
            "display_aspect_ratio": "16:9",
            "pix_fmt":              "yuv420p",
            "level":                40,
            "color_range":          "tv",
            "color_space":          "bt709",
            "color_transfer":       "bt709",
            "color_primaries":      "bt709",
            "chroma_location":      "left",
            "field_order":          "progressive",
            "refs":                 1,
            "is_avc":               "true",
            "nal_length_size":      "4",
            "r_frame_rate":         "24000/1001",
            "avg_frame_rate":       "24000/1001",
            "time_base":            "1/1000",
            "start_pts":            0,
            "start_time":           "0.000000",
            "bits_per_raw_sample":  "8",
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
                "BPS":                  "7055847",
                "BPS-eng":              "7055847",
                "DURATION":             "00:50:01.457000000",
                "DURATION-eng":         "00:50:01.457000000",
                "NUMBER_OF_FRAMES":     "71963",
                "NUMBER_OF_FRAMES-eng": "71963",
                "NUMBER_OF_BYTES":      "2647227928",
                "NUMBER_OF_BYTES-eng":  "2647227928"
            }
        },
        {
            "index":            1,
            "codec_name":       "eac3",
            "codec_long_name":  "ATSC A/52B (AC-3, E-AC-3)",
            "codec_type":       "audio",
            "codec_time_base":  "1/48000",
            "codec_tag_string": "[0][0][0][0]",
            "codec_tag":        "0x0000",
            "sample_fmt":       "fltp",
            "sample_rate":      "48000",
            "channels":         6,
            "bits_per_sample":  0,
            "dmix_mode":        "-1",
            "ltrt_cmixlev":     "-1.000000",
            "ltrt_surmixlev":   "-1.000000",
            "loro_cmixlev":     "-1.000000",
            "loro_surmixlev":   "-1.000000",
            "r_frame_rate":     "0/0",
            "avg_frame_rate":   "0/0",
            "time_base":        "1/1000",
            "start_pts":        0,
            "start_time":       "0.000000",
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
                "language":             "eng",
                "BPS":                  "640000",
                "BPS-eng":              "640000",
                "DURATION":             "00:50:01.408000000",
                "DURATION-eng":         "00:50:01.408000000",
                "NUMBER_OF_FRAMES":     "93794",
                "NUMBER_OF_FRAMES-eng": "93794",
                "NUMBER_OF_BYTES":      "240112640",
                "NUMBER_OF_BYTES-eng":  "240112640"
            }
        },
        {
            "index":            2,
            "codec_name":       "subrip",
            "codec_long_name":  "SubRip subtitle",
            "codec_type":       "subtitle",
            "codec_time_base":  "0/1",
            "codec_tag_string": "[0][0][0][0]",
            "codec_tag":        "0x0000",
            "r_frame_rate":     "0/0",
            "avg_frame_rate":   "0/0",
            "time_base":        "1/1000",
            "start_pts":        0,
            "start_time":       "0.000000",
            "duration_ts":      3001457,
            "duration":         "3001.457000",
            "disposition":      {
                "default":          1,
                "dub":              0,
                "original":         0,
                "comment":          0,
                "lyrics":           0,
                "karaoke":          0,
                "forced":           1,
                "hearing_impaired": 0,
                "visual_impaired":  0,
                "clean_effects":    0,
                "attached_pic":     0,
                "timed_thumbnails": 0
            },
            "tags":             {
                "language":             "eng",
                "title":                "Forced",
                "BPS":                  "11",
                "BPS-eng":              "11",
                "DURATION":             "00:08:15.036000000",
                "DURATION-eng":         "00:08:15.036000000",
                "NUMBER_OF_FRAMES":     "20",
                "NUMBER_OF_FRAMES-eng": "20",
                "NUMBER_OF_BYTES":      "727",
                "NUMBER_OF_BYTES-eng":  "727"
            }
        },
        {
            "index":            3,
            "codec_name":       "subrip",
            "codec_long_name":  "SubRip subtitle",
            "codec_type":       "subtitle",
            "codec_time_base":  "0/1",
            "codec_tag_string": "[0][0][0][0]",
            "codec_tag":        "0x0000",
            "r_frame_rate":     "0/0",
            "avg_frame_rate":   "0/0",
            "time_base":        "1/1000",
            "start_pts":        0,
            "start_time":       "0.000000",
            "duration_ts":      3001457,
            "duration":         "3001.457000",
            "disposition":      {
                "default":          0,
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
                "language":             "eng",
                "BPS":                  "64",
                "BPS-eng":              "64",
                "DURATION":             "00:47:43.688000000",
                "DURATION-eng":         "00:47:43.688000000",
                "NUMBER_OF_FRAMES":     "835",
                "NUMBER_OF_FRAMES-eng": "835",
                "NUMBER_OF_BYTES":      "22960",
                "NUMBER_OF_BYTES-eng":  "22960"
            }
        },
        {
            "index":            4,
            "codec_name":       "subrip",
            "codec_long_name":  "SubRip subtitle",
            "codec_type":       "subtitle",
            "codec_time_base":  "0/1",
            "codec_tag_string": "[0][0][0][0]",
            "codec_tag":        "0x0000",
            "r_frame_rate":     "0/0",
            "avg_frame_rate":   "0/0",
            "time_base":        "1/1000",
            "start_pts":        0,
            "start_time":       "0.000000",
            "duration_ts":      3001457,
            "duration":         "3001.457000",
            "disposition":      {
                "default":          0,
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
                "language":             "eng",
                "title":                "SDH",
                "BPS":                  "67",
                "BPS-eng":              "67",
                "DURATION":             "00:49:46.743000000",
                "DURATION-eng":         "00:49:46.743000000",
                "NUMBER_OF_FRAMES":     "938",
                "NUMBER_OF_FRAMES-eng": "938",
                "NUMBER_OF_BYTES":      "25074",
                "NUMBER_OF_BYTES-eng":  "25074"
            }
        }
    ],
    "format":  {
        "filename":         "some_file_name.mkv",
        "nb_streams":       5,
        "nb_programs":      0,
        "format_name":      "matroska,webm",
        "format_long_name": "Matroska / WebM",
        "start_time":       "0.000000",
        "duration":         "3001.457000",
        "size":             "2888175930",
        "bit_rate":         "7698063",
        "probe_score":      100,
        "tags":             {
            "encoder":       "libebml v1.3.5 + libmatroska v1.4.8",
            "creation_time": "2018-03-03T00:34:27.000000Z"
        }
    }
}

mkv_stereo_aac_audio_ffprobe = {
    "streams": [
        {
            "index":                0,
            "codec_name":           "h264",
            "codec_long_name":      "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
            "profile":              "High",
            "codec_type":           "video",
            "codec_time_base":      "1001/48000",
            "codec_tag_string":     "[0][0][0][0]",
            "codec_tag":            "0x0000",
            "width":                1920,
            "height":               1080,
            "coded_width":          1920,
            "coded_height":         1088,
            "has_b_frames":         1,
            "sample_aspect_ratio":  "1:1",
            "display_aspect_ratio": "16:9",
            "pix_fmt":              "yuv420p",
            "level":                40,
            "chroma_location":      "left",
            "field_order":          "progressive",
            "refs":                 1,
            "is_avc":               "true",
            "nal_length_size":      "4",
            "r_frame_rate":         "24000/1001",
            "avg_frame_rate":       "24000/1001",
            "time_base":            "1/1000",
            "start_pts":            36,
            "start_time":           "0.036000",
            "bits_per_raw_sample":  "8",
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
                "BPS-eng":                          "7905319",
                "DURATION-eng":                     "00:42:24.626000000",
                "NUMBER_OF_FRAMES-eng":             "61010",
                "NUMBER_OF_BYTES-eng":              "2514510211",
                "_STATISTICS_WRITING_APP-eng":      "mkvmerge v24.0.0 ('Beyond The Pale') 64-bit",
                "_STATISTICS_WRITING_DATE_UTC-eng": "2019-02-13 09:50:46",
                "_STATISTICS_TAGS-eng":             "BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES"
            }
        },
        {
            "index":            1,
            "codec_name":       "aac",
            "codec_long_name":  "AAC (Advanced Audio Coding)",
            "profile":          "LC",
            "codec_type":       "audio",
            "codec_time_base":  "1/44100",
            "codec_tag_string": "[0][0][0][0]",
            "codec_tag":        "0x0000",
            "sample_fmt":       "fltp",
            "sample_rate":      "44100",
            "channels":         2,
            "channel_layout":   "stereo",
            "bits_per_sample":  0,
            "r_frame_rate":     "0/0",
            "avg_frame_rate":   "0/0",
            "time_base":        "1/1000",
            "start_pts":        0,
            "start_time":       "0.000000",
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
                "language":                         "eng",
                "BPS-eng":                          "125590",
                "DURATION-eng":                     "00:42:24.628000000",
                "NUMBER_OF_FRAMES-eng":             "109588",
                "NUMBER_OF_BYTES-eng":              "39947530",
                "_STATISTICS_WRITING_APP-eng":      "mkvmerge v24.0.0 ('Beyond The Pale') 64-bit",
                "_STATISTICS_WRITING_DATE_UTC-eng": "2019-02-13 09:50:46",
                "_STATISTICS_TAGS-eng":             "BPS DURATION NUMBER_OF_FRAMES NUMBER_OF_BYTES"
            }
        }
    ],
    "format":  {
        "filename":         "some_file_name.mkv",
        "nb_streams":       2,
        "nb_programs":      0,
        "format_name":      "matroska,webm",
        "format_long_name": "Matroska / WebM",
        "start_time":       "0.000000",
        "duration":         "2544.662000",
        "size":             "2555231069",
        "bit_rate":         "8033227",
        "probe_score":      100,
        "tags":             {
            "encoder":       "libebml v1.3.6 + libmatroska v1.4.9",
            "creation_time": "2019-02-13T09:50:46.000000Z"
        }
    }
}
