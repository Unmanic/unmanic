#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Dec 06 2018, (7:21:18 AM)
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

import os
import ago
import time
import datetime
import logging
logging.basicConfig(level=logging.DEBUG)

def _logger(message, message2 = '', level="info"):
    message  = str(message)
    if message2:
        # Message2 can support other objects:
        if isinstance(message2, str):
            message = "%s - %s" % (message,str(message2))
        elif isinstance(message2, dict) or isinstance(message2, list):
            import pprint
            message2 = pprint.pformat(message2, indent=1)
            message = "%s \n%s" % (message,str(message2))
        else:
            message = "%s - %s" % (message,str(message2))
    message = "LibraryOptimiser - %s" % message
    if level == "debug":
        logging.debug(message);
    elif level == "info":
        logging.info(message);
    elif level == "warning":
        logging.warning(message);
    elif level == "exception":
        logging.exception(message);
    # TODO: Also output all logs to logfile. Then have a function read this to display on the web UI


def makeTimestampHumanReadable(ts):
    return ago.human(ts, precision=1)


def ensureDir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def timestringToSeconds(timestring):
    pt =datetime.datetime.strptime(timestring,'%H:%M:%S.%f')
    return pt.second+pt.minute*60+pt.hour*3600


