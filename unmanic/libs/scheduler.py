#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.scheduler.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Sep 2021, (11:15 AM)

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
import threading
import time

import schedule

from unmanic.libs import common, unlogger
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.session import Session


class ScheduledTasksManager(threading.Thread):
    """
    Manage any tasks that Unmanic needs to execute at regular intervals
    """

    def __init__(self):
        super(ScheduledTasksManager, self).__init__(name='ScheduledTasksManager')
        self.logger = None
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        if not self.logger:
            unmanic_logging = unlogger.UnmanicLogger.__call__()
            self.logger = unmanic_logging.get_logger(self.name)
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting ScheduledTasks Monitor loop")

        # Create scheduled tasks
        # Check the session every 60 minutes
        schedule.every(60).minutes.do(self.register_unmanic)
        # Run the plugin repo update every 60 minutes
        schedule.every(60).minutes.do(self.plugin_repo_update)

        # Loop every 2 seconds to check if a task is due to be run
        while not self.abort_flag.is_set():
            time.sleep(2)
            # Check if scheduled task is due
            schedule.run_pending()

        # Clear any tasks and exit
        schedule.clear()
        self._log("Leaving ScheduledTasks Monitor loop...")

    def register_unmanic(self):
        self._log("Updating session data")
        s = Session()
        s.register_unmanic()

    def plugin_repo_update(self):
        self._log("Checking for updates to plugin repos")
        plugin_handler = PluginsHandler()
        plugin_handler.update_plugin_repos()
