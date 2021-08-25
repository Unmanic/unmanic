#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.unlogger.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Jan 2019, (8:41 AM)

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
import logging

from unmanic.libs.singleton import SingletonType


class UnmanicLogger(object, metaclass=SingletonType):
    _enable_log_to_file = None
    stream_handler = None
    file_handler = None
    _settings = None
    _logger = None

    def __init__(self, log_to_file=True):
        self._enable_log_to_file = log_to_file
        # Create our default parent logger and set the default level to info
        self._logger = logging.getLogger("Unmanic")
        # Initially set this logger to INFO (once the config is applied, this may change)
        self._logger.setLevel(logging.INFO)
        # Prevent logging from being passed up the chain
        self._logger.propagate = False

        # Create formatter
        self.formatter = logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        # Add stream handler
        if not self.stream_handler:
            # Create file handler
            self.stream_handler = logging.StreamHandler()
            # Apply formatter
            self.stream_handler.setFormatter(self.formatter)
            # Set the log level of the stream handle
            self.stream_handler.setLevel(logging.INFO)
            # Add handler
            self._logger.addHandler(self.stream_handler)
        # Add file handler
        self.setup_file_handler()

    def setup_file_handler(self):
        if self._enable_log_to_file and not self.file_handler and self._settings and self._settings.get_log_path():
            # Create directory if not exists
            if not os.path.exists(self._settings.get_log_path()):
                os.makedirs(self._settings.get_log_path())
            # Create file handler
            log_file = os.path.join(self._settings.get_log_path(), 'unmanic.log')
            self.file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', interval=1,
                                                                          backupCount=7)
            # Apply formatter
            self.file_handler.setFormatter(self.formatter)
            # Set log level of file handler...
            if self._settings.get_debugging():
                self.file_handler.setLevel(logging.DEBUG)
            else:
                self.file_handler.setLevel(logging.INFO)
            # Set the log level of the stream handle always to error
            self.stream_handler.setLevel(logging.CRITICAL)
            # Add handler
            self._logger.addHandler(self.file_handler)

    def disable_file_handler(self, debugging=False):
        # Set the log level of the stream handle back to INFO or DEBUG
        if debugging:
            self.stream_handler.setLevel(logging.DEBUG)
        else:
            self.stream_handler.setLevel(logging.INFO)
        # Remove handler
        self._logger.removeHandler(self.file_handler)

    def enable_debugging(self):
        logger = self.get_logger(__class__.__name__)
        logger.info('Debug logging enabled')
        self._logger.setLevel(logging.DEBUG)

    def disable_debugging(self):
        logger = self.get_logger(__class__.__name__)
        logger.info('Debug logging disabled')
        self._logger.setLevel(logging.INFO)

    def setup_logger(self, settings):
        logger = self.get_logger(__class__.__name__)
        logger.info("Initialising file logger. All further logs should output to the 'unmanic.log' file")
        # Set/Update our settings
        self._settings = settings
        if not self.file_handler:
            self.setup_file_handler()
        if self._settings.get_debugging():
            self.enable_debugging()
        else:
            self.disable_debugging()

    def get_logger(self, name=None):
        if name:
            logger = logging.getLogger("Unmanic." + name)
        else:
            logger = self._logger
        return logger
