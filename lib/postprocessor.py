#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.postprocessor.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Apr 2019, (7:33 PM)
 
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

import queue
import threading
import time

from lib import common

"""

The post-processor handles all tasks carried out on completion of a workers ffmpeg task.
This may be on either success or failure of the task.

The post-processor runs as a single thread, processing completed jobs one at a time.
This prevents conflicting copy operations or deleting a file that is also being post processed.

"""


class PostProcessor(threading.Thread):
    """
    PostProcessor

    """

    def __init__(self, data_queues, settings, job_queue):
        super(PostProcessor, self).__init__(name='PostProcessor')
        self.logger = data_queues["logging"].get_logger(self.name)
        self.settings = settings
        self.job_queue = job_queue
        self.abort_flag = threading.Event()
        self.current_file = None
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def run(self):
        self._log("Starting PostProcessor Monitor loop...")
        while not self.abort_flag.is_set():
            time.sleep(1)

            while not self.abort_flag.is_set() and not self.job_queue.processed_is_empty():
                time.sleep(.2)
                self.current_file = self.job_queue.get_next_processed_item()
                if self.current_file:
                    self._log("Post-processing item - {}".format(self.current_file['abspath']))
                    self.post_process_file()

        self._log("Leaving PostProcessor Monitor loop...")

    def post_process_file(self):
        # TODO: Do stuff with self.current_file
        pass
