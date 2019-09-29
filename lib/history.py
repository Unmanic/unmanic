#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Jun 2019, (10:42 AM)
 
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
import logging
import os

import json

from lib import common, unlogger

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class History(object):
    """
    History

    Record statistical data for historical jobs
    """

    def __init__(self, settings=None):
        self.name = 'History'
        self.settings = settings

    def _log(self, message, message2='', level="info"):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(self.name)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.name))

    def read_history_log(self):
        self._log("Reading history from file:", level="debug")
        data = []
        if not os.path.exists(self.settings.CONFIG_PATH):
            os.makedirs(self.settings.CONFIG_PATH)
        history_file = os.path.join(self.settings.CONFIG_PATH, 'history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                self._log("ValueError in reading history from file:", level="exception")
            except Exception as e:
                self._log("Exception in reading history from file:", message2=str(e), level="exception")
        data.reverse()
        return data

    def read_completed_job_data(self, job_id):
        self._log("Reading completed job data from file:", level="debug")
        data = []
        # Create completed job details path in not exists
        completed_job_details_dir = os.path.join(self.settings.CONFIG_PATH, 'completed_job_details')
        if not os.path.exists(completed_job_details_dir):
            os.makedirs(completed_job_details_dir)
        # Set path of conversion details file
        job_details_file = os.path.join(completed_job_details_dir, '{}.json'.format(job_id))
        if os.path.exists(job_details_file):
            try:
                with open(job_details_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                self._log("ValueError in reading completed job data from file:", level="exception")
            except Exception as e:
                self._log("Exception in reading completed job data from file:", message2=str(e), level="exception")
        return data

