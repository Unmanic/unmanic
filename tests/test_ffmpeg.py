#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_ffmpeg.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 Sep 2019, (9:07 AM)
 
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
import shutil
import sys

try:
    from lib import common, unlogger, ffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from lib import common, unlogger, ffmpeg


class TestClass(object):
    """
    TestClass

    Runs unit tests against the ffmpeg class

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
        # import config
        import config
        self.settings = config.CONFIG()
        self.settings.DEBUGGING = True
        self.ffmpeg = ffmpeg.FFMPEGHandle(self.settings)

    def _log(self, message, message2='', level="info"):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger('TestClass')
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format('TestClass'))

    def build_ffmpeg_args(self, test_for_failure=False):
        configured_vencoder = self.settings.SUPPORTED_CODECS[self.settings.VIDEO_CODEC]['encoder']
        failure_vencoder = None
        for x in self.settings.SUPPORTED_CODECS:
            if x != self.settings.VIDEO_CODEC:
                failure_vencoder = self.settings.SUPPORTED_CODECS[x]['encoder']
                break
        if test_for_failure:
            vencoder = failure_vencoder
            self._log("Using encoder {} to setup failure condition".format(vencoder))
        else:
            vencoder = configured_vencoder
            self._log("Using encoder {} to setup success condition".format(vencoder))
        # Setup default args
        args = [
            '-hide_banner',
            '-loglevel',
            'info',
            '-strict',
            '-2',
            '-map',
            '0:0',
            '-map',
            ' 0:1',
            '-c:v',
            vencoder,
            '-c:a:0',
            'aac',
            '-b:a:0',
            '128k',
            '-ac',
            '2',
        ]
        return args

    def convert_single_file(self, infile, outfile, test_for_failure=False):
        if not os.path.exists(infile):
            self._log("No such file: {}".format(infile))
            sys.exit(1)
        # Ensure the directory exists
        common.ensure_dir(outfile)
        # Remove the output file if it already exists
        if os.path.exists(outfile):
            os.remove(outfile)
        # Setup ffmpeg args
        built_args = self.build_ffmpeg_args(test_for_failure)
        # Run conversion process
        self._log("Converting {} -> {}".format(infile, outfile))
        # Fetch file info
        self.ffmpeg.set_file_in(infile)
        assert self.ffmpeg.convert_file_and_fetch_progress(infile, outfile, built_args)
        if not test_for_failure:
            assert self.ffmpeg.post_process_file(outfile)
        elif test_for_failure:
            import pytest
            with pytest.raises(ffmpeg.FFMPEGHandlePostProcessError):
                self.ffmpeg.post_process_file(outfile)

    def test_process_file_for_success(self):
        # Set project root path
        tests_dir = os.path.join(self.project_dir, 'tests')
        tmp_dir = os.path.join(tests_dir, 'tmp')
        # Test just the first file found in the med folder
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'med')):
            filename, file_extension = os.path.splitext(os.path.basename(video_file))
            infile = os.path.join(tests_dir, 'videos', 'med', video_file)
            # Copy the file to a tmp location (it will be replaced)
            testfile = os.path.join(tmp_dir, filename + file_extension)
            self._log(infile, testfile)
            shutil.copy(infile, testfile)
            assert self.ffmpeg.process_file_with_configured_settings(testfile)
            break

    def test_read_file_info_for_success(self):
        # Set project root path
        tests_dir = os.path.join(self.project_dir, 'tests')
        # Test
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'small')):
            infile = os.path.join(tests_dir, 'videos', 'small', video_file)
            assert self.ffmpeg.file_probe(infile)

    def test_read_file_info_for_failure(self):
        # Set project root path
        tests_dir = os.path.join(self.project_dir, 'tests')
        tmp_dir = os.path.join(tests_dir, 'tmp')
        fail_file = os.path.join(tmp_dir, 'test_failure.mkv')
        # Test
        common.touch(fail_file)
        import pytest
        with pytest.raises(ffmpeg.FFMPEGHandleFFProbeError):
            self.ffmpeg.file_probe(fail_file)

    def test_file_not_target_format_for_success(self):
        """
        This modifies the self.settings.VIDEO_CODEC to an incorrect video codec.
        self.setup_class() is called at the end of this function to return the
        settings back to their original state.
        :return:
        """
        self.setup_class()
        # Set project root path
        tests_dir = os.path.join(self.project_dir, 'tests')
        # Test
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'small')):
            should_convert = True
            pathname = os.path.join(tests_dir, 'videos', 'small', video_file)
            file_probe = self.ffmpeg.file_probe(pathname)
            # Ensure the file probe was successful
            assert 'format' in file_probe
            assert 'streams' in file_probe
            # Check for our test mkv file, this file should be set not to need a conversion.
            # The default OUT_CONTAINER os 'matroska'. If this video is already 'matroska',
            # then is should not need converting again.
            if 'matroska' in file_probe['format']['format_name']:
                should_convert = False
                for stream in file_probe['streams']:
                    if stream['codec_type'] == 'video':
                        self.settings.VIDEO_CODEC = stream['codec_name']
            # Reset file in
            self.ffmpeg.file_in = {}
            # Check that the check_file_to_be_processed function correctly identifies the file to be converted
            convert = self.ffmpeg.check_file_to_be_processed(pathname)
            assert (should_convert == convert)
        self.setup_class()

    def test_convert_all_files_for_success(self):
        # Set project root path
        tests_dir = os.path.join(self.project_dir, 'tests')
        tmp_dir = os.path.join(tests_dir, 'tmp')
        # Test all small files of various containers
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'small')):
            filename, file_extension = os.path.splitext(os.path.basename(video_file))
            infile = os.path.join(tests_dir, 'videos', 'small', video_file)
            outfile = os.path.join(tmp_dir, filename + '.mkv')
            self.convert_single_file(infile, outfile)

    def test_convert_all_faulty_files_for_success(self):
        # Set project root path
        tests_dir = os.path.join(self.project_dir, 'tests')
        tmp_dir = os.path.join(tests_dir, 'tmp')
        # Test all faulty files can be successfully converted (these files have assorted issues)
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'faulty')):
            filename, file_extension = os.path.splitext(os.path.basename(video_file))
            infile = os.path.join(tests_dir, 'videos', 'faulty', video_file)
            outfile = os.path.join(tmp_dir, filename + '.mkv')
            self.convert_single_file(infile, outfile)

