#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.ffmpeg.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     03 Jan 2019, (11:23 AM)

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
import subprocess
import json
import shutil
import re
import sys
import time

try:
    from lib import common, unlogger, unffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from lib import common, unlogger, unffmpeg


class FFMPEGHandlePostProcessError(Exception):
    def __init___(self, expected_var, result_var):
        Exception.__init__(self, "Errors found during post process checks. Expected {}, but instead found {}".format(
            expected_var, result_var))
        self.expected_var = expected_var
        self.result_var = result_var


class FFMPEGHandleConversionError(Exception):
    def __init___(self, command):
        Exception.__init__(self, "FFMPEG command returned non 0 status. Command: {}".format(command))
        self.command = command


class FFMPEGHandle(object):
    def __init__(self, settings):
        self.name = 'FFMPEGHandle'
        self.settings = settings
        self.process = None
        self.file_in = None
        self.file_out = None
        self.start_time = None
        self.total_frames = None
        self.duration = None
        self.src_fps = None
        self.elapsed = None
        self.time = None
        self.percent = None
        self.frame = None
        self.fps = None
        self.speed = None
        self.bitrate = None
        self.file_size = None
        self.ffmpeg_cmd_stdout = None

        self.set_info_defaults()

    def set_info_defaults(self):
        self.file_in = {}
        self.file_out = {}
        self.start_time = time.time()
        self.total_frames = None
        self.duration = None
        self.src_fps = None
        self.elapsed = 0
        self.time = 0
        self.percent = 0
        self.frame = 0
        self.fps = 0
        self.speed = 0
        self.bitrate = 0
        self.file_size = None
        self.ffmpeg_cmd_stdout = []

    def _log(self, message, message2='', level="info"):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(self.name)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.name))

    def file_probe(self, vid_file_path):
        """
        Give a json from ffprobe command line

        :param vid_file_path: The absolute (full) path of the video file, string.
        :return:
        """
        # Get the file probe info
        probe_info = unffmpeg.Info().file_probe(vid_file_path)

        # Get FPS from file probe info
        self.src_fps = None
        try:
            self.src_fps = eval(probe_info['streams'][0]['avg_frame_rate'])
        except ZeroDivisionError:
            # Warning, Cannot use input FPS
            self._log('Warning, Cannot use input FPS', level='warning')
        if self.src_fps == 0:
            raise ValueError('Unexpected zero FPS')

        # Get Duration from file probe info
        self.duration = None
        try:
            self.duration = float(probe_info['format']['duration'])
        except ZeroDivisionError:
            # Warning, Cannot use input Duration
            self._log('Warning, Cannot use input Duration', level='warning')

        if self.src_fps is None and self.duration is None:
            raise ValueError('Unable to match against FPS or Duration.')

        return probe_info

    def set_file_in(self, vid_file_path):
        """
        Set the file in property

        :param vid_file_path:
        :return:
        """
        # Fetch file info
        try:
            self.file_in['abspath'] = vid_file_path
            self.file_in['file_probe'] = self.file_probe(vid_file_path)
            return True
        except unffmpeg.exceptions.ffprobe.FFProbeError as e:
            self._log("Exception in method process_file", str(e), level='exception')
            return False
        except Exception as e:
            self._log("Exception in method process_file", str(e), level='exception')
            return False

    def set_file_out(self, vid_file_path):
        """
        Set the file out property

        :param vid_file_path:
        :return:
        """
        # Fetch file info
        try:
            self.file_out['abspath'] = vid_file_path
            self.file_out['file_probe'] = self.file_probe(vid_file_path)
            return True
        except unffmpeg.exceptions.ffprobe.FFProbeError as e:
            self._log("Exception in method set_file_out", str(e), level='exception')
            return False
        except Exception as e:
            self._log("Exception in method set_file_out", str(e), level='exception')
            return False

    def get_current_video_codecs(self, file_properties):
        codecs = []
        for stream in file_properties['streams']:
            if stream['codec_type'] == 'video':
                codecs.append(stream['codec_name'])
        return codecs

    def check_file_to_be_processed(self, vid_file_path):
        """
        Check if this file is already in the configured destination format.

        :param vid_file_path:
        :return:
        """
        # TODO: Add variable to force conversion based on audio config also

        # Read the file's properties
        try:
            if not self.file_in and not self.set_file_in(vid_file_path):
                # Failed to fetch properties
                if self.settings.DEBUGGING:
                    self._log("Failed to fetch properties of file {}".format(vid_file_path), level='debug')
                    self._log("Marking file not to be processed", level='debug')
                return False
            file_probe = self.file_in['file_probe']
        except Exception as e:
            self._log("Exception in method check_file_to_be_processed when reading file in", str(e), level='exception')
            # Failed to fetch properties
            if self.settings.DEBUGGING:
                self._log("Failed to fetch properties of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
            return False

        # Check if the file container from it's properties matches the configured container
        correct_extension = False
        try:
            # Get the list of possible file extensions from the ffprobe
            current_possible_format_names = file_probe['format']['format_name'].split(",")
            if self.settings.DEBUGGING:
                self._log("Current file format names:", current_possible_format_names, level='debug')

            # Get container extension
            container = unffmpeg.containers.grab_module(self.settings.OUT_CONTAINER)
            container_extension = container.container_extension()

            # Loop over file extensions to check if it is already one used by our configured container.
            for format_name in current_possible_format_names:
                extension = 'NONE SELECTED'
                if format_name in self.settings.SUPPORTED_CONTAINERS:
                    extension = self.settings.SUPPORTED_CONTAINERS[format_name]['extension']
                if extension == container_extension:
                    if self.settings.DEBUGGING:
                        self._log("File already in container format {} - {}".format(container_extension,
                                                                                    vid_file_path), level='debug')
                    # This extension is used by our configured container.
                    # We will assume that we are already the correct container
                    correct_extension = True

            # If this is not in the correct extension, then log it. This file may be added to the conversion list
            if not correct_extension and self.settings.DEBUGGING:
                self._log("Current file format names do not match the configured extension {}".format(
                    container_extension), level='debug')
        except Exception as e:
            self._log("Exception in method check_file_to_be_processed. check file container", str(e), level='exception')
            # Failed to fetch properties
            if self.settings.DEBUGGING:
                self._log("Failed to read format of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
            return False

        # Check if the file video codec from it's properties matches the configured video codec
        correct_video_codec = False
        if self.settings.ENABLE_VIDEO_ENCODING:
            try:
                video_streams_codecs = ""
                for stream in file_probe['streams']:
                    if stream['codec_type'] == 'video':
                        # Check if this file is already the right format
                        video_streams_codecs += "{},{}".format(video_streams_codecs, stream['codec_name'])
                        if stream['codec_name'] == self.settings.VIDEO_CODEC:
                            if self.settings.DEBUGGING:
                                self._log("File already has {} codec video stream - {}".format(self.settings.VIDEO_CODEC, vid_file_path),
                                          level='debug')
                            correct_video_codec = True
                if not correct_video_codec:
                    if self.settings.DEBUGGING:
                        self._log(
                            "The current file's video streams ({}) do not match the configured video codec ({})".format(
                                video_streams_codecs, self.settings.VIDEO_CODEC), level='debug')
            except Exception as e:
                # Failed to fetch properties
                self._log("Exception in method check_file_to_be_processed. Check video codec.", str(e),
                          level='exception')
                if self.settings.DEBUGGING:
                    self._log("Failed to read codec info of file {}".format(vid_file_path), level='debug')
                    self._log("Marking file not to be processed", level='debug')
                return False
        else:
            correct_video_codec = True

        # Finally ensure that all file properties match the configured values.
        if correct_extension and correct_video_codec:
            # This file is already the correct container and codec
            return False
        # File did not match, it will need to be added to the queue for processing
        return True

    def post_process_file(self, vid_file_path):
        try:
            self.file_out = self.file_probe(vid_file_path)
        except unffmpeg.exceptions.ffprobe.FFProbeError as e:
            self._log("Exception in method post_process_file", str(e), level='exception')
            return False
        except Exception as e:
            self._log("Exception in method post_process_file", str(e), level='exception')
            return False

        # Ensure file is correct format
        result = False
        for stream in self.file_out['streams']:
            if stream['codec_type'] == 'video':
                # Check if this file is the right codec
                if stream['codec_name'] == self.settings.VIDEO_CODEC:
                    result = True
                elif self.settings.DEBUGGING:
                    self._log("File is the not correct codec {} - {}".format(self.settings.VIDEO_CODEC,vid_file_path))
                    raise FFMPEGHandlePostProcessError(self.settings.VIDEO_CODEC, stream['codec_name'])
                # TODO: Test duration is the same as src
        return result

    def process_file_with_configured_settings(self, vid_file_path):
        # Parse input path
        src_file = os.path.basename(vid_file_path)
        src_path = os.path.abspath(vid_file_path)
        src_folder = os.path.dirname(src_path)

        # Get container extension
        container = unffmpeg.containers.grab_module(self.settings.OUT_CONTAINER)
        container_extension = container.container_extension()

        # Parse an output cache path
        out_folder = "file_conversion-{}".format(time.time())
        out_file = "{}-{}.{}".format(os.path.splitext(src_file)[0], time.time(), container_extension)
        out_path = os.path.join(self.settings.CACHE_PATH, out_folder, out_file)

        # Create output path if not exists 
        common.ensure_dir(out_path)

        # Reset all info
        self.set_info_defaults()

        # Fetch file info
        self.set_file_in(vid_file_path)

        # Convert file
        success = False
        ffmpeg_args = self.generate_ffmpeg_args()
        if ffmpeg_args:
            success = self.convert_file_and_fetch_progress(src_path, out_path, ffmpeg_args)
        if success:
            # Move file back to original folder and remove source
            success = self.post_process_file(out_path)
            if success:
                destPath = os.path.join(src_folder, out_file)
                self._log("Moving file {} --> {}".format(out_path, destPath))
                shutil.move(out_path, destPath)
                try:
                    self.post_process_file(destPath)
                except FFMPEGHandlePostProcessError:
                    success = False
                if success:
                    # If successful move, remove source
                    # TODO: Add env variable option to keep src
                    if src_path != destPath:
                        self._log("Removing source: {}".format(src_path))
                        os.remove(src_path)
                else:
                    self._log("Copy / Replace failed during post processing '{}'".format(out_path), level='warning')
                    return False
            else:
                self._log("Encoded file failed post processing test '{}'".format(out_path), level='warning')
                return False
        else:
            self._log("Failed processing file '{}'".format(src_path), level='warning')
            return False
        # If file conversion was successful, we will get here
        self._log("Successfully processed file '{}'".format(src_path))
        return True

    def generate_ffmpeg_args(self,):
        # ffmpeg -i /library/XXXXX.mkv \
        #     -c:v libx265 \
        #     -map 0:0 -map 0:1 -map 0:1 \
        #     -c:a:0 copy \
        #     -c:a:1 libmp3lame -b:a:0 192k -ac 2 \
        #     -y /cache/XXXXX.mkv
        # 

        # Read video information for the input file
        file_probe = self.file_in['file_probe']
        if not file_probe:
            return False

        # current_container = unffmpeg.containers.grab_module(self.settings.OUT_CONTAINER)
        destination_container = unffmpeg.containers.grab_module(self.settings.OUT_CONTAINER)

        # Suppress printing banner. (-hide_banner)
        # Set loglevel to info ("-loglevel", "info")
        # Allow experimental encoder config ("-strict", "-2")
        # 
        command = ["-hide_banner", "-loglevel", "info", "-strict", "-2", "-max_muxing_queue_size", "512"]

        # Read stream data
        streams_to_map = []
        streams_to_encode = []

        # Set video encoding args
        video_codec_handle = unffmpeg.VideoCodecHandle(file_probe)
        if not self.settings.ENABLE_VIDEO_ENCODING:
            video_codec_handle.disable_video_encoding = True
        video_codec_handle.set_video_codec(self.settings.VIDEO_CODEC)
        video_codec_args = video_codec_handle.args()
        streams_to_map = streams_to_map + video_codec_args['streams_to_map']
        streams_to_encode = streams_to_encode + video_codec_args['streams_to_encode']

        # Set audio encoding args
        audio_codec_handle = unffmpeg.AudioCodecHandle(file_probe)
        if not self.settings.ENABLE_AUDIO_ENCODING:
            audio_codec_handle.disable_audio_encoding = True
        # Are we transcoding audio streams to a configured codec?
        audio_codec_handle.enable_audio_stream_transcoding = self.settings.ENABLE_AUDIO_STREAM_TRANSCODING
        audio_codec_handle.audio_codec_transcoding = self.settings.AUDIO_CODEC
        audio_codec_handle.audio_encoder_transcoding = self.settings.AUDIO_STREAM_ENCODER
        # Are we cloning audio streams to stereo streams?
        audio_codec_handle.enable_audio_stream_stereo_cloning = self.settings.ENABLE_AUDIO_STREAM_STEREO_CLONING
        audio_codec_handle.set_audio_codec_with_default_encoder_cloning(self.settings.AUDIO_CODEC_CLONING)
        audio_codec_handle.audio_stereo_stream_bitrate = self.settings.AUDIO_STEREO_STREAM_BITRATE
        # Fetch args
        audio_codec_args = audio_codec_handle.args()
        streams_to_map = streams_to_map + audio_codec_args['streams_to_map']
        streams_to_encode = streams_to_encode + audio_codec_args['streams_to_encode']

        # Set subtitle encoding args
        subtitle_handle = unffmpeg.SubtitleHandle(file_probe, destination_container)
        if self.settings.REMOVE_SUBTITLE_STREAMS:
            subtitle_handle.remove_subtitle_streams = True
        subtitle_args = subtitle_handle.args()
        streams_to_map = streams_to_map + subtitle_args['streams_to_map']
        streams_to_encode = streams_to_encode + subtitle_args['streams_to_encode']

        # Map streams
        command = command + streams_to_map

        # Add arguments for creating streams
        command = command + streams_to_encode

        self._log(" ".join(command), level='debug')

        return command

    def convert_file_and_fetch_progress(self, infile, outfile, args):
        if not self.file_in['file_probe']:
            try:
                self.file_in['file_probe'] = self.file_probe(infile)
            except unffmpeg.exceptions.ffprobe.FFProbeError as e:
                self._log("Exception in method convert_file_and_fetch_progress", str(e), level='exception')
                return False
            except Exception as e:
                self._log("Exception in method convert_file_and_fetch_progress", str(e), level='exception')
                return False

        # Create command with infile, outfile and the arguments
        command = ['ffmpeg', '-y', '-i', infile] + args + ['-y', outfile]
        if self.settings.DEBUGGING:
            self._log("Executing: {}".format(' '.join(command)), level='debug')

        # Log the start time
        self.start_time = time.time()

        # If we have probed both the source FPS and total duration, then we can calculate the total frames
        if self.duration and self.src_fps and self.duration > 0 and self.src_fps > 0:
            self.total_frames = int(self.duration * self.src_fps)

        # Execute command
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True)

        # Reset cmd stdout
        self.ffmpeg_cmd_stdout = []

        # Poll process for new output until finished
        while True:
            line_text = self.process.stdout.readline()
            # Add line to stdout list. This is used for debugging the process if something goes wrong
            if self.settings.DEBUGGING:
                # Fetch ffmpeg stdout and append it to the current task object (to be saved during post process)
                # This adds a fair amount of data to the database. It is not ideal to do this
                # for every task unless the user really needs it.
                # TODO: Add config options to save this data instead of relying on debugging.
                #  We could filter it here so that it does not include the lines starting with 'frame='
                #  in order to reduce the amount of data needing to be saved.
                self.ffmpeg_cmd_stdout.append(line_text)
            if line_text == '' and self.process.poll() is not None:
                break
            # parse the progress
            try:
                self.parse_conversion_progress(line_text)
            except Exception as e:
                # Only need to show any sort of exception if we have debugging enabled.
                # So we should log it as a debug rather than an exception.
                self._log("Exception in method parse_conversion_progress", str(e), level='debug')

        # Get the final output and the exit status
        self.process.communicate()[0]
        if self.process.returncode == 0:
            return True
        else:
            raise FFMPEGHandleConversionError(command)

    def parse_conversion_progress(self, line_text):
        """
        Use regex to pull progress data from process line text

        :param line_text:
        :return:
        """
        # Calculate elapsed time
        self.elapsed = (time.time() - self.start_time)

        # Calculate elapsed time
        if line_text and 'frame=' in line_text:
            # Update time
            _time = self.get_progress_from_regex_of_string(line_text, r"time=(\s+|)(\d+:\d+:\d+\.\d+)", self.time)
            if _time:
                self.time = common.time_string_to_seconds(_time)

            # Update frames
            _frame = float(self.get_progress_from_regex_of_string(line_text, r"frame=(\s+|)(\d+)", self.frame))
            if _frame and _frame > self.frame:
                self.frame = _frame

            # Update speed
            _speed = self.get_progress_from_regex_of_string(line_text, r"speed=(\s+|)(\d+\.\d+)", self.speed)
            if _speed:
                self.speed = _speed

            # Update bitrate
            _bitrate = self.get_progress_from_regex_of_string(line_text, r"bitrate=(\s+|)(\d+\.\d+\w+|\d+w)",
                                                              self.bitrate)
            if _bitrate:
                self.bitrate = "{}/s".format(_bitrate)

            # Update file size
            _size = self.get_progress_from_regex_of_string(line_text, r"size=(\s+|)(\d+\w+|\d+.\d+\w+)", self.frame)
            if _size:
                self.file_size = _size

            # Update percent
            _percent = None
            if self.frame and self.total_frames and self.frame > 0 and self.total_frames > 0:
                # If we have both the current frame and the total number of frames, then we can easily calculate the %
                _percent = int(int(self.frame) / int(self.total_frames) * 100)
            if not _percent and self.time and self.duration and self.time > 0 and self.duration > 0:
                # If that was not successful, we need to resort to assuming the percent by the duration and the time
                # passed so far
                _percent = int(int(self.time) / int(self.duration) * 100)
            if _percent and _percent > self.percent:
                self.percent = _percent

        # self._log("TOTAL: frames", self.total_frames, level='debug')
        # self._log("TOTAL: duration", self.duration, level='debug')
        # self._log("PROGRESS: elapsed time", self.elapsed, level='debug')
        # self._log("PROGRESS: seconds converted", self.time, level='debug')
        # self._log("PROGRESS: percent converted", self.percent, level='debug')
        # self._log("PROGRESS: frames converted", self.frame, level='debug')
        # self._log("PROGRESS: speed: {}x".format(self.speed), level='debug')
        # self._log("PROGRESS: bitrate", self.bitrate, level='debug')
        # self._log("PROGRESS: file size", self.file_size, level='debug')

    def get_progress_from_regex_of_string(self, line, regex_string, default=0):
        return_value = default
        regex = re.compile(regex_string)
        findall = re.findall(regex, line)
        if findall:
            split_list = findall[-1]
            if len(split_list) == 2:
                return_value = split_list[1].strip()
        return return_value

