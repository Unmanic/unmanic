#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unffmpeg_audio_codec.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Sep 2019, (8:12 AM)
 
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
    from lib import common, unlogger, unffmpeg
    from tests.test_data import mkv_ffprobe, mp4_ffprobe
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from lib import common, unlogger, unffmpeg
    from tests.test_data import mkv_ffprobe, mp4_ffprobe


class TestClass(object):
    """
    TestClass

    Runs unit tests against the unffmpeg audio codec class

    """

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        unmanic_logging = unlogger.UnmanicLogger.__call__(False)
        unmanic_logging.get_logger()

    def test_ensure_we_can_generate_audio_codec_args(self):
        # Fetch a list of args from the unffmpeg audio codec handler
        audio_codec_handle = unffmpeg.AudioCodecHandle(mkv_ffprobe.mkv_multiple_subtitles_ffprobe)
        audio_codec_args = audio_codec_handle.args()
        # Assert the streams to map array is not empty
        assert audio_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert audio_codec_args['streams_to_encode']

    def test_ensure_we_can_generate_copy_current_audio_codec_args(self):
        # Fetch a list of args from the unffmpeg audio codec handler
        audio_codec_handle = unffmpeg.AudioCodecHandle(mkv_ffprobe.mkv_multiple_subtitles_ffprobe)
        # Just copy the current codec (do not re-encode)
        audio_codec_handle.disable_audio_encoding = True
        audio_codec_args = audio_codec_handle.args()
        # Assert the streams to map array is not empty
        assert audio_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert audio_codec_args['streams_to_encode']
        # Assert the streams to encode array is set to copy
        assert audio_codec_args['streams_to_encode'][1] == 'copy'

    def test_ensure_we_can_generate_a_cloned_stereo_aac_audio_codec_stream_from_ss_audio_stream_args(self):
        # Fetch a list of args from the unffmpeg audio codec handler
        audio_codec_handle = unffmpeg.AudioCodecHandle(mp4_ffprobe.mp4_dd_plus_audio_ffprobe)
        # Set the audio codec to aac
        audio_codec_handle.set_audio_codec('aac')
        audio_codec_args = audio_codec_handle.args()
        # Assert the streams to map array is not empty
        assert audio_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert audio_codec_args['streams_to_encode']
        # Assert the first streams to encode array item is set to copy (copies the DD Plus stream)
        assert audio_codec_args['streams_to_encode'][1] == 'copy'
        # Assert the second streams to encode array item is set to aac (clones the DD Plus stream to a stereo aac)
        assert audio_codec_args['streams_to_encode'][3] == 'aac'

    def test_ensure_we_can_set_the_bitrate_of_a_stereo_audio_codec_stream(self):
        # Fetch a list of args from the unffmpeg audio codec handler
        audio_codec_handle = unffmpeg.AudioCodecHandle(mp4_ffprobe.mp4_dd_plus_audio_ffprobe)
        # Set the audio codec to aac
        audio_codec_handle.set_audio_codec('aac')
        audio_codec_handle.audio_stereo_stream_bitrate = 'TEST_BITRATE'
        audio_codec_args = audio_codec_handle.args()
        # Assert the streams to map array is not empty
        assert audio_codec_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert audio_codec_args['streams_to_encode']
        # Assert the second streams to encode array item has a bitrate set of 'TEST_BITRATE'
        assert audio_codec_args['streams_to_encode'][5] == 'TEST_BITRATE'

    def test_ensure_throws_exception_for_absent_audio_codec_args(self):
        with pytest.raises(ImportError) as excinfo:
            # Fetch a list of args from the unffmpeg audio codec handler
            audio_codec_handle = unffmpeg.AudioCodecHandle(mkv_ffprobe.mkv_stereo_aac_audio_ffprobe)
            # Set the audio codec to something that does not exist
            audio_codec_handle.set_audio_codec('non_existent_codec')
