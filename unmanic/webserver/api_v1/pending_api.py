#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.pending_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     26 Oct 2020, (2:26 PM)

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

import json
import os
import time
import tornado.web
import tornado.log
import tornado.routing

from unmanic.libs import task, common
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler


class ApiPendingHandler(BaseApiHandler):
    SUPPORTED_METHODS = ["GET", "POST"]
    name = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "method":       "add_tasks_to_pending_tasks_list",
            "path_pattern": r"/api/v1/pending/add/",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'pending_api'
        self.config = kwargs.get("settings")
        self.unmanic_data_queues = kwargs.get("unmanic_data_queues")
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def post(self, path):
        self.action_route()

    def add_tasks_to_pending_tasks_list(self, *args, **kwargs):
        """
        TODO: Add the given list of tasks to the pending task list

        :param args:
        :param kwargs:
        :return:
        """
        pass

    def create_task_from_path(self, pathname):
        """
        TODO: Generate a Task object from a pathname

        :param pathname:
        :return:
        """
        pass
