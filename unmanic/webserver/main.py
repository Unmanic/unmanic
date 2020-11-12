#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.main.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2018, (7:21 AM)

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

import time
import tornado.web
import json

from unmanic.libs import common, history


class MainUIRequestHandler(tornado.web.RequestHandler):
    name = None
    data_queues = None
    foreman = None
    components = None
    config = None
    historic_task_list = None

    def initialize(self, data_queues, foreman, settings):
        self.name = 'main'
        self.data_queues = data_queues
        self.foreman = foreman
        self.components = []
        self.config = settings
        self.historic_task_list = []

    def get(self, path):
        if self.get_query_arguments('ajax'):
            # Print out the json based on the call
            self.handle_ajax_call(self.get_query_arguments('ajax')[0])
        else:
            self.get_historical_tasks()
            self.set_header("Content-Type", "text/html")
            self.render("main/main.html", historic_task_list=self.historic_task_list, time_now=time.time())

    def handle_ajax_call(self, query):
        self.set_header("Content-Type", "application/json")
        if query == 'workersInfo':
            if self.get_query_arguments('workerId'):
                worker_info = self.get_workers_info(self.get_query_arguments('workerId')[0])
                self.set_header("Content-Type", "text/html")
                self.render("main/main-worker-pie-chart.html", worker_info=worker_info)
            else:
                self.write(json.dumps(self.get_workers_info()))
        if query == 'pendingTasks':
            if self.get_query_arguments('format') and 'html' in self.get_query_arguments('format'):
                self.set_header("Content-Type", "text/html")
                self.render("main/main-pending-tasks.html", time_now=time.time())
            else:
                self.write(json.dumps(self.get_pending_tasks()))
        if query == 'historicalTasks':
            if self.get_query_arguments('format') and 'html' in self.get_query_arguments('format'):
                self.get_historical_tasks()
                self.set_header("Content-Type", "text/html")
                self.render("main/main-completed-tasks-list.html", historic_task_list=self.historic_task_list,
                            time_now=time.time())
            else:
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps(self.get_historical_tasks()))

    def get_workers_info(self, worker_id=None):
        if worker_id is not None:
            workers_info = self.foreman.get_worker_status(worker_id)
        else:
            workers_info = self.foreman.get_all_worker_status()
        return workers_info

    def get_workers_count(self):
        return len(self.foreman.get_all_worker_status())

    def get_pending_tasks(self):
        # TODO: Configure pagination on the UI - limit 5,10,20,50,100 (default to 20)
        limit = 20
        return self.foreman.task_queue.list_pending_tasks(limit)

    def get_historical_tasks(self):
        self.historic_task_list = []
        history_logging = history.History(self.config)
        historic_task_list = list(history_logging.get_historic_task_list(20))
        for historical_item in historic_task_list:
            human_readable_time = common.make_timestamp_human_readable(int(historical_item['finish_time']))
            historical_item['human_readable_time'] = human_readable_time
            self.historic_task_list.append(historical_item)
        return self.historic_task_list
