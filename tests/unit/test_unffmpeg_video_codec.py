#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unffmpeg_video_codec.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     20 Sep 2019, (6:55 PM)
 
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

import os
import sys

import pytest

try:
    from unmanic.libs import common, unlogger, unffmpeg
    from tests.support_.test_data import ffprobe_mkv
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import common, unlogger, unffmpeg
    from tests.support_.test_data import ffprobe_mkv


class TestClass(object):
    """
    TestClass

    Runs unit tests against the unffmpeg video codec class

    """

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        unmanic_logging = unlogger.UnmanicLogger.__call__(False)
        unmanic_logging.get_logger()

    @pytest.mark.unittest
    def test_ensure_we_can_generate_video_codec_args(self):
        # Fetch a list of args from the unffmpeg video codec handler
        video_codec_handle = unffmpeg.VideoCodecHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe)
        video_codec_args = video_codec_handle.args()
        # Assert the streams to map array is not empty
        assert video_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert video_codec_args['streams_to_encode']

    @pytest.mark.unittest
    def test_ensure_we_can_generate_copy_current_video_codec_args(self):
        # Fetch a list of args from the unffmpeg video codec handler
        video_codec_handle = unffmpeg.VideoCodecHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe)
        # Just copy the current codec (do not re-encode)
        video_codec_handle.disable_video_encoding = True
        video_codec_args = video_codec_handle.args()
        # Assert the streams to map array is not empty
        assert video_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert video_codec_args['streams_to_encode']
        # Assert the streams to encode array is set to copy
        assert video_codec_args['streams_to_encode'][1] == 'copy'

    @pytest.mark.unittest
    def test_ensure_we_can_generate_hevc_video_codec_args(self):
        # Fetch a list of args from the unffmpeg video codec handler
        video_codec_handle = unffmpeg.VideoCodecHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe)
        # Set the video codec to HEVC
        video_codec_handle.set_video_codec_with_default_encoder('hevc')
        video_codec_args = video_codec_handle.args()
        # Assert the streams to map array is not empty
        assert video_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert video_codec_args['streams_to_encode']
        # Assert the streams to encode array is set to libx265
        assert video_codec_args['streams_to_encode'][1] == 'libx265'

    @pytest.mark.unittest
    def test_ensure_throws_exception_for_absent_video_codec_args(self):
        with pytest.raises(ImportError) as excinfo:
            # Fetch a list of args from the unffmpeg video codec handler
            video_codec_handle = unffmpeg.VideoCodecHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe)
            # Set the video codec to something that does not exist
            video_codec_handle.set_video_codec_with_default_encoder('non_existent_codec')

    @pytest.mark.unittest
    def test_ensure_args_of_video_stream_is_copied_if_src_codec_matches_dest_codec(self):
        # Fetch a list of args from the unffmpeg video codec handler
        video_codec_handle = unffmpeg.VideoCodecHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe)
        # Set the video codec to H264 the same as the current source video codec
        video_codec_handle.set_video_codec_with_default_encoder('h264')
        video_codec_args = video_codec_handle.args()
        # Assert the streams to map array is not empty
        assert video_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert video_codec_args['streams_to_encode']
        # Assert the streams to encode array is set to copy
        assert video_codec_args['streams_to_encode'][1] == 'copy'
