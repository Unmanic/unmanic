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
import uuid

import tornado.web
import tornado.locks
import tornado.ioloop
import tornado.websocket
from tornado import gen

from unmanic import config
from unmanic.libs import common, history, session


class MainUIRequestHandler(tornado.web.RequestHandler):
    name = None
    config = None
    session = None
    data_queues = None
    foreman = None
    components = None

    def initialize(self, data_queues, foreman):
        self.name = 'main'
        self.config = config.CONFIG()
        self.session = session.Session()

        # TODO: Fetch data queues from uiserver.py
        self.data_queues = data_queues
        #self.foreman = foreman
        self.components = []

    def get(self, path):
        if self.get_query_arguments('ajax'):
            # Print out the json based on the call
            self.handle_ajax_call(self.get_query_arguments('ajax')[0])
        else:
            self.set_header("Content-Type", "text/html")
            self.render("main/main.html", time_now=time.time(),
                        session=self.session)

    def handle_ajax_call(self, query):
        self.set_header("Content-Type", "application/json")
        if query == 'login':
            self.session.register_unmanic(self.session.get_installation_uuid(), force=True)
            self.redirect("/dashboard/")

    def get_pending_tasks(self):
        # TODO: Configure pagination on the UI - limit 5,10,20,50,100 (default to 20)
        limit = 20
        return self.foreman.task_queue.list_pending_tasks(limit)


class DashboardWebSocket(tornado.websocket.WebSocketHandler):
    name = None
    config = None
    sending_worker_info = False
    sending_completed_tasks_info = False
    close_event = False

    def __init__(self, *args, **kwargs):
        self.name = 'dashws'
        self.config = config.CONFIG()
        self.server_id = str(uuid.uuid4())
        self.data_queues = kwargs.pop('data_queues')
        self.foreman = kwargs.pop('foreman')
        self.session = session.Session()
        super(DashboardWebSocket, self).__init__(*args, **kwargs)

    def open(self):
        self.close_event = tornado.locks.Event()

    def on_message(self, message):
        switcher = {
            'start_workers_info':         self.start_workers_info,
            'start_completed_tasks_info': self.start_completed_tasks_info,
        }
        # Get the function from switcher dictionary
        func = switcher.get(message, lambda: self.write_message({'success': False}))
        # Execute the function
        func()

    def on_close(self):
        self.close_event.set()
        self.sending_worker_info = False
        self.sending_completed_tasks_info = False

    def start_workers_info(self):
        self.sending_worker_info = True
        tornado.ioloop.IOLoop.current().spawn_callback(self.async_workers_info)

    def start_completed_tasks_info(self):
        self.sending_completed_tasks_info = True
        tornado.ioloop.IOLoop.current().spawn_callback(self.async_completed_tasks_info)

    async def async_workers_info(self):
        while self.sending_worker_info:
            workers_info = self.foreman.get_all_worker_status()
            await self.write_message(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'workers_info',
                    'data':      workers_info,
                }
            )
            await gen.sleep(.2)

    async def async_completed_tasks_info(self):
        while self.sending_completed_tasks_info:
            return_data = []
            history_logging = history.History(self.config)
            historic_task_list = list(history_logging.get_historic_task_list(20))
            for historical_item in historic_task_list:
                if (int(historical_item['finish_time']) + 60) > int(time.time()):
                    historical_item['human_readable_time'] = 'Just Now'
                else:
                    human_readable_time = common.make_timestamp_human_readable(int(historical_item['finish_time']))
                    historical_item['human_readable_time'] = human_readable_time
                return_data.append(historical_item)
            await self.write_message(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'completed_tasks',
                    'data':      return_data,
                }
            )
            await gen.sleep(10)
