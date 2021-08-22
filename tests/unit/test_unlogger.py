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

import pytest

try:
    from unmanic.libs import unlogger
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import unlogger


class SettingsObject(object):
    pass



# TODO: Re-enable unit test once config object can be called without a DB connection
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

    @pytest.mark.unittest
    def test_logging_special_characters(self):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        main_logger = unmanic_logging.get_logger()
        main_logger.info("Check that these characters display correctly")
        main_logger.info("Success: \u251c – € ’ “ ” « » — à á ã ç ê é í ó õ ú")
        main_logger.info("Fails: \udce2\udc80\udc98")
