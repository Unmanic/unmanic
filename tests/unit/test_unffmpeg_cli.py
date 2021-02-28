#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unffmpeg_cli.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     22 Oct 2020, (7:16 PM)

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
    import unmanic.libs.unffmpeg as unffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(project_dir)
    import unmanic.libs.unffmpeg as unffmpeg



class TestClass(object):
    """
    TestClass

    """

    def setup_class(self):
        """
        Setup any state specific to the execution of the given class
        (which usually contains tests).

        :return:
        """
        pass

    def teardown_class(self):
        """
        Teardown any state that was previously setup with a call to
        setup_class.

        :return:
        """
        pass

    def setup_method(self):
        """
        Setup any state tied to the execution of the given method in a
        class.
        setup_method is invoked for every test method of a class.

        :return:
        """
        pass

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        call.

        :return:
        """
        pass

    def invalid_command(self):
        return {
            "TODO:": "Write valid command"
        }

    def valid_command(self):
        # command = ['ffmpeg', '-y', '-i', infile] + args + ['-y', outfile]
        valid_command = {
            "ffmpeg":                 "",
            "-y":                     "",
            " -hide_banner":          "",
            "-i":                     "/path/to/video.mkv",
            "-loglevel":              "info",
            "-strict":                "-2",
            "-max_muxing_queue_size": "512",
        }
        return valid_command

    @pytest.mark.unittest
    def test_can_generate_valid_ffmpeg_command(self):
        ffmpeg_cli = unffmpeg.cli
        command = ffmpeg_cli.ffmpeg_generate_valid_comand(self.valid_command())
        print(command)

    @pytest.mark.unittest
    def test_can_validate_command_schema(self):
        # Loop over settings object attributes
        command = self.valid_command()
        valid = unffmpeg.cli.validate_command(command)
        assert valid == command


if __name__ == '__main__':
    pytest.main(['-s', '--log-cli-level=DEBUG', __file__])
