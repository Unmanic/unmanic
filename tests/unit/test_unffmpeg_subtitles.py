#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unffmpeg_subtitles.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     19 Sep 2019, (6:57 PM)
 
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

    Runs unit tests against the unffmpeg subtitle's class

    """

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # sys.path.append(self.project_dir)
        unmanic_logging = unlogger.UnmanicLogger.__call__(False)
        unmanic_logging.get_logger()

    def get_container(self, out_container):
        return unffmpeg.containers.grab_module(out_container)

    @pytest.mark.unittest
    def test_ensure_we_can_copy_subtitles_if_container_supports_current_subtitle_stream_in_args(self):
        # Get the destination container object by it's name
        destination_container = self.get_container('matroska')
        # Fetch a list of args from the unffmpeg subtitle handler
        subtitle_handle = unffmpeg.SubtitleHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe, destination_container)
        subtitle_args = subtitle_handle.args()
        # Assert the streams to map array is not empty
        assert subtitle_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert subtitle_args['streams_to_encode']

    @pytest.mark.unittest
    def test_ensure_we_can_remove_subtitles_in_args(self):
        # Get the destination container object by it's name
        destination_container = self.get_container('matroska')
        # Fetch a list of args from the unffmpeg subtitle handler
        subtitle_handle = unffmpeg.SubtitleHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe, destination_container)
        # Remove the subtitles for this (even though the destination supports subtitles)
        subtitle_handle.remove_subtitle_streams = True
        subtitle_args = subtitle_handle.args()
        # Assert the streams to map array is not empty
        assert not subtitle_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert not subtitle_args['streams_to_encode']

    @pytest.mark.unittest
    def test_ensure_we_can_convert_subtitles_from_mkv_to_avi_in_args(self):
        # Get the destination container object by it's name
        destination_container = self.get_container('avi')
        # Fetch a list of args from the unffmpeg subtitle handler
        subtitle_handle = unffmpeg.SubtitleHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe, destination_container)
        subtitle_args = subtitle_handle.args()
        # Assert the streams to map array is not empty
        assert subtitle_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert subtitle_args['streams_to_encode']

    @pytest.mark.unittest
    def test_ensure_we_can_convert_subtitles_from_mkv_to_mp4_in_args(self):
        # Get the destination container object by it's name
        destination_container = self.get_container('mp4')
        # Fetch a list of args from the unffmpeg subtitle handler
        subtitle_handle = unffmpeg.SubtitleHandle(ffprobe_mkv.mkv_multiple_subtitles_ffprobe, destination_container)
        subtitle_args = subtitle_handle.args()
        # Assert the streams to map array is not empty
        assert subtitle_args['streams_to_map']
        # Assert the streams to encode array is not empty
        assert subtitle_args['streams_to_encode']
