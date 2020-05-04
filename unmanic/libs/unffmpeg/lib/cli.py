#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.cli.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Sep 2019, (2:31 PM)
 
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
import json
import subprocess

from ..exceptions.ffmpeg import FFMpegError
from ..exceptions.ffprobe import FFProbeError


def ffprobe_file(vid_file_path):
    """
    Give a json from ffprobe command line

    :param vid_file_path: The absolute (full) path of the video file, string.
    :return:
    """
    if type(vid_file_path) != str:
        raise Exception('Give ffprobe a full file path of the video')

    command = ["ffprobe",
               "-loglevel", "quiet",
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
        raise FFProbeError(vid_file_path, str(e))
    if pipe.returncode == 1 or 'error' in info:
        raise FFProbeError(vid_file_path, info)
    if not info:
        raise FFProbeError(vid_file_path, 'No info found')

    return info


def ffmpeg_available_encoders():
    """
    Return the raw output of codecs supported by ffmpeg
      Encoders:
        V..... = Video
        A..... = Audio
        S..... = Subtitle
        .F.... = Frame-level multithreading
        ..S... = Slice-level multithreading
        ...X.. = Codec is experimental
        ....B. = Supports draw_horiz_band
        .....D = Supports direct rendering method 1

    :return:
    """
    command = ["ffmpeg",
               "-loglevel", "quiet",
               "-encoders"
               ]

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()

    # Check for results
    try:
        raw_output = out.decode("utf-8")
    except Exception as e:
        raise FFMpegError(command, str(e))
    if pipe.returncode == 1 or 'error' in raw_output:
        raise FFMpegError(command, raw_output)
    if not raw_output:
        raise FFMpegError(command, 'No command output returned')

    return raw_output
