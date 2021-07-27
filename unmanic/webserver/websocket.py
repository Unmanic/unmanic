#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.websocket.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Jul 2021, (6:08 PM)

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
from tornado import gen, log

from unmanic import config
from unmanic.libs import common, history, session
from unmanic.libs.uiserver import UnmanicDataQueues, UnmanicRunningTreads
from unmanic.webserver.helpers import completed_tasks, pending_tasks


class UnmanicWebsocketHandler(tornado.websocket.WebSocketHandler):
    name = None
    config = None
    sending_worker_info = False
    sending_pending_tasks_info = False
    sending_completed_tasks_info = False
    close_event = False

    def __init__(self, *args, **kwargs):
        self.name = 'UnmanicWebsocketHandler'
        self.config = config.CONFIG()
        self.server_id = str(uuid.uuid4())
        udq = UnmanicDataQueues()
        urt = UnmanicRunningTreads()
        self.data_queues = udq.get_unmanic_data_queues()
        self.foreman = urt.get_unmanic_running_thread('foreman')
        self.session = session.Session()
        super(UnmanicWebsocketHandler, self).__init__(*args, **kwargs)

    def open(self):
        tornado.log.app_log.warning('WS Opened', exc_info=True)
        self.close_event = tornado.locks.Event()

    def on_message(self, message):
        switcher = {
            'start_workers_info':         self.start_workers_info,
            'start_pending_tasks_info':   self.start_pending_tasks_info,
            'start_completed_tasks_info': self.start_completed_tasks_info,
        }
        # Get the function from switcher dictionary
        func = switcher.get(message, lambda: self.write_message({'success': False}))
        # Execute the function
        func()

    def on_close(self):
        tornado.log.app_log.warning('WS Closed', exc_info=True)
        self.close_event.set()
        self.sending_worker_info = False
        self.sending_completed_tasks_info = False

    def start_workers_info(self):
        self.sending_worker_info = True
        tornado.ioloop.IOLoop.current().spawn_callback(self.async_workers_info)

    def start_pending_tasks_info(self):
        self.sending_pending_tasks_info = True
        tornado.ioloop.IOLoop.current().spawn_callback(self.async_pending_tasks_info)

    def start_completed_tasks_info(self):
        self.sending_completed_tasks_info = True
        tornado.ioloop.IOLoop.current().spawn_callback(self.async_completed_tasks_info)

    async def send(self, message):
        if self.ws_connection:
            await self.write_message(message)

    async def async_workers_info(self):
        while self.sending_worker_info:
            workers_info = self.foreman.get_all_worker_status()

            # Send message to client
            await self.send(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'workers_info',
                    'data':      workers_info,
                }
            )

            # Sleep for X seconds
            await gen.sleep(.2)

    async def async_pending_tasks_info(self):
        while self.sending_pending_tasks_info:
            results = []
            params = {
                'start':        '0',
                'length':       '10',
                'search_value': '',
                'order':        {
                    "column": 'finish_time',
                    "dir":    'desc',
                }
            }
            task_list = pending_tasks.prepare_filtered_pending_tasks(params)

            for task_result in task_list.get('results', []):
                # Append the task to the results list
                results.append(
                    {
                        'id':       task_result['id'],
                        'label':    task_result['abspath'],
                        'priority': task_result['priority'],
                        'status':   task_result['status'],
                    }
                )

            # Send message to client
            await self.send(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'pending_tasks',
                    'data':      {
                        'results': results
                    },
                }
            )

            # Sleep for X seconds
            await gen.sleep(3)

    async def async_completed_tasks_info(self):
        while self.sending_completed_tasks_info:
            results = []
            params = {
                'start':        '0',
                'length':       '10',
                'search_value': '',
                'order':        {
                    "column": 'finish_time',
                    "dir":    'desc',
                }
            }
            task_list = completed_tasks.prepare_filtered_completed_tasks(params)

            for task_result in task_list.get('results', []):
                # Set human readable time
                if (int(task_result['finish_time']) + 60) > int(time.time()):
                    human_readable_time = 'Just Now'
                else:
                    human_readable_time = common.make_timestamp_human_readable(int(task_result['finish_time']))

                # Append the task to the results list
                results.append(
                    {
                        'id':                  task_result['id'],
                        'label':               task_result['task_label'],
                        'success':             task_result['task_success'],
                        'finish_time':         task_result['finish_time'],
                        'human_readable_time': human_readable_time,
                    }
                )

            # Send message to client
            await self.send(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'completed_tasks',
                    'data':      {
                        'results': results
                    },
                }
            )

            # Sleep for X seconds
            await gen.sleep(3)
