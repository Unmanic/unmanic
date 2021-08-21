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


def ffmpeg_cmd(params):
    """
    Execute a ffmpeg command subprocess and read the output

    :param params:
    :return:
    """
    command = ["ffmpeg"] + params

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


def ffprobe_cmd(params):
    """
    Execute a ffprobe command subprocess and read the output

    :param params:
    :return:
    """
    command = ["ffprobe"] + params

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()

    # Check for results
    try:
        raw_output = out.decode("utf-8")
    except Exception as e:
        raise FFProbeError(command, str(e))
    if pipe.returncode == 1 or 'error' in raw_output:
        raise FFProbeError(command, raw_output)
    if not raw_output:
        raise FFProbeError(command, 'No info found')

    return raw_output


def ffprobe_file(vid_file_path):
    """
    Returns a dictionary result from ffprobe command line prove of a file

    :param vid_file_path: The absolute (full) path of the video file, string.
    :return:
    """
    if type(vid_file_path) != str:
        raise Exception('Give ffprobe a full file path of the video')

    params = [
        "-loglevel", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_error",
        vid_file_path
    ]

    # Check result
    results = ffprobe_cmd(params)
    try:
        info = json.loads(results)
    except Exception as e:
        raise FFProbeError(vid_file_path, str(e))

    return info


def ffmpeg_version_info():
    """
    Returns a dictionary result of the current FFMPEG versions

    :return:
    """
    params = [
        "-loglevel", "quiet",
        "-print_format", "json",
        "-show_versions",
    ]

    results = ffprobe_cmd(params)
    try:
        info = json.loads(results)
    except Exception as e:
        raise FFProbeError("ffmpeg_version_info function", str(e))

    return info


def ffmpeg_available_encoders():
    """
    Return the raw output of encoders supported by ffmpeg
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
    params = [
        "-loglevel",
        "quiet",
        "-encoders",
    ]

    return ffmpeg_cmd(params)


def ffmpeg_available_decoders():
    """
    Return the raw output of decoders supported by ffmpeg
      Decoders:
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
    params = [
        "-loglevel",
        "quiet",
        "-decoders",
    ]

    return ffmpeg_cmd(params)


def ffmpeg_available_hw_acceleration_methods():
    """
    Return the raw output of hardware accelration methods supported by ffmpeg
      Hardware acceleration methods:
      vdpau
      cuda
      vaapi


    :return:
    """
    params = [
        "-loglevel",
        "quiet",
        "-hwaccels",
    ]

    return ffmpeg_cmd(params)
