#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unlogger.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 Sep 2019, (8:45 AM)
 
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
import sys

try:
    from lib import unlogger
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from lib import unlogger


class SettingsObject(object):
    pass


class TestClass(object):
    """
    TestClass

    Runs unit tests against the unlogger class

    """

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        # Logging file handler is disabled for unit tests
        unmanic_logging = unlogger.UnmanicLogger.__call__(False)
        unmanic_logging.get_logger()

    def test_logging_singleton(self):
        logger1 = unlogger.UnmanicLogger.__call__().get_logger()
        logger2 = unlogger.UnmanicLogger.__call__().get_logger()

        # Ensure singleton works:
        if logger1 == logger2:
            print("### Instances of UnmanicLogger are the same object")

        # Create a child logger
        logger_blah = unlogger.UnmanicLogger.__call__().get_logger("blah")

        # Test one (everything works on console, no logging to files)
        print("### Info logging - everything works on console, no logging to files")
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
        logger_config = unlogger.UnmanicLogger.__call__()
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

    def test_logging_special_characters(self):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        main_logger = unmanic_logging.get_logger()
        main_logger.info("Check that these characters display correctly")
        main_logger.info("Success: \u251c – € ’ “ ” « » — à á ã ç ê é í ó õ ú")
        main_logger.info("Fails: \udce2\udc80\udc98")

