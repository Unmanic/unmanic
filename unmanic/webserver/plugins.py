#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugins.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     28 Feb 2021, (10:26 PM)

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
import tornado.web

from unmanic import config
from unmanic.libs import session


class PluginsUIRequestHandler(tornado.web.RequestHandler):
    name = None
    config = None
    session = None

    data_queues = None
    data = None

    def initialize(self, data_queues):
        self.name = 'plugins'
        self.config = config.CONFIG()
        self.session = session.Session()

        self.data_queues = data_queues
        self.data = {
            'plugin_types': [
                {
                    'id':          'library_management_file_test',
                    'name':        'Library Management - File test',
                    'plugin_type': 'library_management.file_test',
                },
                {
                    'id':          'worker_process',
                    'name':        'Worker - Processing file',
                    'plugin_type': 'worker.process_item',
                },
                {
                    'id':          'postprocessor_file_movement',
                    'name':        'Post-processor - File movements',
                    'plugin_type': 'postprocessor.file_move',
                },
                {
                    'id':          'postprocessor_task_results',
                    'name':        'Post-processor - Marking task success/failure',
                    'plugin_type': 'postprocessor.task_result',
                },
            ]
        }

    def get(self, path):
        self.render("plugins/plugins.html", config=self.config, data=self.data, session=self.session)
