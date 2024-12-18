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
import threading


class UnmanicLogging:
    _instance = None
    _lock = threading.Lock()
    _configured = False
    stream_handler = None  # Class-level stream handler
    file_handler = None  # Class-level file handler

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UnmanicLogging, cls).__new__(cls)
                cls._instance._logger = logging.getLogger("Unmanic")
                cls._instance._logger.setLevel(logging.INFO)
                cls._instance._logger.propagate = False
            return cls._instance

    @staticmethod
    def get_logger(name=None, settings=None):
        """
        Get a child logger. Configure the root logger if 'settings' are provided.
        """
        logger_instance = UnmanicLogging()
        if settings and not logger_instance._configured:
            logger_instance.configure(settings)

        if name:
            return logging.getLogger(f"Unmanic.{name}")
        return logger_instance._logger

    def configure(self, settings):
        """
        Configure the logger using the provided Config settings instance.

        :param settings: Instance of Config class with application settings.
        """
        with self._lock:
            if self._configured:
                return  # Prevent reconfiguration
            # Get logger for this class
            init_logger = logging.getLogger(f"Unmanic.UnmanicLogging")

            # Default formatter
            formatter = logging.Formatter(
                '%(asctime)s:%(levelname)s:%(name)s - %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )

            # Set up stream handler
            if self.stream_handler is None:
                self.stream_handler = logging.StreamHandler()
                self.stream_handler.setFormatter(formatter)
                # Set the log level of the stream handle for this log line only
                self.stream_handler.setLevel(logging.INFO)
                self._logger.addHandler(self.stream_handler)
                # Add an info log to let users know where to look for their logs
                init_logger.info("Initialising file logger. All further logs should output to the 'unmanic.log' file")
                # Set the log level of the stream handle always to error
                self.stream_handler.setLevel(logging.CRITICAL)

            # Set up file handler if log path exists
            log_path = settings.get_log_path()
            if log_path:
                if not os.path.exists(log_path):
                    os.makedirs(log_path)

                self.file_handler = logging.FileHandler(os.path.join(log_path, "unmanic.log"))
                self.file_handler.setFormatter(formatter)
                # Set file handler log level based on debugging setting
                self.file_handler.setLevel(logging.DEBUG if settings.get_debugging() else logging.INFO)
                self._logger.addHandler(self.file_handler)

            # Set root logger level
            self._logger.setLevel(logging.DEBUG if settings.get_debugging() else logging.INFO)
            self._configured = True

    @staticmethod
    def enable_debugging():
        """
        Enable debugging globally across all threads.
        """
        instance = UnmanicLogging()
        instance._logger.setLevel(logging.DEBUG)
        instance._logger.info("Log level set to DEBUG")

    @staticmethod
    def disable_debugging():
        """
        Disable debugging globally across all threads.
        """
        instance = UnmanicLogging()
        instance._logger.setLevel(logging.INFO)
        instance._logger.info("Log level set to INFO")

    @staticmethod
    def disable_file_handler(debugging=False):
        """
        Disable logging to file and only log to stdout.

        :param debugging: If True, sets stream handler to DEBUG level; otherwise INFO level.
        """
        instance = UnmanicLogging()

        # Remove file handler if it exists
        if instance.file_handler:
            instance._logger.removeHandler(instance.file_handler)
            instance.file_handler = None
            instance._logger.info("File logging disabled. Logging only to stdout.")

        # Adjust stream handler level
        if instance.stream_handler:
            instance.stream_handler.setLevel(logging.DEBUG if debugging else logging.INFO)
            instance._logger.info(f"Stream logging set to {'DEBUG' if debugging else 'INFO'}")

    @staticmethod
    def update_stream_formatter(formatter):
        """
        Update the formatter of the stream handler.

        :param formatter: A logging.Formatter instance.
        """
        instance = UnmanicLogging()
        if instance.stream_handler:
            instance.stream_handler.setFormatter(formatter)
            instance._logger.info("Stream handler formatter updated.")
        else:
            instance._logger.warning("No stream handler found to update formatter.")
