#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jan 03 2019, (11:23:45 AM)
#
#   Copyright:
#          Copyright (C) Josh Sunnex - All Rights Reserved
#
#          Permission is hereby granted, free of charge, to any person obtaining a copy
#          of this software and associated documentation files (the "Software"), to deal
#          in the Software without restriction, including without limitation the rights
#          to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#          copies of the Software, and to permit persons to whom the Software is
#          furnished to do so, subject to the following conditions:
# 
#          The above copyright notice and this permission notice shall be included in all
#          copies or substantial portions of the Software.
# 
#          THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#          EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#          MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#          IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#          DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#          OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#          OR OTHER DEALINGS IN THE SOFTWARE.
#
#
###################################################################################################


import os
import subprocess
import json
import shutil
import re
import sys
import time
from datetime import datetime

import common


#      /$$$$$$$$                                           /$$     /$$                            /$$$$$$  /$$
#     | $$_____/                                          | $$    |__/                           /$$__  $$| $$
#     | $$       /$$   /$$  /$$$$$$$  /$$$$$$   /$$$$$$  /$$$$$$   /$$  /$$$$$$  /$$$$$$$       | $$  \__/| $$  /$$$$$$   /$$$$$$$ /$$$$$$$  /$$$$$$   /$$$$$$$
#     | $$$$$   |  $$ /$$/ /$$_____/ /$$__  $$ /$$__  $$|_  $$_/  | $$ /$$__  $$| $$__  $$      | $$      | $$ |____  $$ /$$_____//$$_____/ /$$__  $$ /$$_____/
#     | $$__/    \  $$$$/ | $$      | $$$$$$$$| $$  \ $$  | $$    | $$| $$  \ $$| $$  \ $$      | $$      | $$  /$$$$$$$|  $$$$$$|  $$$$$$ | $$$$$$$$|  $$$$$$
#     | $$        >$$  $$ | $$      | $$_____/| $$  | $$  | $$ /$$| $$| $$  | $$| $$  | $$      | $$    $$| $$ /$$__  $$ \____  $$\____  $$| $$_____/ \____  $$
#     | $$$$$$$$ /$$/\  $$|  $$$$$$$|  $$$$$$$| $$$$$$$/  |  $$$$/| $$|  $$$$$$/| $$  | $$      |  $$$$$$/| $$|  $$$$$$$ /$$$$$$$//$$$$$$$/|  $$$$$$$ /$$$$$$$/
#     |________/|__/  \__/ \_______/ \_______/| $$____/    \___/  |__/ \______/ |__/  |__/       \______/ |__/ \_______/|_______/|_______/  \_______/|_______/
#                                             | $$
#                                             | $$
#                                             |__/
class FFMPEGHandlePostProcessError(Exception):
    def __init___(self,expected_var,result_var):
        Exception.__init__(self,"Errors found during post process checks. Expected {}, but instead found {}".format(expected_var,result_var))
        self.expected_var   = expected_var
        self.result_var     = result_var


class FFMPEGHandleFFProbeError(Exception):
    def __init___(self,path,info):
        Exception.__init__(self,"Unable to fetch data from file {}. {}".format(path,info))
        self.path = path
        self.info = info


class FFMPEGHandleConversionError(Exception):
    def __init___(self,command,info):
        Exception.__init__(self,"FFMPEG command retunred non 0 status. Command: {}".format(command))
        self.command = command


#      /$$$$$$$$ /$$$$$$$$ /$$      /$$ /$$$$$$$  /$$$$$$$$  /$$$$$$        /$$   /$$                           /$$ /$$
#     | $$_____/| $$_____/| $$$    /$$$| $$__  $$| $$_____/ /$$__  $$      | $$  | $$                          | $$| $$
#     | $$      | $$      | $$$$  /$$$$| $$  \ $$| $$      | $$  \__/      | $$  | $$  /$$$$$$  /$$$$$$$   /$$$$$$$| $$  /$$$$$$   /$$$$$$
#     | $$$$$   | $$$$$   | $$ $$/$$ $$| $$$$$$$/| $$$$$   | $$ /$$$$      | $$$$$$$$ |____  $$| $$__  $$ /$$__  $$| $$ /$$__  $$ /$$__  $$
#     | $$__/   | $$__/   | $$  $$$| $$| $$____/ | $$__/   | $$|_  $$      | $$__  $$  /$$$$$$$| $$  \ $$| $$  | $$| $$| $$$$$$$$| $$  \__/
#     | $$      | $$      | $$\  $ | $$| $$      | $$      | $$  \ $$      | $$  | $$ /$$__  $$| $$  | $$| $$  | $$| $$| $$_____/| $$
#     | $$      | $$      | $$ \/  | $$| $$      | $$$$$$$$|  $$$$$$/      | $$  | $$|  $$$$$$$| $$  | $$|  $$$$$$$| $$|  $$$$$$$| $$
#     |__/      |__/      |__/     |__/|__/      |________/ \______/       |__/  |__/ \_______/|__/  |__/ \_______/|__/ \_______/|__/
#
#
#
class FFMPEGHandle(object):
    def __init__(self, settings, logging):
        self.name = 'FFMPEGHandle'
        self.logger = logging.get_logger(self.name)
        self.settings = settings
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

    def _log(self, message, message2 = '', level = "info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def file_probe(self, vid_file_path):
        ''' Give a json from ffprobe command line

        @vid_file_path : The absolute (full) path of the video file, string.
        '''
        if type(vid_file_path) != str:
            raise Exception('Give ffprobe a full file path of the video')

        command = ["ffprobe",
                "-loglevel",  "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                "-show_error",
                vid_file_path
            ]

        pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = pipe.communicate()

        # Check result
        try:
            info = json.loads(out.decode("utf-8"))
        except Exception as e: 
            self._log("Exception - file_probe: {}".format(e), level='exception')
            raise FFMPEGHandleFFProbeError(vid_file_path,str(e))
        if pipe.returncode == 1 or 'error' in info:
            raise FFMPEGHandleFFProbeError(vid_file_path, info)

        # Get FPS
        try:
            # TODO: Remove unnecessary logging
            if self.settings.DEBUGGING:
                self._log('meda', message2=info, level='debug')
            if info:
                self.src_fps = eval(info['streams'][0]['avg_frame_rate'])
        except ZeroDivisionError:
            self._log('Warning, Cannot use input FPS', level='warning')
        if self.src_fps == 0:
            raise ValueError('Unexpected zero FPS')

        # Get Duration
        try:
            self.duration = float(info['format']['duration'])
        except ZeroDivisionError:
            self._log('Warning, Cannot use input Duration', level='warning')

        if self.src_fps == None and self.duration == None:
            raise ValueError('Unable to match against FPS or Duration.')

        return info

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
        except Exception as e:
            self._log("Exception - process_file: {}".format(e), level='exception')
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
            self._log("Exception - check_file_to_be_processed: {}".format(e), level='exception')
            # Failed to fetch properties
            if self.settings.DEBUGGING:
                self._log("Failed to fetch properties of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
            return False

        # Check if the file container from it's properties matches the configured container
        correct_extension = False
        try:
            current_possible_extensions = file_probe['format']['format_name'].split(",")
            for extension in current_possible_extensions:
                if extension == self.settings.OUT_CONTAINER:
                    if self.settings.DEBUGGING:
                        self._log("File already in container format {} - {}".format(self.settings.OUT_CONTAINER,vid_file_path), level='debug')
                    correct_extension = True
        except Exception as e: 
            self._log("Exception - check_file_to_be_processed: {}".format(e), level='exception')
            # Failed to fetch properties
            if self.settings.DEBUGGING:
                self._log("Failed to read format of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
            return False

        # Check if the file video codec from it's properties matches the configured video codec
        correct_video_codec = False
        try:
            for stream in file_probe['streams']:
                if stream['codec_type'] == 'video':
                    # Check if this file is already the right format
                    if stream['codec_name'] == self.settings.VIDEO_CODEC:
                        if self.settings.DEBUGGING:
                            self._log("File already {} - {}".format(self.settings.VIDEO_CODEC,vid_file_path), level='debug')
                        correct_video_codec = True
        except Exception as e: 
            self._log("Exception - check_file_to_be_processed: {}".format(e), level='exception')
            # Failed to fetch properties
            if self.settings.DEBUGGING:
                self._log("Failed to read codec info of file {}".format(vid_file_path), level='debug')
                self._log("Marking file not to be processed", level='debug')
            return False

        # Finally ensure that all file properties match the configured values.
        if correct_extension and correct_video_codec:
            # This file is already the correct container and codec
            return False
        # File did not match, it will need to be added to the queue for processing
        return True

    def post_process_file(self, vid_file_path):
        try:
            self.file_out = self.file_probe(vid_file_path)
        except Exception as e: 
            self._log("Exception - post_process_file: {}".format(e), level='exception')
            return False
            # Failed to fetch properties
            raise FFMPEGHandlePostProcessError(self.settings.VIDEO_CODEC,stream['codec_name'])

        # Ensure file is correct format
        result = False
        for stream in self.file_out['streams']:
            if stream['codec_type'] == 'video':
                # Check if this file is the right codec
                if stream['codec_name'] == self.settings.VIDEO_CODEC:
                    result = True
                elif self.settings.DEBUGGING:
                    self._log("File is the not correct codec {} - {}".format(self.settings.VIDEO_CODEC,vid_file_path))
                    raise FFMPEGHandlePostProcessError(self.settings.VIDEO_CODEC,stream['codec_name'])
                # TODO: Test duration is the same as src
        return result

    def process_file_with_configured_settings(self, vid_file_path):
        # Parse input path
        src_file = os.path.basename(vid_file_path)
        src_path = os.path.abspath(vid_file_path)
        src_folder = os.path.dirname(src_path)

        # Parse an output cache path
        out_folder = "file_conversion-{}".format(time.time())
        out_file = "{}-{}.{}".format(os.path.splitext(src_file)[0], time.time(), self.settings.OUT_CONTAINER)
        out_path = os.path.join(self.settings.CACHE_PATH, out_folder, out_file)

        # Create output path if not exists 
        common.ensureDir(out_path)

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
        file_properties = self.file_in
        if not file_properties:
            return False

        # Suppress printing banner. (-hide_banner)
        # Set loglevel to info ("-loglevel", "info")
        # Allow experimental encoder config ("-strict", "-2")
        # 
        command = ["-hide_banner", "-loglevel", "info", "-strict", "-2"]

        # Read stream data
        streams_to_map      = []
        streams_to_create   = []
        audio_tracks_count  = 0
        for stream in file_properties['streams']:
            if stream['codec_type'] == 'video':
                # Map this stream
                streams_to_map = streams_to_map + [
                        "-map",   "0:{}".format(stream['index'])
                    ]

                streams_to_create = streams_to_create + [
                        "-c:v", self.settings.CODEC_CONFIG[self.settings.VIDEO_CODEC]['encoder']
                    ]
            if stream['codec_type'] == 'audio':
                # Get details of audio channel:
                if stream['channels'] > 2:
                    # Map this stream
                    streams_to_map = streams_to_map + [
                            "-map",   "0:{}".format(stream['index'])
                        ]

                    streams_to_create = streams_to_create + [
                            "-c:a:{}".format(audio_tracks_count), "copy"
                        ]
                    audio_tracks_count += 1

                    # TODO: Make this optional
                    try:
                        audio_tag = ''.join([i for i in stream['tags']['title'] if not i.isdigit()]).rstrip('.') + 'Stereo'
                    except:
                        audio_tag = 'Stereo'

                    # Map a duplicated stream
                    streams_to_map = streams_to_map + [
                            "-map",   " 0:{}".format(stream['index'])
                        ]

                    streams_to_create = streams_to_create + [
                                "-c:a:{}".format(audio_tracks_count), self.settings.CODEC_CONFIG[self.settings.AUDIO_CODEC]['encoder'] ,
                                "-b:a:{}".format(audio_tracks_count), self.settings.AUDIO_STEREO_STREAM_BITRATE,
                                "-ac", "2",
                                "-metadata:s:a:{}".format(audio_tracks_count), "title='{}'".format(audio_tag),
                            ]
                else:
                    # Force conversion of stereo audio to standard
                    streams_to_map = streams_to_map + [
                            "-map",   " 0:{}".format(stream['index'])
                        ]

                    streams_to_create = streams_to_create + [
                                "-c:a:{}".format(audio_tracks_count), self.settings.CODEC_CONFIG[self.settings.AUDIO_CODEC]['encoder'] ,
                                "-b:a:{}".format(audio_tracks_count), self.settings.AUDIO_STEREO_STREAM_BITRATE,
                                "-ac", "2",
                            ]
            if stream['codec_type'] == 'subtitle':
                if self.settings.REMOVE_SUBTITLE_STREAMS:
                    continue
                # Map this stream
                streams_to_map = streams_to_map + [
                        "-map",   "0:{}".format(stream['index'])
                    ]

                streams_to_create = streams_to_create + [
                        "-c:s:{}".format(audio_tracks_count), "copy"
                    ]
                audio_tracks_count += 1

        # Map streams
        command = command + streams_to_map

        # Add arguments for creating streams
        command = command + streams_to_create

        if self.settings.DEBUGGING:
            self._log(" ".join(command), level='debug')

        return command

    def convert_file_and_fetch_progress(self, infile, outfile, args):
        file_properties = self.file_in
        if not file_properties:
            try:
                file_properties = self.file_probe(infile)
            except Exception as e: 
                self._log("Exception - convert_file_and_fetch_progress: {}".format(e), level='exception')
                return False

        # Create command with infile, outfile and the arguments
        command = ['ffmpeg', '-y', '-i',infile] + args + ['-y',outfile]
        if self.settings.DEBUGGING:
           self._log("Executing: {}".format(' '.join(command)), level='debug')

        # Log the start time
        self.start_time     = time.time()
        self.total_frames   = int(self.duration * self.src_fps)

        # Execute command
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        # Poll process for new output until finished
        while True:
            line_text = self.process.stdout.readline()
            if line_text == '' and self.process.poll() is not None:
                break
            # parse the progress
            try:
                self.parse_conversion_progress(line_text)
            except:
                pass

        # Get the final output and the exit status
        output   = self.process.communicate()[0]
        if (self.process.returncode == 0):
            return True
        else:
            raise FFMPEGHandleConversionError(command)

    def parse_conversion_progress(self, line_text):
        # Use regex to pull progress data from process line text

        # Calculate elapsed time
        self.elapsed = (time.time() - self.start_time)

        # Calculate elapsed time
        if line_text and 'frame=' in line_text:
            # Update time
            _time            = self.get_progress_from_regex_of_string(line_text,r"time=(\s+|)(\d+:\d+:\d+\.\d+)",self.time)
            if _time:
                self.time    = common.timestringToSeconds(_time)

            # Update frames
            _frame           = float(self.get_progress_from_regex_of_string(line_text,r"frame=(\s+|)(\d+)",self.frame))
            if _frame and _frame > self.frame:
                self.frame   = _frame

            # Update speed
            _speed             = self.get_progress_from_regex_of_string(line_text,r"speed=(\s+|)(\d+\.\d+)",self.speed)
            if _speed:
                self.speed     = _speed

            # Update bitrate
            _bitrate           = self.get_progress_from_regex_of_string(line_text,r"bitrate=(\s+|)(\d+\.\d+\w+|\d+w)",self.bitrate)
            if _bitrate:
                self.bitrate   = "{}/s".format(_bitrate)

            # Update file size
            _size              = self.get_progress_from_regex_of_string(line_text,r"size=(\s+|)(\d+\w+|\d+.\d+\w+)",self.frame)
            if _size:
                self.file_size = _size

            # Update percent
            try:
                _percent       = int(int(self.frame) / int(self.total_frames) * 100)
            except:
                _percent       = int(int(self.time) / int(self.duration) * 100)
            if _percent and _percent > self.percent:
                self.percent   = _percent
                
        self._log("TOTAL: frames", self.total_frames, level='debug')
        self._log("TOTAL: duration", self.duration, level='debug')
        self._log("PROGRESS: elapsed time", self.elapsed, level='debug')
        self._log("PROGRESS: seconds converted", self.time, level='debug')
        self._log("PROGRESS: percent converted", self.percent, level='debug')
        self._log("PROGRESS: frames converted", self.frame, level='debug')
        self._log("PROGRESS: speed: {}x".format(self.speed), level='debug')
        self._log("PROGRESS: bitrate", self.bitrate, level='debug')
        self._log("PROGRESS: file size", self.file_size, level='debug')

    def get_progress_from_regex_of_string(self,line,regex_string,default=0):
        return_value = default
        # Update frame
        regex   = re.compile(regex_string)
        #search  = regex.search(line)
        #if search:
        findall = re.findall(regex, line)
        if findall:
            split_list  = findall[-1]
            if len(split_list) == 2:
                return_value = split_list[1].strip()
        return return_value





#      /$$   /$$           /$$   /$$           /$$$$$$$$                    /$$
#     | $$  | $$          |__/  | $$          |__  $$__/                   | $$
#     | $$  | $$ /$$$$$$$  /$$ /$$$$$$           | $$  /$$$$$$   /$$$$$$$ /$$$$$$   /$$$$$$$
#     | $$  | $$| $$__  $$| $$|_  $$_/           | $$ /$$__  $$ /$$_____/|_  $$_/  /$$_____/
#     | $$  | $$| $$  \ $$| $$  | $$             | $$| $$$$$$$$|  $$$$$$   | $$   |  $$$$$$
#     | $$  | $$| $$  | $$| $$  | $$ /$$         | $$| $$_____/ \____  $$  | $$ /$$\____  $$
#     |  $$$$$$/| $$  | $$| $$  |  $$$$/         | $$|  $$$$$$$ /$$$$$$$/  |  $$$$//$$$$$$$/
#      \______/ |__/  |__/|__/   \___/           |__/ \_______/|_______/    \___/ |_______/
#
#
#

class TestClass(object):
    def setup_class(self):
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(self.project_dir)
        import config
        self.settings = config.CONFIG()
        self.settings.DEBUGGING = True
        import unlogger
        self.logging = unlogger.UnmanicLogger.__call__()
        self.logging.setup_logger(self.settings)
        self.logger  = self.logging.get_logger()
        self.ffmpeg  = FFMPEGHandle(self.settings, self.logging)

    def _log(self, message, message2 = '', level = "info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def build_ffmpeg_args(self,test_for_failure=False):
        configured_vencoder = self.settings.CODEC_CONFIG[self.settings.VIDEO_CODEC]['encoder']
        failure_vencoder    = None
        for x in self.settings.CODEC_CONFIG:
            if x != self.settings.VIDEO_CODEC:
                failure_vencoder = self.settings.CODEC_CONFIG[x]['encoder']
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

    def convert_single_file(self,infile,outfile,test_for_failure=False):
        if not os.path.exists(infile):
            self._log("No such file: {}".format(infile))
            sys.exit(1)
        # Ensure the directory exists
        common.ensureDir(outfile)
        # Remove the ouput file if it already exists
        if os.path.exists(outfile):
            os.remove(outfile)
        # Setup ffmpeg args
        built_args = self.build_ffmpeg_args(test_for_failure)
        # Run conversion process
        self._log("Converting {} -> {}".format(infile, outfile))
        assert self.ffmpeg.convert_file_and_fetch_progress(infile, outfile, built_args)
        if not test_for_failure:
            assert self.ffmpeg.post_process_file(outfile)
        elif test_for_failure:
            import pytest
            with pytest.raises(FFMPEGHandlePostProcessError):
                self.ffmpeg.post_process_file(outfile)


    def test_read_file_info_for_success(self):
        self.setup_class()
        # Set project root path
        tests_dir   = os.path.join(self.project_dir, 'tests')
        tmp_dir     = os.path.join(tests_dir, 'tmp')
        # Test
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'small')):
            infile  = os.path.join(tests_dir, 'videos', 'small', video_file)
            assert self.ffmpeg.file_probe(infile)

    def test_read_file_info_for_failure(self):
        self.setup_class()
        # Set project root path
        tests_dir   = os.path.join(self.project_dir, 'tests')
        tmp_dir     = os.path.join(tests_dir, 'tmp')
        fail_file   = os.path.join(tmp_dir, 'test_failure.mkv')
        # Test
        common.touch(fail_file)
        import pytest
        with pytest.raises(FFMPEGHandleFFProbeError):
            self.ffmpeg.file_probe(fail_file)

    def test_convert_all_files_for_success(self):
        self.setup_class()
        # Set project root path
        tests_dir   = os.path.join(self.project_dir, 'tests')
        tmp_dir     = os.path.join(tests_dir, 'tmp')
        # Test
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'small')):
            filename, file_extension = os.path.splitext(os.path.basename(video_file))
            infile  = os.path.join(tests_dir, 'videos', 'small', video_file)
            outfile = os.path.join(tmp_dir, filename + '.mkv')
            self.convert_single_file(infile,outfile)

    def test_process_file_for_success(self):
        self.setup_class()
        # Set project root path
        tests_dir    = os.path.join(self.project_dir, 'tests')
        tmp_dir      = os.path.join(tests_dir, 'tmp')
        # Test
        for video_file in os.listdir(os.path.join(tests_dir, 'videos', 'med')):
            filename, file_extension = os.path.splitext(os.path.basename(video_file))
            infile   = os.path.join(tests_dir, 'videos', 'med', video_file)
            # Copy the file to a tmp location (it will be replaced)
            testfile = os.path.join(tmp_dir, filename + file_extension)
            self._log(infile, testfile)
            shutil.copy(infile, testfile)
            assert self.ffmpeg.process_file(testfile)
            break



if __name__ == "__main__":
    TestClass().test_process_file_for_success()
