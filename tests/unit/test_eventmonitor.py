#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.test_eventmonitor.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     30 Dec 2023, (6:59 PM)
 
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
  
           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import pytest
from unittest.mock import patch
from unmanic.libs.eventmonitor import EventHandler

class TestEventMonitor(object):
    def test_wait_for_file_stabilization_file_stable(self):
        """
        Test that confirms that True is returned when the file does not change size.
        It should only check the file size twice and sleep once.
        """
        file_path = "/path/to/file.txt"
        event_monitor = EventHandler([], 1, set())

        with patch("os.path.getsize") as mock_getsize, \
                patch("time.sleep") as mock_sleep:
            mock_getsize.return_value = 100

            result = event_monitor._wait_for_file_stabilization(file_path)

            assert result is True
            mock_getsize.assert_called_with(file_path)
            assert mock_getsize.call_count == 2
            assert mock_sleep.call_count == 1

    def test_wait_for_file_stabilization_file_not_stable(self):
        """
        Test that the method wait waits for the file to stabilize if the size changes.
        It should check the file size 4 times and sleep 3 times.
        """
        file_path = "/path/to/file.txt"
        event_monitor = EventHandler([], 1, set())

        with patch("os.path.getsize") as mock_getsize, \
                patch("time.sleep") as mock_sleep:
            mock_getsize.side_effect = [50, 100, 150, 150]

            result = event_monitor._wait_for_file_stabilization(file_path)

            assert result is True
            assert mock_getsize.call_count == 4
            assert mock_sleep.call_count == 3
            mock_getsize.assert_called_with(file_path)

    def test_wait_for_file_stabilization_file_deleted(self):
        """
        Test that the method raises an exception if the file is moved or deleted while being checked for stabilization.
        """
        file_path = "/path/to/file.txt"
        event_monitor = EventHandler([], 1, set())

        with patch("os.path.getsize") as mock_getsize, \
                patch("time.sleep") as mock_sleep:
            mock_getsize.side_effect = OSError

            with pytest.raises(OSError):
                event_monitor._wait_for_file_stabilization(file_path)

            mock_getsize.assert_called_once_with(file_path)
            mock_sleep.assert_not_called()

    def test_wait_for_file_stabilization_timeout_reached(self):
        """
        Test that ensures the method will throw a TimeoutError if the timeout is reached.
        Since each iteration requires a sleep of 1 second, the method should sleep once before raising the exception.
        """
        file_path = "/path/to/file.txt"
        event_monitor = EventHandler([], 1, set())

        with patch("os.path.getsize") as mock_getsize:
            mock_getsize.side_effect = [100, 200, 300, 400]

            with pytest.raises(TimeoutError):
                event_monitor._wait_for_file_stabilization(file_path, timeout_seconds=0.1)

            mock_getsize.assert_called_with(file_path)
            assert mock_getsize.call_count == 1
