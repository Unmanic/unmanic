#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jan 06 2019, (8:41:24 AM)
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
import logging


class SingletonType(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonType, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# python 3 style
class UnmanicLogger(object, metaclass=SingletonType):
    _enable_log_to_file = None
    _stream_handler = None
    _file_handler = None
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
        if not self._stream_handler:
            # Create file handler
            self._stream_handler = logging.StreamHandler()
            # Apply formatter
            self._stream_handler.setFormatter(self.formatter)
            # Set the log level of the stream handle
            self._stream_handler.setLevel(logging.INFO)
            # Add handler
            self._logger.addHandler(self._stream_handler)
        # Add file handler
        self.setup_file_handler()
        print("UnmanicLogger - GENERATING NEW INSTANCE")
        # ###########
        # log_to_debug = self._logger
        # while log_to_debug is not None:
        #     print ("########## level: %s, name: %s, handlers: %s" % (log_to_debug.level,
        #                                                 log_to_debug.name,
        #                                                 log_to_debug.handlers))
        #     log_to_debug = log_to_debug.parent
        # ##########

    def setup_file_handler(self):
        if self._enable_log_to_file and not self._file_handler and self._settings and self._settings.LOG_PATH:
            # Create directory if not exists
            if not os.path.exists(self._settings.LOG_PATH):
                os.makedirs(self._settings.LOG_PATH)
            # Create file handler
            log_file = os.path.join(self._settings.LOG_PATH, 'unmanic.log')
            self._file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=7)
            # Apply formatter
            self._file_handler.setFormatter(self.formatter)
            # Set log level of file handler...
            if self._settings.DEBUGGING:
                self._file_handler.setLevel(logging.DEBUG)
            else:
                self._file_handler.setLevel(logging.INFO)
            # Set the log level of the stream handle always to error
            self._stream_handler.setLevel(logging.ERROR)
            # Add handler
            self._logger.addHandler(self._file_handler)
    
    def setup_logger(self, settings):
        # Set/Update our settings
        self._settings = settings
        if not self._file_handler:
            self.setup_file_handler()
        if self._settings.DEBUGGING:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)
        print("UnmanicLogger - SETUP LOGGER")
        # ###########
        # log_to_debug = self._logger
        # while log_to_debug is not None:
        #     print ("########## level: %s, name: %s, handlers: %s" % (log_to_debug.level,
        #                                                 log_to_debug.name,
        #                                                 log_to_debug.handlers))
        #     log_to_debug = log_to_debug.parent
        # ##########

    def get_logger(self, name=None):
        if name:
            logger = logging.getLogger("Unmanic."+name)
        else:
            logger = self._logger
        return logger





#      /$$   /$$           /$$   /$$           /$$$$$$$$                    /$$
#     | $$  | $$          |__/  | $$          |__  $$__/                   | $$
#     | $$  | $$ /$$$$$$$  /$$ /$$$$$$           | $$  /$$$$$$   /$$$$$$$ /$$$$$$   /$$$$$$$
#     | $$  | $$| $$__  $$| $$|_  $$_/           | $$ /$$__  $$ /$$_____/|_  $$_/  /$$_____/
#     | $$  | $$| $$  \ $$| $$  | $$             | $$| $$$$$$$$|  $$$$$$   | $$   |  $$$$$$
#     | $$  | $$| $$  | $$| $$  | $$ /$$         | $$| $$_____/ \____  $$  | $$ /$$\____  $$
#     |  $$$$$$/| $$  | $$| $$  |  $$$$/         | $$|  $$$$$$$ /$$$$$$$/  |  $$$$//$$$$$$$/
#      \______/ |__/  |__/|__/   \___/           |__/ \_______/|_______/    \___/ |_______/
#
#
#

class SettingsObject(object):
    pass

def test_logging_singleton():
    logger1 = UnmanicLogger.__call__().get_logger()
    logger2 = UnmanicLogger.__call__().get_logger()

    # Ensure singleton works:
    if logger1 == logger2:
        print("### Instances of UnmanicLogger are the same object")

    # Create a child logger
    logger_blah = UnmanicLogger.__call__().get_logger("blah")

    # Test one (everything works on console, no loogging to files)
    print("### Info logging - everything works on console, no loogging to files")
    logger1.info("Default - test1 - info")
    logger1.debug("Default - test1 - debug")
    logger1.warning("Default - test1 - warning")
    logger1.critical("Default - test1 - critical")
    logger1.exception("Default - test1 - exception: %s", "Test Exception String")

    logger_blah.info("BLAH - test1 - info")
    logger_blah.debug("BLAH - test1 - debug")
    logger_blah.warning("BLAH - test1 - warning")
    logger_blah.critical("BLAH - test1 - critical")
    logger_blah.exception("BLAH - test1 - exception: %s", "Test Exception String")

    # Fake our settings...
    settings = SettingsObject()
    settings.LOG_PATH = "./"
    settings.DEBUGGING = False
    logger_config = UnmanicLogger.__call__()
    logger_config.setup_logger(settings)

    # Test two (everything CRITICAL and EXCEPTION level only on console and unmanic.log)
    print("### Critical logging or greater only. Able to log to ./unmanic.log")
    logger1.info("Default - test2 - info")
    logger1.debug("Default - test2 - debug")
    logger1.warning("Default - test2 - warning")
    logger1.critical("Default - test2 - critical")
    logger1.exception("Default - test2 - exception: %s", "Test Exception String")

    logger_blah.info("BLAH - test2 - info")
    logger_blah.debug("BLAH - test2 - debug")
    logger_blah.warning("BLAH - test2 - warning")
    logger_blah.critical("BLAH - test2 - critical")
    logger_blah.exception("BLAH - test2 - exception: %s", "Test Exception String")

def test_logging_special_characters():
    unmanic_logging = UnmanicLogger.__call__()
    main_logger = unmanic_logging.get_logger()
    main_logger.info("Check that these characters display correctly")
    main_logger.info("Success: \u251c – € ’ “ ” « » — à á ã ç ê é í ó õ ú")
    main_logger.info("Fails: \udce2\udc80\udc98")

