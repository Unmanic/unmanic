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
import math
import os
import subprocess
import shutil
import re
import sys
import time

try:
    from unmanic.libs import common, unlogger, unffmpeg
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import common, unlogger, unffmpeg


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


class FFMPEGHandleConfigurationError(Exception):
    def __init___(self, required_setting, settings_dict):
        Exception.__init__(self, "Missing required setting {} in settings dict - {}".format(required_setting, settings_dict))
        self.required_setting = required_setting
        self.settings_dict = settings_dict


class FFMPEGHandle(object):
    process = None
    file_in = None
    file_out = None
    start_time = None
    total_frames = None
    duration = None
    src_fps = None
    elapsed = None
    time = None
    percent = None
    frame = None
    fps = None
    speed = None
    bitrate = None
    file_size = None
    ffmpeg_cmd_stdout = None

    def __init__(self, settings):
        self.name = 'FFMPEGHandle'
        # Ensure settings are complete
        self.settings = settings
        self.validate_settings()
        # Fetch supported containers
        self.supported_containers = unffmpeg.containers.get_all_containers()
        # Set class info to default values
        self.set_info_defaults()

    def validate_settings(self):
        required_settings = [
            'audio_codec',
            'audio_codec_cloning',
            'audio_stereo_stream_bitrate',
            'audio_stream_encoder',
            'cache_path',
            'debugging',
            'enable_audio_encoding',
            'enable_audio_stream_stereo_cloning',
            'enable_audio_stream_transcoding',
            'enable_video_encoding',
            'out_container',
            'remove_subtitle_streams',
            'video_codec',
            'video_stream_encoder',
            'overwrite_additional_ffmpeg_options',
            'additional_ffmpeg_options',
        ]
        setting_keys = self.settings.keys()
        for required_setting in required_settings:
            if required_setting not in self.settings:
                raise FFMPEGHandleConfigurationError(required_setting, self.settings)

    def set_info_defaults(self):
        self.file_in = {}
        self.file_out = {}
        self.start_time = time.time()
        self.total_frames = None
        self.duration = None
        self.src_fps = None
        self.elapsed = '0'
        self.time = '0'
        self.percent = '0'
        self.frame = '0'
        self.fps = '0'
        self.speed = '0'
        self.bitrate = '0'
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
        except KeyError:
            # Warning, Cannot use input Duration
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
        except KeyError:
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
            self._log("Unexpected exception in method process_file", str(e), level='exception')
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

    def check_file_to_be_processed(self, vid_file_path, settings):
        """
        Check if this file is already in the configured destination format.

        :param vid_file_path:
        :param settings:
        :return:
        """

        # Read the file's properties
        try:
            if not self.file_in and not self.set_file_in(vid_file_path):
                # Failed to fetch properties
                self._log("Failed to fetch properties of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
                return False
            file_probe = self.file_in['file_probe']
        except Exception as e:
            self._log("Exception in method check_file_to_be_processed when reading file in", str(e), level='exception')
            # Failed to fetch properties
            self._log("Failed to fetch properties of file {}".format(vid_file_path), level='debug')
            self._log("Marking file not to be processed", level='debug')
            return False

        # Check if the file container from it's properties matches the configured container
        correct_extension = False
        if not settings.get('keep_original_container'):
            try:
                # Get the list of possible file extensions from the ffprobe
                current_possible_format_names = file_probe['format']['format_name'].split(",")
                self._log("Current file format names:", current_possible_format_names, level='debug')

                # Get container extension
                container = unffmpeg.containers.grab_module(settings['out_container'])
                container_extension = container.container_extension()

                # Loop over file extensions to check if it is already one used by our configured container.
                for format_name in current_possible_format_names:
                    extension = 'NONE SELECTED'
                    if format_name in self.supported_containers:
                        extension = self.supported_containers[format_name]['extension']
                    if extension == container_extension:
                        self._log("File already in container format {} - {}".format(container_extension, vid_file_path),
                                  level='debug')
                        # This extension is used by our configured container.
                        # We will assume that we are already the correct container
                        correct_extension = True

                # If this is not in the correct extension, then log it. This file may be added to the conversion list
                if not correct_extension:
                    self._log("Current file format names do not match the configured extension {}".format(container_extension),
                              level='debug')
            except Exception as e:
                self._log("Exception in method check_file_to_be_processed. check file container", str(e), level='exception')
                # Failed to fetch properties
                self._log("Failed to read format of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
                return False
        else:
            correct_extension = True

        # Check if the file video codec from it's properties matches the configured video codec
        correct_video_codec = False
        if settings['enable_video_encoding']:
            try:
                video_streams_codecs = ""
                for stream in file_probe['streams']:
                    if stream['codec_type'] == 'video':
                        # Check if this file is already the right format
                        if video_streams_codecs:
                            video_streams_codecs += "{},{}".format(video_streams_codecs, stream['codec_name'])
                        else:
                            video_streams_codecs += "{}".format(stream['codec_name'])
                        # Ignore certain codec types (images)
                        if stream['codec_name'] in ['mjpeg']:
                            continue
                        # Check if codec name is the same as the one configured
                        if stream['codec_name'] == settings['video_codec']:
                            self._log(
                                "File already has {} codec video stream - {}".format(settings['video_codec'], vid_file_path),
                                level='debug')
                            correct_video_codec = True
                if not correct_video_codec:
                    self._log("The current file's video streams ({}) do not match the configured video codec ({})".format(
                        video_streams_codecs, settings['video_codec']), level='debug')
            except Exception as e:
                # Failed to fetch properties
                self._log("Exception in method check_file_to_be_processed. Check video codec.", str(e),
                          level='exception')
                self._log("Failed to read codec info of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
                return False
        else:
            correct_video_codec = True

        correct_audio_codec = False
        if settings.get('enable_audio_encoding') and settings.get('enable_audio_stream_transcoding'):
            try:
                audio_streams_codecs = ""
                for stream in file_probe['streams']:
                    if stream['codec_type'] == 'audio':
                        # Check if this file is already the right format
                        if audio_streams_codecs:
                            audio_streams_codecs += "{},{}".format(audio_streams_codecs, stream['codec_name'])
                        else:
                            audio_streams_codecs += "{}".format(stream['codec_name'])
                        if stream['codec_name'] == settings['audio_codec']:
                            self._log(
                                "File already has {} codec audio stream - {}".format(settings['audio_codec'], vid_file_path),
                                level='debug')
                            correct_audio_codec = True
                if not audio_streams_codecs:
                    # File does not contain any audio streams
                    self._log("File does not contain any audio streams - {}".format(vid_file_path), level='debug')
                    correct_audio_codec = True
                if not correct_audio_codec:
                    self._log(
                        "The current file's audio streams ({}) do not match the configured audio codec ({})".format(
                            audio_streams_codecs, settings['audio_codec']), level='debug')
            except Exception as e:
                # Failed to fetch properties
                self._log("Exception in method check_file_to_be_processed. Check audio codec.", str(e),
                          level='exception')
                self._log("Failed to read codec info of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
                return False
        else:
            correct_audio_codec = True

        # Finally ensure that all file properties match the configured values.
        if correct_extension and correct_video_codec and correct_audio_codec:
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
                if stream['codec_name'] == self.settings['video_codec']:
                    result = True
                else:
                    raise FFMPEGHandlePostProcessError(self.settings['video_codec'], stream['codec_name'])
                # TODO: Test duration is the same as src
        return result

    def process_file_with_configured_settings(self, vid_file_path):
        # Parse input path
        src_file = os.path.basename(vid_file_path)
        src_path = os.path.abspath(vid_file_path)
        src_folder = os.path.dirname(src_path)

        # Get container extension
        container = unffmpeg.containers.grab_module(self.settings['out_container'])
        container_extension = container.container_extension()

        # Parse an output cache path
        out_folder = "unmanic_file_conversion-{}".format(time.time())
        out_file = "{}-{}.{}".format(os.path.splitext(src_file)[0], time.time(), container_extension)
        out_path = os.path.join(self.settings['cache_path'], out_folder, out_file)

        # Create output path if not exists
        common.ensure_dir(out_path)

        # Reset all info
        self.set_info_defaults()

        # Fetch file info
        self.set_file_in(vid_file_path)

        # Convert file
        success = False
        # Read video information for the input file
        file_probe = self.file_in['file_probe']
        if not file_probe:
            return False
        ffmpeg_args = self.generate_ffmpeg_args(file_probe, src_path, out_path)
        if ffmpeg_args:
            success = self.convert_file_and_fetch_progress(src_path, ffmpeg_args)
        if success:
            # Move file back to original folder and remove source
            success = self.post_process_file(out_path)
            if success:
                destPath = os.path.join(src_folder, out_file)
                self._log("Moving file {} --> {}".format(out_path, destPath))
                shutil.move(out_path, destPath)
                try:
                    self.post_process_file(destPath)
                except FFMPEGHandlePostProcessError as e:
                    self._log("File is the not correct codec. {}".format(e), level='exception')
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

    def generate_ffmpeg_args(self, file_probe, in_file, out_file):
        # ffmpeg -i /library/XXXXX.mkv \
        #     -c:v libx265 \
        #     -map 0:0 -map 0:1 -map 0:1 \
        #     -c:a:0 copy \
        #     -c:a:1 libmp3lame -b:a:0 192k -ac 2 \
        #     -y /cache/XXXXX.mkv
        #

        # current_container = unffmpeg.containers.grab_module(self.settings['out_container'])
        destination_container = unffmpeg.containers.grab_module(self.settings['out_container'])

        # Suppress printing banner. (-hide_banner)
        # Set loglevel to info ("-loglevel", "info")
        # Allow experimental encoder config ("-strict", "-2")
        # Fix issue - 'Too many packets buffered for output stream 0:1' ("-max_muxing_queue_siz", "2048")
        #       REF: [https://trac.ffmpeg.org/ticket/6375]
        #
        main_options = ["-hide_banner", "-loglevel", "info", "-strict", "-2"]
        # Configure Advanced options: https://ffmpeg.org/ffmpeg.html#Advanced-options
        # These are added after the input file
        advanced_options = ["-max_muxing_queue_size", "2048"]
        command = []

        # Hardware acceleration args
        hardware_acceleration = unffmpeg.HardwareAccelerationHandle(file_probe)
        if self.settings['enable_video_encoding']:
            hardware_acceleration.video_encoder = self.settings['video_stream_encoder']
        # Check if hardware decoding is enabled
        if self.settings['enable_hardware_accelerated_decoding']:
            hardware_acceleration.enable_hardware_accelerated_decoding = True
            # The "Enable HW Decoding" checkbox is selected...
            # Loop over available decoders to select the best match for the current settings...
            for hardware_device in hardware_acceleration.get_hwaccel_devices():
                # TODO: in the future perhaps add a feature to be able to select which decoder to use.

                # First select the first one in the list (if nothing else matches, this one will be used)
                if hardware_acceleration.hardware_device is None:
                    hardware_acceleration.hardware_device = hardware_device

                # If we have enabled a HW accelerated encoder, then attempt to match the decoder with it.
                hwaccel = hardware_acceleration.hardware_device.get('hwaccel')
                if "vaapi" in self.settings['video_stream_encoder'] and hwaccel == "vaapi":
                    hardware_acceleration.hardware_device = hardware_device
                    break
                elif "nvenc" in self.settings['video_stream_encoder'] and hwaccel == "cuda":
                    hardware_acceleration.hardware_device = hardware_device
                    break
                continue
        hardware_acceleration.set_hwaccel_args()
        main_options = hardware_acceleration.update_main_options(main_options)
        advanced_options = hardware_acceleration.update_advanced_options(advanced_options)

        # Read stream data
        streams_to_map = []
        streams_to_encode = []

        # Set video encoding args
        video_codec_handle = unffmpeg.VideoCodecHandle(file_probe)
        if not self.settings['enable_video_encoding']:
            video_codec_handle.disable_video_encoding = True
        # Set video codec and encoder
        video_codec_handle.video_codec = self.settings['video_codec']
        video_codec_handle.video_encoder = self.settings['video_stream_encoder']
        video_codec_args = video_codec_handle.args()
        streams_to_map = streams_to_map + video_codec_args['streams_to_map']
        streams_to_encode = streams_to_encode + video_codec_args['streams_to_encode']

        # Set audio encoding args
        audio_codec_handle = unffmpeg.AudioCodecHandle(file_probe)
        if not self.settings['enable_audio_encoding']:
            audio_codec_handle.disable_audio_encoding = True
        # Are we transcoding audio streams to a configured codec?
        audio_codec_handle.enable_audio_stream_transcoding = self.settings['enable_audio_stream_transcoding']
        audio_codec_handle.audio_codec_transcoding = self.settings['audio_codec']
        audio_codec_handle.audio_encoder_transcoding = self.settings['audio_stream_encoder']
        # Are we cloning audio streams to stereo streams?
        audio_codec_handle.enable_audio_stream_stereo_cloning = self.settings['enable_audio_stream_stereo_cloning']
        audio_codec_handle.set_audio_codec_with_default_encoder_cloning(self.settings['audio_codec_cloning'])
        audio_codec_handle.audio_stereo_stream_bitrate = self.settings['audio_stereo_stream_bitrate']
        # Fetch args
        audio_codec_args = audio_codec_handle.args()
        streams_to_map = streams_to_map + audio_codec_args['streams_to_map']
        streams_to_encode = streams_to_encode + audio_codec_args['streams_to_encode']

        # Set subtitle encoding args
        subtitle_handle = unffmpeg.SubtitleHandle(file_probe, destination_container)
        if self.settings['remove_subtitle_streams']:
            subtitle_handle.remove_subtitle_streams = True
        subtitle_args = subtitle_handle.args()
        streams_to_map = streams_to_map + subtitle_args['streams_to_map']
        streams_to_encode = streams_to_encode + subtitle_args['streams_to_encode']

        # Overwrite additional options
        if self.settings['overwrite_additional_ffmpeg_options']:
            advanced_options = self.settings['additional_ffmpeg_options'].split()

        # Add main options to command
        command = command + main_options

        # Add input file
        command = command + ['-i', in_file]

        # Add advanced options to command
        command = command + advanced_options

        # Map streams
        command = command + streams_to_map

        # Add arguments for creating streams
        command = command + streams_to_encode

        # Add output file
        command = command + ['-y', out_file]

        return command

    def convert_file_and_fetch_progress(self, infile, args):
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
        command = ['ffmpeg'] + args
        self._log("Executing: {}".format(' '.join(command)), level='debug')

        # Log the start time
        self.start_time = time.time()

        # If we have probed both the source FPS and total duration, then we can calculate the total frames
        if self.duration and self.src_fps and self.duration > 0 and self.src_fps > 0:
            self.total_frames = int(self.duration * self.src_fps)

        # Execute command
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True, errors='replace')

        # Reset cmd stdout
        self.ffmpeg_cmd_stdout = [
            '\n\n',
            'COMMAND:\n',
            ' '.join(command),
            '\n\n',
            'LOG:\n',
        ]

        # Poll process for new output until finished
        while True:
            line_text = self.process.stdout.readline()

            # Fetch ffmpeg stdout and append it to the current task object (to be saved during post process)
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
        self.elapsed = str(time.time() - self.start_time)

        # Calculate elapsed time
        if line_text and 'frame=' in line_text:
            # Update time
            _time = self.get_progress_from_regex_of_string(line_text, r"time=(\s+|)(\d+:\d+:\d+\.\d+)", self.time)
            if _time:
                self.time = str(common.time_string_to_seconds(_time))

            # Update frames
            _frame = self.get_progress_from_regex_of_string(line_text, r"frame=(\s+|)(\d+)", self.frame)
            if _frame and int(_frame) > int(self.frame):
                self.frame = _frame

            # Update speed
            _speed = self.get_progress_from_regex_of_string(line_text, r"speed=(\s+|)(\d+\.\d+)", self.speed)
            if _speed:
                self.speed = str(_speed)

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
            if _frame and self.total_frames and int(_frame) > 0 and int(self.total_frames) > 0:
                # If we have both the current frame and the total number of frames, then we can easily calculate the %
                #_percent = float(int(_frame) / int(self.total_frames))
                _percent = float(int(_frame) / int(self.total_frames)) * 100
                _percent = math.trunc(_percent)
            elif self.time and self.duration and int(self.time) > 0 and int(self.duration) > 0:
                # If that was not successful, we need to resort to assuming the percent by the duration and the time
                # passed so far
                _percent = float(int(self.time) / int(self.duration)) * 100
                _percent = math.trunc(_percent)
            if _percent and int(_percent) > int(self.percent):
                self.percent = str(_percent)

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
