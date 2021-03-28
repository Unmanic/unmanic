#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.filetest.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     28 Mar 2021, (7:28 PM)

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

from unmanic.libs import ffmpeg, history


class FileTest(object):
    """
    FileTest

    Object to manage tests carried out on files discovered
    during a library scan or inode event

    """

    def __init__(self, settings, path):
        self.settings = settings
        self.path = path

    def init_ffmpeg_handle_settings(self):
        return {
            'audio_codec':                          self.settings.get_config_item('audio_codec'),
            'audio_stream_encoder':                 self.settings.get_audio_stream_encoder(),
            'audio_codec_cloning':                  self.settings.get_audio_codec_cloning(),
            'audio_stereo_stream_bitrate':          self.settings.get_audio_stereo_stream_bitrate(),
            'cache_path':                           self.settings.get_cache_path(),
            'debugging':                            self.settings.get_debugging(),
            'enable_audio_encoding':                self.settings.get_enable_audio_encoding(),
            'enable_audio_stream_stereo_cloning':   self.settings.get_enable_audio_stream_stereo_cloning(),
            'enable_audio_stream_transcoding':      self.settings.get_enable_audio_stream_transcoding(),
            'enable_video_encoding':                self.settings.get_enable_video_encoding(),
            'out_container':                        self.settings.get_out_container(),
            'remove_subtitle_streams':              self.settings.get_remove_subtitle_streams(),
            'video_codec':                          self.settings.get_video_codec(),
            'video_stream_encoder':                 self.settings.get_video_stream_encoder(),
            'overwrite_additional_ffmpeg_options':  self.settings.get_overwrite_additional_ffmpeg_options(),
            'additional_ffmpeg_options':            self.settings.get_additional_ffmpeg_options(),
            'enable_hardware_accelerated_decoding': self.settings.get_enable_hardware_accelerated_decoding(),
        }

    def file_already_in_target_format(self):
        """
        Check if file is not the correct format

        :return:
        """
        # init FFMPEG handle
        ffmpeg_settings = self.init_ffmpeg_handle_settings()
        ffmpeg_handle = ffmpeg.FFMPEGHandle(ffmpeg_settings)
        # Reset file in
        ffmpeg_handle.file_in = {}
        # Check if file matches configured codec and format
        file_not_correct_format = ffmpeg_handle.check_file_to_be_processed(self.path, ffmpeg_settings)
        if file_not_correct_format:
            # File needs to be processed
            return False
        return True

    def file_failed_in_history(self):
        """
        Check if file has already failed in history

        :return:
        """
        # Fetch historical tasks
        history_logging = history.History(self.settings)
        task_results = history_logging.get_historic_tasks_list_with_source_probe(abspath=self.path, task_success=False)
        if not task_results:
            # No results were found matching that pathname
            return False
        # That pathname was found in the results of failed historic tasks
        return True

    def file_ends_in_allowed_search_extensions(self):
        """
        Check if the file is in the allowed search extensions

        :return:
        """
        # Get the file extension
        file_extension = os.path.splitext(self.path)[-1][1:]

        # Ensure the file's extension is lowercase
        file_extension = file_extension.lower()

        # Get the list of configured extensions to search for
        allowed_search_extensions = self.settings.allowed_search_extensions()

        # Check if it ends with one of the allowed search extensions
        if file_extension in allowed_search_extensions:
            return True
        return False

    def file_in_directory_containing_ignore_lockfile(self):
        """
        Check if folder contains a '.unmanicignore' lockfile

        :return:
        """
        # Get file parent directory
        directory = os.path.dirname(self.path)
        # Check if lockfile (.unmanicignore) exists
        if os.path.exists(os.path.join(directory, '.unmanicignore')):
            return True
        return False

    def should_file_be_added_to_task_list(self):
        """
        Test if this file needs to be added to the task list

        :return:
        """
        errors = []

        if self.file_in_directory_containing_ignore_lockfile():
            errors.append("File found in directory containing unmanic ignore file - '{}'".format(self.path))
            return False, errors

        if not self.file_ends_in_allowed_search_extensions():
            errors.append("File suffix is not in allowed search extensions - '{}'".format(self.path))
            return False, errors

        # Check if file has failed in history.
        if self.file_failed_in_history():
            errors.append("File found already failed in history - '{}'".format(self.path))
            return False, errors

        # Check if this file is already the correct format:
        if self.file_already_in_target_format():
            errors.append("File is already in target format - '{}'".format(self.path))
            return False, errors

        return True, errors
