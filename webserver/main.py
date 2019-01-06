#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Dec 06 2018, (7:21:18 AM)
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


import time
import tornado.web
import json


class MainUIRequestHandler(tornado.web.RequestHandler):
    def initialize(self, data_queues, workerHandle, settings):
        self.name           = 'main'
        self.data_queues    = data_queues
        self.workerHandle   = workerHandle
        self.components     = []
        self.config         = settings

    def get(self, path):
        if self.get_query_arguments('ajax'):
            # Print out the json based on the call
            self.handleAjaxCall(self.get_query_arguments('ajax')[0])
        else:
            self.render("main.html", time_now=time.time())

    def handleAjaxCall(self, query):
        self.set_header("Content-Type", "application/json")
        if query == 'workersInfo':
            self.write(json.dumps(self.getWorkersInfo()))
        if query == 'pendingTasks':
            if self.get_query_arguments('format') and 'html' in self.get_query_arguments('format'):
                self.set_header("Content-Type", "text/html")
                self.render("main-pending-tasks.html", time_now=time.time())
            else:
                self.write(json.dumps(self.getPendingTasks()))
        if query == 'historicalTasks':
            if self.get_query_arguments('format') and 'html' in self.get_query_arguments('format'):
                self.set_header("Content-Type", "text/html")
                self.render("main-completed-tasks.html", time_now=time.time())
            else:
                self.write(json.dumps(self.getHistoricalTasks()))

    def getWorkersInfo(self):
        return self.workerHandle.getAllWorkerStatus()

    def getWorkersCount(self):
        return len(self.workerHandle.getAllWorkerStatus())

    def getPendingTasks(self):
        return self.workerHandle.job_queue.listAllItems()

    def getHistoricalTasks(self):
        return self.workerHandle.getAllHistoricalTasks()

