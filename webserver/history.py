#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     19 May 2019, (2:28 PM)
 
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


class HistoryUIRequestHandler(tornado.web.RequestHandler):
    def initialize(self, data_queues, workerHandle, settings):
        self.name = 'history'
        self.config = settings
        self.data_queues = data_queues
        self.workerHandle = workerHandle
        self.data = {}

    def get(self, path):
        if self.get_query_arguments('ajax'):
            # Print out the json based on the call
            self.handleAjaxCall(self.get_query_arguments('ajax')[0])
        else:
            self.set_page_data()
            self.render("history.html", config=self.config, data=self.data)

    def handleAjaxCall(self, query):
        if query == 'conversionDetails':
            if self.get_query_arguments('jobId')[0]:
                job_data = self.get_historical_job_data(self.get_query_arguments('jobId')[0])
                print(job_data)
                self.set_header("Content-Type", "text/html")
                self.render("history-conversion-details.html", job_data=job_data)

    def get_historical_tasks(self):
        return self.workerHandle.getAllHistoricalTasks()

    def get_historical_job_data(self, job_id):
        return self.config.read_completed_job_data(job_id)

    def set_page_data(self):
        history_list = self.get_historical_tasks()
        self.data['historical_item_list'] = []
        self.data['success_count'] = 0
        self.data['failed_count'] = 0
        self.data['total_count'] = 0
        count = 0
        for item in history_list:
            # Set this item's ID
            # TODO: Set to py enumerate function and remove item id
            count += 1
            item['id'] = count
            # Set success status
            if item['success']:
                self.data['success_count'] += 1
            else:
                self.data['failed_count'] += 1
            self.data['total_count'] += 1
            self.data['historical_item_list'].append(item)
