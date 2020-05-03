#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_unffmpeg_containers.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     15 Sep 2019, (7:09 PM)
 
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
    from unmanic.libs import common, unlogger
    from unmanic.libs.unffmpeg import containers
except ImportError:
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_dir)
    from unmanic.libs import common, unlogger
    from unmanic.libs.unffmpeg import containers


class TestClass(object):
    """
    TestClass

    Runs unit tests against the unffmpeg container's class

    """

    def setup_class(self):
        """
        Setup the class state for pytest
        :return:
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # sys.path.append(self.project_dir)
        unmanic_logging = unlogger.UnmanicLogger.__call__(False)
        unmanic_logging.get_logger()

    def test_ensure_we_can_read_list_of_supported_containers(self):
        supported_containers = containers.get_all_containers()
        # Ensure that a list of containers was returned
        assert supported_containers
        # Ensure AVI containers are supported correctly
        assert supported_containers['avi']
        assert supported_containers['avi']['extension'] == 'avi'
        assert supported_containers['avi']['supports_subtitles']
        # Ensure MKV containers are supported correctly
        assert supported_containers['matroska']
        assert supported_containers['matroska']['extension'] == 'mkv'
        assert supported_containers['matroska']['supports_subtitles']

    def test_ensure_we_can_grab_module_of_a_supported_container(self):
        supported_containers = containers.get_all_containers()
        # Ensure that a list of containers was returned
        assert supported_containers
        for supported_container in supported_containers.keys():
            container = containers.grab_module(supported_container)
            # Ensure the module's extension is retrieved by the base class's container_extension function
            assert container.extension == container.container_extension()
            # Ensure the module's description is retrieved by the base class's container_description function
            assert container.description == container.container_description()
            # If the module supports subtitles, ensure this is returned by the
            # base class's container_supports_subtitles function
            if container.supports_subtitles:
                assert container.container_supports_subtitles()
