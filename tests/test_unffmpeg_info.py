#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unffmpeg_info.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Sep 2019, (2:51 PM)
 
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

try:
    from lib import unffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from lib import unffmpeg


class TestClass(object):
    """
    TestClass

    Runs unit tests against the unffmpeg info class

    """

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_can_read_ffmpeg_supported_codecs(self):
        # Fetch a list of supported codecs from unffmpeg
        all_codecs = unffmpeg.Info().get_all_supported_codecs()
        # Ensure audio codecs are available
        assert 'audio' in all_codecs
        # Ensure video codecs are available
        assert 'video' in all_codecs

    def test_can_read_ffmpeg_supported_video_codecs(self):
        # Fetch a list of supported codecs from unffmpeg
        all_codecs = unffmpeg.Info().get_all_supported_codecs()
        # Ensure h264 is available
        assert 'h264' in all_codecs['video']
        # Ensure h265 is available
        assert 'hevc' in all_codecs['video']
        # Ensure a gibberish codec is not available
        assert 'NONSENSE CODEC' not in all_codecs['video']
