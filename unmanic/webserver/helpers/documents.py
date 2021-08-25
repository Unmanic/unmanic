#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.documents.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Aug 2021, (2:59 PM)

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
import zipfile

from unmanic import config


def generate_log_files_zip():
    settings = config.Config()

    cache_path = settings.get_cache_path()
    logs_path = settings.get_log_path()

    # Ensure the cache path exists
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    # Ensure the logs path exists
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

    # Create zip of all log files
    out_file = os.path.join(cache_path, 'UnmanicLogs.zip')
    with zipfile.ZipFile(out_file, 'w') as zip_object:
        # Iterate over all the files in directory
        for dir_name, subdirectories, filenames in os.walk(logs_path):
            for filename in filenames:
                # create complete filepath of file in directory
                logfile_path = os.path.join(dir_name, filename)
                # Add file to zip
                zip_object.write(logfile_path, os.path.basename(logfile_path))

    return out_file
