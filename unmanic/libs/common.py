#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.common.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2018, (7:21 AM)
 
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
  
           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""

import datetime
import os
import random
import string
import shutil


def get_home_dir():
    home_dir = os.environ.get('HOME_DIR')
    if home_dir is None:
        home_dir = os.path.expanduser("~")
    return home_dir


def get_config_dir():
    config_dir = os.environ.get('CONFIG_PATH')
    if config_dir is None:
        config_dir = os.path.join(get_home_dir(), '.unmanic', 'config')
    return config_dir


def get_ui_port():
    ui_port = os.environ.get('UI_PORT')
    if ui_port is None:
        ui_port = 8888
    return ui_port


def format_message(message, message2=''):
    message = str(message)
    if message2:
        # Message2 can support other objects:
        if isinstance(message2, str):
            message = "%s - %s" % (message, str(message2))
        elif isinstance(message2, dict) or isinstance(message2, list):
            import pprint
            message2 = pprint.pformat(message2, indent=1)
            message = "%s \n%s" % (message, str(message2))
        else:
            message = "%s - %s" % (message, str(message2))
    message = "[FORMATTED] - %s" % message
    return message


def make_timestamp_human_readable(ts):
    """
    Accept a unix timestamp, return a human readable timedelta string.

    :param ts: a datetime, timedelta, or timestamp (integer / float) object
    :returns: Human readable timedelta string (Str)
    """
    units = ("year", "day", "hour", "minute", "second", "millisecond", "microsecond")
    precision = 1
    past_tense = "{} ago"
    future_tense = "in {}"

    # Get datetime from ts string
    dt = datetime.datetime.fromtimestamp(ts)
    delta = datetime.datetime.now(tz=dt.tzinfo) - dt

    # Determine if this is past or future tense
    the_tense = future_tense if delta < datetime.timedelta(0) else past_tense

    # Create a dictionary of units
    delta = abs(delta)
    d = {
        "year":        int(delta.days / 365),
        "day":         int(delta.days % 365),
        "hour":        int(delta.seconds / 3600),
        "minute":      int(delta.seconds / 60) % 60,
        "second":      delta.seconds % 60,
        "millisecond": delta.microseconds / 1000,
        "microsecond": delta.microseconds % 1000,
    }

    human_readable_list = []
    count = 0

    # Start building up the output in the human readable list.
    for unit in units:
        if count >= precision:
            break  # met precision
        if d[unit] == 0:
            continue  # skip 0's
        else:
            s = "" if d[unit] == 1 else "s"  # handle plurals
            human_readable_list.append("{} {}{}".format(d[unit], unit, s))
        count += 1

    return the_tense.format(", ".join(human_readable_list))


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def time_string_to_seconds(time_string):
    pt = datetime.datetime.strptime(time_string, '%H:%M:%S.%f')
    return pt.second + pt.minute * 60 + pt.hour * 3600


def tail(f, n, offset=0):
    """Reads a n lines from f with an offset of offset lines."""
    avg_line_length = 153
    to_read = n + offset
    while 1:
        try:
            f.seek(-(avg_line_length * to_read), 2)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
        except IOError:
            f.seek(0)
        pos = f.tell()
        lines = f.read().splitlines()
        if len(lines) >= to_read or pos == 0:
            return lines
        avg_line_length *= 1.3


def touch(fname, mode=0o666, dir_fd=None, **kwargs):
    """Touch a file. If it does not exist, create it."""
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(fname, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(f.fileno() if os.utime in os.supports_fd else fname,
                 dir_fd=None if os.supports_fd else dir_fd, **kwargs)


def clean_files_in_dir(directory):
    """This will completely wipe all contents from a directory"""
    if os.path.exists(directory):
        for root, subFolders, files in os.walk(directory):
            if os.path.basename(root).startswith("unmanic_file_conversion"):
                print("Clearing cache path - {}".format(root))
                try:
                    shutil.rmtree(root)
                except Exception as e:
                    print("Exception while clearing cache path - {}".format(str(e)))


def random_string(string_length=5):
    """Generate a random string of fixed length"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


def json_dump_to_file(json_data, out_file, check=True, rollback_on_fail=True):
    """Dump json data to a file. Optionally checks that the output json data is valid"""
    import json
    import time
    import tempfile
    import shutil

    result = {
        'errors':  [],
        'success': False
    }

    # If check param is flagged and there already exists a out file, create a temporary backup
    if check and os.path.exists(out_file):
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'json_dump_to_file_backup-{}'.format(time.time()))
        try:
            shutil.copy2(out_file, temp_path)
            result['temp_path'] = temp_path
        except Exception as e:
            result['success'] = False
            result['errors'].append("Failed to create temporary file - {}".format(str(e)))

    # Write data to out_file
    try:
        with open(out_file, 'w') as outfile:
            json.dump(json_data, outfile, sort_keys=True, indent=4)
        result['success'] = True
    except Exception as e:
        result['success'] = False
        result['errors'].append("Exception in writing history to file: {}".format(str(e)))

    # If check param is flagged, ensure json data exists in the output file
    if check:
        try:
            with open(out_file) as infile:
                data = json.load(infile)
            result['success'] = True
        except Exception as e:
            result['success'] = False
            result['errors'].append("JSON file invalid")

        # If data save was unsuccessful and the rollback_on_fail param is flagged
        # and there is a temp file set, roll back to old file
        if not result['success'] and result['temp_path'] and rollback_on_fail:
            os.remove(out_file)
            shutil.copy2(result['temp_path'], out_file)
    return result


def extract_video_codecs_from_file_properties(file_properties: dict):
    """
    Read a dictionary of file properties
    Extract a list of video codecs from the video streams

    :param file_properties:
    :return:
    """
    codecs = []
    for stream in file_properties['streams']:
        if stream['codec_type'] == 'video':
            codecs.append(stream['codec_name'])
    return codecs


def fetch_file_data_by_path(pathname):
    """
    Returns a dictionary of file data for a given path.

    Will throw an exception if pathname is not a valid file

    :param pathname:
    :return:
    """
    # Set source dict
    file_data = {
        'abspath':  os.path.abspath(pathname),
        'basename': os.path.basename(pathname),
        'dirname':  os.path.dirname(os.path.abspath(pathname))
    }

    # Probe file
    from unmanic.libs.unffmpeg import Info
    probe_info = Info().file_probe(file_data['abspath'])

    # Extract only the video codec list
    video_codecs_list = extract_video_codecs_from_file_properties(probe_info)

    # Make comma separated string from the list of video codecs used in this file
    file_data['video_codecs'] = ','.join(video_codecs_list)

    # Merge file probe with file_data
    file_data.update(probe_info)

    # return the file data
    return file_data
