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
import json
import queue
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
    sending_frontend_message = False
    sending_system_logs = False
    sending_worker_info = False
    sending_pending_tasks_info = False
    sending_completed_tasks_info = False
    close_event = False

    def __init__(self, *args, **kwargs):
        self.name = 'UnmanicWebsocketHandler'
        self.config = config.Config()
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
        try:
            message_data = json.loads(message)
            if message_data.get('command'):
                # Execute the function
                getattr(self, message_data.get('command', 'default_failure_response'))(params=message_data.get('params', {}))
        except json.decoder.JSONDecodeError:
            tornado.log.app_log.error('Received incorrectly formatted message - {}'.format(message), exc_info=False)

    def on_close(self):
        tornado.log.app_log.warning('WS Closed', exc_info=True)
        self.close_event.set()
        self.stop_frontend_messages()
        self.stop_workers_info()
        self.stop_pending_tasks_info()
        self.stop_completed_tasks_info()

    def default_failure_response(self, params=None):
        """
        WS Command - default_failure_response
        Returns a failure response

        :param params:
        :type params:
        :return:
        :rtype:
        """
        self.write_message({'success': False})

    def start_frontend_messages(self, params=None):
        """
        WS Command - start_frontend_messages
        Start sending messages from the application to the frontend.

        :param params:
        :type params:
        :return:
        :rtype:
        """
        if not self.sending_frontend_message:
            self.sending_frontend_message = True
            tornado.ioloop.IOLoop.current().spawn_callback(self.async_frontend_message)

    def stop_frontend_messages(self, params=None):
        """
        WS Command - stop_frontend_messages
        Stop sending messages from the application to the frontend.

        :param params:
        :type params:
        :return:
        :rtype:
        """
        self.sending_frontend_message = False

    def start_system_logs(self, params=None):
        """
        WS Command - start_system_logs
        Start sending system logs from the application to the frontend.

        :param params:
        :type params:
        :return:
        :rtype:
        """
        if not self.sending_system_logs:
            self.sending_system_logs = True
            tornado.ioloop.IOLoop.current().spawn_callback(self.async_system_logs)

    def stop_system_logs(self, params=None):
        """
        WS Command - stop_system_logs
        Stop sending system logs from the application to the frontend.

        :param params:
        :type params:
        :return:
        :rtype:
        """
        self.sending_system_logs = False

    def start_workers_info(self, params=None):
        """
        WS Command - start_workers_info
        Start sending information pertaining to the workers

        :param params:
        :type params:
        :return:
        :rtype:
        """
        if not self.sending_worker_info:
            self.sending_worker_info = True
            tornado.ioloop.IOLoop.current().spawn_callback(self.async_workers_info)

    def stop_workers_info(self, params=None):
        """
        WS Command - stop_workers_info
        Stop sending information pertaining to the workers

        :param params:
        :type params:
        :return:
        :rtype:
        """
        self.sending_worker_info = False

    def start_pending_tasks_info(self, params=None):
        """
        WS Command - start_pending_tasks_info
        Start sending information pertaining to the pending tasks list

        :param params:
        :type params:
        :return:
        :rtype:
        """
        if not self.sending_pending_tasks_info:
            self.sending_pending_tasks_info = True
            tornado.ioloop.IOLoop.current().spawn_callback(self.async_pending_tasks_info)

    def stop_pending_tasks_info(self, params=None):
        """
        WS Command - stop_pending_tasks_info
        Stop sending information pertaining to the pending tasks list

        :param params:
        :type params:
        :return:
        :rtype:
        """
        self.sending_pending_tasks_info = False

    def start_completed_tasks_info(self, params=None):
        """
        WS Command - start_completed_tasks_info
        Start sending information pertaining to the completed tasks list

        :param params:
        :type params:
        :return:
        :rtype:
        """
        if not self.sending_completed_tasks_info:
            self.sending_completed_tasks_info = True
            tornado.ioloop.IOLoop.current().spawn_callback(self.async_completed_tasks_info)

    def stop_completed_tasks_info(self, params=None):
        """
        WS Command - stop_completed_tasks_info
        Stop sending information pertaining to the completed tasks list

        :param params:
        :type params:
        :return:
        :rtype:
        """
        self.sending_completed_tasks_info = False

    def dismiss_message(self, params=None):
        """
        WS Command - dismiss_message
        Dismiss a specified message by id.

        params:
            - message_id    - The ID of the message to be dismissed

        :param params:
        :type params:
        :return:
        :rtype:
        """
        frontend_messages = self.data_queues.get('frontend_messages')
        frontend_messages.remove_item(params.get('message_id', ''))

    async def send(self, message):
        if self.ws_connection:
            await self.write_message(message)

    async def async_frontend_message(self):
        while self.sending_frontend_message:
            frontend_messages = self.data_queues.get('frontend_messages')
            frontend_message_items = frontend_messages.read_all_items()
            # Send message to client
            await self.send(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'frontend_message',
                    'data':      frontend_message_items,
                }
            )

            # Sleep for X seconds
            await gen.sleep(.2)

    async def async_system_logs(self):
        while self.sending_system_logs:
            system_logs = self.config.read_system_logs(lines=35)

            # Send message to client
            await self.send(
                {
                    'success':   True,
                    'server_id': self.server_id,
                    'type':      'system_logs',
                    'data':      {
                        "logs_path":   self.config.get_log_path(),
                        'system_logs': system_logs,
                    },
                }
            )

            # Sleep for X seconds
            await gen.sleep(1)

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
                    "column": 'priority',
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
