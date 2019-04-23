#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Apr 23 2019, (19:17:00 PM)
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

from lib import ffmpeg
from lib import common

import collections
import os


"""

An object to contain all details of the job queue in such a way that it is presented in a synchronous list
while being able to be accessed by a number of threads simultaneously

"""


class JobQueue(object):
    """
    JobQueue

    Creates an job item per file.
    This job item is passed through stages by the Worker and PostProcessor

    Attributes:
        settings (object): The application settings read from config.py
        data_queues (list): A list of Queue objects. Contains the logger

    """

    def __init__(self, settings, data_queues):
        self.name = 'JobQueue'
        self.incoming = collections.deque()
        self.in_progress = collections.deque()
        self.processed = collections.deque()
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings, data_queues['logging'])
        self.logger = data_queues["logging"].get_logger(self.name)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def incoming_is_empty(self):
        if self.incoming:
            return False
        return True

    def processed_is_empty(self):
        if self.processed:
            return False
        return True

    def remove_completed_item(self, file_info):
        self.in_progress.remove(file_info['abspath'])

    def get_next_incoming_item(self):
        item = self.incoming.popleft()
        self.in_progress.append(item['abspath'])
        return item

    def get_next_processed_item(self):
        item = self.processed.popleft()
        return item

    def add_item(self, pathname):
        # Check if this path is already in the job queue
        for item in self.list_all_incoming_items():
            if item['abspath'] == os.path.abspath(pathname):
                return False
        # Check if this path is already in progress of being converted
        for item in self.list_all_in_progress_items():
            if item == os.path.abspath(pathname):
                return False
        # Check if this path is already processed and waiting to be moved
        for item in self.list_all_processed_items():
            if item == os.path.abspath(pathname):
                return False
        # Get info on the file from ffmpeg
        file_info = {
            'abspath': os.path.abspath(pathname),
            'basename': os.path.basename(pathname),
            'video_codecs': ','.join(self.ffmpeg.get_current_video_codecs(self.ffmpeg.file_probe(pathname)))
        }
        self.incoming.append(file_info)
        return True

    def list_all_incoming_items(self):
        return list(self.incoming)

    def list_all_in_progress_items(self):
        return list(self.in_progress)

    def list_all_processed_items(self):
        return list(self.processed)

