#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.ffmpegmediator.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Oct 2020, (2:39 PM)

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

from unmanic.libs import ffmpeg


def generate_example_ffmpeg_args(config):
    """
    Configure ffmpeg object.

    :return:
    """
    dummy_probe = {
        "streams": [
            {
                "index":                0,
                "codec_name":           "h264",
                "codec_long_name":      "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                "profile":              "Main",
                "codec_type":           "video",
                "codec_time_base":      "1/50",
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
                "chroma_location":      "left",
                "refs":                 1,
                "is_avc":               "true",
                "nal_length_size":      "4",
                "r_frame_rate":         "25/1",
                "avg_frame_rate":       "25/1",
                "time_base":            "1/12800",
                "start_pts":            0,
                "start_time":           "0.000000",
                "duration_ts":          67584,
                "duration":             "5.280000",
                "bit_rate":             "1205959",
                "bits_per_raw_sample":  "8",
                "nb_frames":            "132",
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
                    "creation_time": "1970-01-01T00:00:00.000000Z",
                    "language":      "und",
                    "handler_name":  "VideoHandler"
                }
            },
            {
                "index":            1,
                "codec_name":       "aac",
                "codec_long_name":  "AAC (Advanced Audio Coding)",
                "profile":          "LC",
                "codec_type":       "audio",
                "codec_time_base":  "1/48000",
                "codec_tag_string": "mp4a",
                "codec_tag":        "0x6134706d",
                "sample_fmt":       "fltp",
                "sample_rate":      "48000",
                "channels":         6,
                "channel_layout":   "5.1",
                "bits_per_sample":  0,
                "r_frame_rate":     "0/0",
                "avg_frame_rate":   "0/0",
                "time_base":        "1/48000",
                "start_pts":        0,
                "start_time":       "0.000000",
                "duration_ts":      254976,
                "duration":         "5.312000",
                "bit_rate":         "384828",
                "max_bit_rate":     "400392",
                "nb_frames":        "249",
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
                    "creation_time": "1970-01-01T00:00:00.000000Z",
                    "language":      "und",
                    "handler_name":  "SoundHandler"
                }
            }
        ],
        "format":  {
            "filename":         "/path/to/input/video.mkv",
            "nb_streams":       2,
            "nb_programs":      0,
            "format_name":      "mov,mp4,m4a,3gp,3g2,mj2",
            "format_long_name": "QuickTime / MOV",
            "start_time":       "0.000000",
            "duration":         "5.312000",
            "size":             "1055736",
            "bit_rate":         "1589963",
            "probe_score":      100,
            "tags":             {
                "major_brand":       "isom",
                "minor_version":     "512",
                "compatible_brands": "isomiso2avc1mp41",
                "creation_time":     "1970-01-01T00:00:00.000000Z",
                "encoder":           "Lavf53.24.2"
            }
        }
    }
    settings = {
        'audio_codec':                          config.AUDIO_CODEC,
        'audio_codec_cloning':                  config.AUDIO_CODEC_CLONING,
        'audio_stereo_stream_bitrate':          config.AUDIO_STEREO_STREAM_BITRATE,
        'audio_stream_encoder':                 config.AUDIO_STREAM_ENCODER,
        'cache_path':                           config.CACHE_PATH,
        'debugging':                            config.DEBUGGING,
        'enable_audio_encoding':                config.ENABLE_AUDIO_ENCODING,
        'enable_audio_stream_stereo_cloning':   config.ENABLE_AUDIO_STREAM_STEREO_CLONING,
        'enable_audio_stream_transcoding':      config.ENABLE_AUDIO_STREAM_TRANSCODING,
        'enable_video_encoding':                config.ENABLE_VIDEO_ENCODING,
        'out_container':                        config.OUT_CONTAINER,
        'remove_subtitle_streams':              config.REMOVE_SUBTITLE_STREAMS,
        'video_codec':                          config.VIDEO_CODEC,
        'video_stream_encoder':                 config.VIDEO_STREAM_ENCODER,
        'overwrite_additional_ffmpeg_options':  config.OVERWRITE_ADDITIONAL_FFMPEG_OPTIONS,
        'additional_ffmpeg_options':            config.ADDITIONAL_FFMPEG_OPTIONS,
        'enable_hardware_accelerated_decoding': config.ENABLE_HARDWARE_ACCELERATED_DECODING,
    }

    # Create ffmpeg object
    ffmpeg_obj = ffmpeg.FFMPEGHandle(settings)

    # Create commandline args from ffmpeg object
    ffmpeg_args = ffmpeg_obj.generate_ffmpeg_args(dummy_probe, '/path/to/input/video.mkv', '/path/to/output/video.mkv')

    # Return args
    return ffmpeg_args
