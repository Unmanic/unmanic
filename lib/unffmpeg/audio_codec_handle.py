#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.audio_codec_handle.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Sep 2019, (7:53 AM)
 
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


class AudioCodecHandle(object):
    """
    AudioCodecHandle

    Handle FFMPEG operations pertaining to audio codec streams
    """

    def __init__(self, file_probe):
        self.file_probe = file_probe
        self.encoding_args = {}

        # Configurable settings
        self.disable_audio_encoding = False
        self.audio_encoder = 'aac'  # Default to aac
        self.audio_stereo_stream_bitrate = '128k'  # Default to 128k

    def args(self):
        """
        Return a dictionary of streams to map and streams to encode
        :return:
        """
        # Read stream data
        self.encoding_args['streams_to_map'] = []
        self.encoding_args['streams_to_encode'] = []
        audio_tracks_count = 0
        for stream in self.file_probe['streams']:
            # If this is a video stream, then process the args
            if stream['codec_type'] == 'audio':

                if self.disable_audio_encoding:
                    # Audio re-encoding is disabled. Just copy the stream
                    self.encoding_args['streams_to_encode'] = self.encoding_args['streams_to_encode'] + [
                        "-c:a:{}".format(audio_tracks_count), "copy"
                    ]
                    # Map this stream
                    self.encoding_args['streams_to_map'] = self.encoding_args['streams_to_map'] + [
                        "-map", "0:{}".format(stream['index'])
                    ]
                    audio_tracks_count += 1
                else:
                    # Get details of audio channel:
                    if stream['channels'] > 2:
                        # Map this stream
                        self.encoding_args['streams_to_map'] = self.encoding_args['streams_to_map'] + [
                                "-map",   "0:{}".format(stream['index'])
                            ]

                        self.encoding_args['streams_to_encode'] = self.encoding_args['streams_to_encode'] + [
                                "-c:a:{}".format(audio_tracks_count), "copy"
                            ]
                        audio_tracks_count += 1

                        # TODO: Make this optional
                        try:
                            audio_tag = ''.join([i for i in stream['tags']['title'] if not i.isdigit()]).rstrip(
                                '.') + 'Stereo'
                        except:
                            audio_tag = 'Stereo'

                        # Map a duplicated stream
                        self.encoding_args['streams_to_map'] = self.encoding_args['streams_to_map'] + [
                                "-map",   " 0:{}".format(stream['index'])
                            ]

                        self.encoding_args['streams_to_encode'] = self.encoding_args['streams_to_encode'] + [
                                    "-c:a:{}".format(audio_tracks_count), self.audio_encoder,
                                    "-b:a:{}".format(audio_tracks_count), self.audio_stereo_stream_bitrate,
                                    "-ac", "2",
                                    "-metadata:s:a:{}".format(audio_tracks_count), "title='{}'".format(audio_tag),
                                ]
                        audio_tracks_count += 1
                    else:
                        # Force conversion of stereo audio to standard
                        self.encoding_args['streams_to_map'] = self.encoding_args['streams_to_map'] + [
                                "-map",   " 0:{}".format(stream['index'])
                            ]

                        self.encoding_args['streams_to_encode'] = self.encoding_args['streams_to_encode'] + [
                                    "-c:a:{}".format(audio_tracks_count), self.audio_encoder,
                                    "-b:a:{}".format(audio_tracks_count), self.audio_stereo_stream_bitrate,
                                    "-ac", "2",
                                ]
                        audio_tracks_count += 1

        return self.encoding_args

    def set_audio_codec(self, codec_name):
        """
        Set the audio encoder

        :return:
        """
        codec = audio_codecs.grab_module(codec_name)
        self.audio_encoder = codec.audio_encoder()
