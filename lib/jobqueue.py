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

from lib import ffmpeg, task
from lib import common

import collections
import os

from threading import Lock
from sortedcontainers import SortedList

class IncomingQueue:
    def __init__(self):
        self._lock = Lock()
        self._q = SortedList()

    def add(self, priority, item):
        """
        Parameters
        ----------
        priority : float
            Lower value means higher priority
        item : object
            Object to be put on queue
        """
        elem = (priority, item)
        with self._lock:
            self._q.add(elem)

    def is_empty(self):
        with self._lock:
            return len(self._q) == 0

    def get(self):
        """ Get highest priority item.
        """

        with self._lock:
            priority, item = self._q.pop(0)
            return item

    def contains_abspath(self, abspath):
        with self._lock:
            for item in self._q:
                if abspath == item[1].source['abspath']:
                    return True
        return False



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
        self.settings = settings
        self.data_queues = data_queues
        self.incoming = IncomingQueue()
        self.in_progress = collections.deque()
        self.processed = collections.deque()
        self.ffmpeg = ffmpeg.FFMPEGHandle(settings)
        self.logger = data_queues["logging"].get_logger(self.name)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def incoming_is_empty(self):
        return self.incoming.is_empty()

    def processed_is_empty(self):
        if self.processed:
            return False
        return True

    def mark_item_as_processed(self, task_item):
        self.in_progress.remove(task_item.source['abspath'])
        self.processed.append(task_item)
        return task_item

    def get_next_incoming_item(self):
        task_item = self.incoming.get()
        self.in_progress.append(task_item.source['abspath'])
        return task_item

    def get_next_processed_item(self):
        item = self.processed.popleft()
        return item

    def add_item(self, priority, pathname):
        abspath = os.path.abspath(pathname)
        # Check if this path is already in the job queue
        if self.incoming.contains_abspath(abspath):
            return False
        # Check if this path is already in progress of being converted
        for path in self.list_all_in_progress_paths():
            if path == abspath:
                return False
        # Check if this path is already processed and waiting to be moved
        for item in self.list_all_processed_items():
            if item.source['abspath'] == abspath:
                return False
        # Create a new task and set the source
        new_task = task.Task(self.settings, self.data_queues)
        new_task.set_source_data(pathname)
        new_task.set_destination_data()
        new_task.set_cache_path()
        self.incoming.add(priority, new_task)
        return True

    def list_all_incoming_items(self):
        return list(self.incoming)

    def list_all_processed_items(self):
        return list(self.processed)

    def list_all_in_progress_paths(self):
        return list(self.in_progress)

