#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.subtitle_handle.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     19 Sep 2019, (5:23 PM)
 
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


class SubtitleHandle(object):
    """
    SubtitleHandle

    Handle FFMPEG operations pertaining to subtitle streams
    """

    def __init__(self, file_probe, container):
        self.file_probe = file_probe
        self.container = container
        self.subtitle_args = {}

        # Configurable settings
        self.remove_subtitle_streams = False

        # Check if destination container supports subtitles
        if not container.container_supports_subtitles():
            # Destination container does not support subtitles,
            # Force them to be removed
            self.remove_subtitle_streams = True

    def args(self):
        """
        Return a dictionary of streams to map and streams to encode
        :return:
        """
        # Read stream data
        self.subtitle_args['streams_to_map'] = []
        self.subtitle_args['streams_to_encode'] = []
        subtitle_tracks_count = 0
        for stream in self.file_probe['streams']:
            # If this is a subtitle stream, then process the args
            if stream['codec_type'] == 'subtitle':
                # Remove subtitles means add no args
                if self.remove_subtitle_streams:
                    continue

                # Add stream
                # Check container for support of current stream (If copy is possible)
                # TODO: Add support for user selection of subtitle format
                supported_subtitles = self.container.supported_subtitles()
                # TODO: Select best/or configured subtitle codec, then fetch that codec class.
                #       Use the subtitle class rather than this array
                if stream['codec_name'] in supported_subtitles:
                    # If dest container supports the current subtitle codec, just copy it
                    self.subtitle_args['streams_to_encode'] = self.subtitle_args['streams_to_encode'] + [
                        "-c:s:{}".format(subtitle_tracks_count), "copy"
                    ]
                    subtitle_tracks_count += 1
                else:
                    # The dest container does not support the current subtitle stream.
                    # Transcode the stream to a format that the destination container does support
                    # TODO: Check if it can be re-encoded. It is not possible to switch between image and text format
                    # If dest container supports the current subtitle codec, just copy it
                    # unsupported subtitles will need to be removed, otherwise ffmpeg will not convert
                    unsupported_subtitles = self.container.unsupported_subtitles()
                    if stream['codec_name'] in unsupported_subtitles:
                        continue
                    else:
                        self.subtitle_args['streams_to_encode'] = self.subtitle_args['streams_to_encode'] + [
                            "-c:s:{}".format(subtitle_tracks_count), "{}".format(supported_subtitles[0])
                        ]
                        subtitle_tracks_count += 1

                # Map this stream if it was marked above as compatible with the destination
                self.subtitle_args['streams_to_map'] = self.subtitle_args['streams_to_map'] + [
                    "-map", "0:{}".format(stream['index'])
                ]

        return self.subtitle_args

    def remove_subtitles(self):
        """
        Remove the subtitles stream from result file

        :return:
        """
        self.remove_subtitle_streams = True
