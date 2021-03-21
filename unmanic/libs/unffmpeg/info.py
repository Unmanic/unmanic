#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.main.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Sep 2019, (2:08 PM)
 
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

from . import audio_codecs
from . import subtitle_codecs
from . import video_codecs
from .lib import cli


class Info(object):
    """
    Info

    Provide information on FFMPEG commands and configuration
    """
    available_encoders = None
    available_decoders = None

    @staticmethod
    def versions():
        """
        Return the system ffmpeg version as a string

        :return:
        """
        return cli.ffmpeg_version_info()

    def file_probe(self, vid_file_path):
        """
        Probe media file and return result dictionary

        :param vid_file_path:
        :return:
        """
        # TODO: Move this to a new "Probe" class
        return cli.ffprobe_file(vid_file_path)

    def get_available_ffmpeg_encoders(self):
        """
        Sets a dictionary of encoders supported by ffmpeg
        """
        available_audio_encoders = {}
        available_subtitle_encoders = {}
        available_video_encoders = {}

        # Get raw ffmpeg output of available encoders
        info = cli.ffmpeg_available_encoders()

        # Sort through the lines and create a dictionary of audio, subtitle and video encoders
        for line in info.splitlines():
            line = line.rstrip().lstrip()
            if line.startswith('A') and line != 'A..... = Audio':
                # Audio encoder
                data = line.split()
                capabilities = data.pop(0)
                codec = data.pop(0)
                available_audio_encoders[codec] = {
                    'capabilities': capabilities,
                    'description':  " ".join(data)
                }
            elif line.startswith('S') and line != 'S..... = Subtitle':
                # Subtitle encoder
                data = line.split()
                capabilities = data.pop(0)
                codec = data.pop(0)
                available_subtitle_encoders[codec] = {
                    'capabilities': capabilities,
                    'description':  " ".join(data)
                }
            elif line.startswith('V') and line != 'V..... = Video':
                # Video encoder
                data = line.split()
                capabilities = data.pop(0)
                codec = data.pop(0)
                available_video_encoders[codec] = {
                    'capabilities': capabilities,
                    'description':  " ".join(data)
                }

        # Combine dictionaries into one
        self.available_encoders = {
            'audio':    available_audio_encoders,
            'subtitle': available_subtitle_encoders,
            'video':    available_video_encoders
        }

        return self.available_encoders

    def get_available_ffmpeg_decoders(self):
        """
        Sets a dictionary of decoders supported by ffmpeg
        """
        available_audio_decoders = {}
        available_subtitle_decoders = {}
        available_video_decoders = {}

        # Get raw ffmpeg output of available decoders
        info = cli.ffmpeg_available_decoders()

        # Sort through the lines and create a dictionary of audio, subtitle and video decoders
        for line in info.splitlines():
            line = line.rstrip().lstrip()
            if line.startswith('A') and line != 'A..... = Audio':
                # Audio decoder
                data = line.split()
                capabilities = data.pop(0)
                codec = data.pop(0)
                available_audio_decoders[codec] = {
                    'capabilities': capabilities,
                    'description':  " ".join(data)
                }
            elif line.startswith('S') and line != 'S..... = Subtitle':
                # Subtitle decoder
                data = line.split()
                capabilities = data.pop(0)
                codec = data.pop(0)
                available_subtitle_decoders[codec] = {
                    'capabilities': capabilities,
                    'description':  " ".join(data)
                }
            elif line.startswith('V') and line != 'V..... = Video':
                # Video decoder
                data = line.split()
                capabilities = data.pop(0)
                codec = data.pop(0)
                available_video_decoders[codec] = {
                    'capabilities': capabilities,
                    'description':  " ".join(data)
                }

        # Combine dictionaries into one
        self.available_decoders = {
            'audio':    available_audio_decoders,
            'subtitle': available_subtitle_decoders,
            'video':    available_video_decoders
        }

        return self.available_decoders

    def get_available_ffmpeg_hw_acceleration_methods(self):
        methods = []

        # Get raw ffmpeg output of available encoders
        info = cli.ffmpeg_available_hw_acceleration_methods()

        # Sort through the lines and create a list of methods
        for line in info.splitlines():
            line = line.rstrip().lstrip()
            if not line or line.startswith('Hardware acceleration'):
                continue
            else:
                methods.append(line)

        return methods

    def get_ffmpeg_audio_encoders(self):
        """
        Fetch all audio encoders supported by ffmpeg

        :return:
        """
        if self.available_encoders is None:
            self.get_available_ffmpeg_encoders()
        return self.available_encoders['audio']

    def get_ffmpeg_subtitle_encoders(self):
        """
        Fetch all subtitle encoders supported by ffmpeg

        :return:
        """
        if self.available_encoders is None:
            self.get_available_ffmpeg_encoders()
        return self.available_encoders['subtitle']

    def get_ffmpeg_video_encoders(self):
        """
        Fetch all video encoders supported by ffmpeg

        :return:
        """
        if self.available_encoders is None:
            self.get_available_ffmpeg_encoders()
        return self.available_encoders['video']

    def filter_available_encoders_for_codec(self, codec_encoders, codec_type):
        """
        Filter a given list of encoders. Removes any that are not available with FFMPEG

        :param codec_type:
        :param codec_encoders:
        :return:
        """
        available_encoders = {}
        if codec_type == 'audio':
            available_encoders = self.get_ffmpeg_audio_encoders()
        elif codec_type == 'subtitle':
            available_encoders = self.get_ffmpeg_subtitle_encoders()
        elif codec_type == 'video':
            available_encoders = self.get_ffmpeg_video_encoders()
        # Iterate through the list of encoders.
        for encoder in codec_encoders:
            # Check if ffmpeg has that encoder
            if encoder not in available_encoders:
                # Encoder is not available, remove it from the list
                codec_encoders.remove(encoder)
        return codec_encoders

    def get_all_supported_codecs_of_type(self, codec_type):
        """
        Fetch a list of supported codecs and
        return a dictionary of their data

        :return:
        """
        codec_dict = {}
        return_codec_dict = {}
        if codec_type == 'audio':
            codec_dict = audio_codecs.get_all_audio_codecs()
        elif codec_type == 'subtitle':
            codec_dict = audio_codecs.get_all_audio_codecs()
        elif codec_type == 'video':
            codec_dict = video_codecs.get_all_video_codecs()
        # Iterate through the list of codecs.
        for codec_name in codec_dict:
            codec = codec_dict[codec_name]
            # Get list of encoders for this codec that are available in ffmpeg
            codec_encoders = self.filter_available_encoders_for_codec(codec['encoders'], codec_type)
            # Check if any encoders were found
            if not codec_encoders:
                continue
            # At least one encoder is found for that codec.
            # Add codec to codec_list if one encoder exists
            return_codec_dict[codec_name] = codec
        return return_codec_dict

    def get_all_supported_video_codecs(self):
        """
        Fetch a list of supported video codecs and
        return a dictionary of their data

        :return:
        """
        return_codec_dict = {}
        codec_dict = video_codecs.get_all_video_codecs()
        for codec_name in codec_dict:
            codec = codec_dict[codec_name]
            # Get list of encoders for this codec that are available in ffmpeg
            codec_encoders = self.filter_available_encoders_for_codec(codec['encoders'], 'video')
            # Check if any encoders were found
            if not codec_encoders:
                continue
            # At least one encoder is found for that codec.
            # Add codec to codec_list if one encoder exists
            return_codec_dict[codec_name] = codec
        return return_codec_dict

    def get_all_supported_codecs(self):
        supported_audio_codecs = self.get_all_supported_codecs_of_type('audio')
        # TODO: Subtitles
        supported_video_codecs = self.get_all_supported_codecs_of_type('video')

        # Combine dictionaries into one and return
        return {
            'audio':    supported_audio_codecs,
            'subtitle': {},
            'video':    supported_video_codecs
        }
