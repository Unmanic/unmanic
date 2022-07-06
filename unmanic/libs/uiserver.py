#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.uiserver.py

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

import os
import socket
import threading
import asyncio
import logging
from queue import Queue

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from tornado.routing import PathMatches
from tornado.template import Loader
from tornado.web import Application, StaticFileHandler, RedirectHandler

from unmanic import config
from unmanic.libs import common
from unmanic.libs.singleton import SingletonType
from unmanic.webserver.downloads import DownloadsHandler

public_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "webserver", "public"))
tornado_settings = {
    'template_loader': Loader(public_directory),
    'static_css':      os.path.join(public_directory, "css"),
    'static_fonts':    os.path.join(public_directory, "fonts"),
    'static_icons':    os.path.join(public_directory, "icons"),
    'static_img':      os.path.join(public_directory, "img"),
    'static_js':       os.path.join(public_directory, "js"),
    'debug':           True,
    'autoreload':      False,
}


class FrontendPushMessages(Queue, metaclass=SingletonType):
    """
    Handles messages passed to the frontend.

    Messages are sent as objects. These objects require the following fields:
        - 'id'          : A unique ID of the message. Prevent messages duplication
        - 'type'        : The type of message - 'error', 'warning', 'success', or 'info'
        - 'code'        : A code to represent an I18n string for the frontend to display
        - 'message'     : Additional message string that can be appended to the I18n string displayed on the frontend.
        - 'timeout'     : The timeout for this message. If set to 0, then the message will persist until manually dismissed.

    """

    def _init(self, maxsize):
        self.all_items = set()
        Queue._init(self, maxsize)

    def put(self, item):
        # Ensure received item is valid
        self.__validate_item(item)
        # If it is not already in message list, add it to the list and the queue
        if item.get('id') not in self.all_items:
            self.all_items.add(item.get('id'))
            self.add_to_queue(item)

    def add_to_queue(self, item, block=True, timeout=None):
        Queue.put(self, item, block, timeout)

    @staticmethod
    def __validate_item(item):
        # Ensure all required keys are present
        for key in ['id', 'type', 'code', 'message', 'timeout']:
            if key not in item:
                raise Exception("Frontend message item incorrectly formatted. Missing key: '{}'".format(key))

        # Ensure the given type is valid
        if item.get('type') not in ['error', 'warning', 'success', 'info', 'status']:
            raise Exception(
                "Frontend message item's code must be in ['error', 'warning', 'success', 'info', 'status']. Received '{}'".format(
                    item.get('type')
                )
            )
        return True

    def get_all_items(self):
        items = []
        while not self.empty():
            items.append(self.get())
        return items

    def requeue_items(self, items):
        for item in items:
            self.add_to_queue(item)

    def remove_item(self, item_id):
        # Get all items out of queue
        current_items = self.get_all_items()
        # Create list of items that will be queued again
        requeue_items = []
        for current_item in current_items:
            if current_item.get('id') != item_id:
                requeue_items.append(current_item)
        # Remove the requested item ID from the all_items set
        lock = threading.RLock()
        lock.acquire()
        if item_id in self.all_items:
            self.all_items.remove(item_id)
        lock.release()
        # Add all requeue_items items back into the queue
        self.requeue_items(requeue_items)

    def read_all_items(self):
        # Get all items out of queue
        current_items = self.get_all_items()
        # Add all requeue_items items back into the queue
        self.requeue_items(current_items)
        # Return items list
        return current_items

    def update(self, item):
        # Ensure received item is valid
        self.__validate_item(item)
        # If it is not already in message list, add it to the list and the queue
        if item.get('id') not in self.all_items:
            self.all_items.add(item.get('id'))
            self.add_to_queue(item)
        else:
            # Get all items out of queue
            current_items = self.get_all_items()
            # Create list of items that will be queued again
            # This will not include the item requested for update
            lock = threading.RLock()
            lock.acquire()
            requeue_items = []
            for current_item in current_items:
                if current_item.get('id') != item.get('id'):
                    requeue_items.append(current_item)
                    continue
                requeue_items.append(item)
            # Add all requeue_items items back into the queue
            self.requeue_items(requeue_items)


class UnmanicDataQueues(object, metaclass=SingletonType):
    _unmanic_data_queues = {}

    def __init__(self):
        pass

    def set_unmanic_data_queues(self, unmanic_data_queues):
        self._unmanic_data_queues = unmanic_data_queues

    def get_unmanic_data_queues(self):
        return self._unmanic_data_queues


class UnmanicRunningTreads(object, metaclass=SingletonType):
    _unmanic_threads = {}

    def __init__(self):
        pass

    def set_unmanic_running_threads(self, unmanic_threads):
        self._unmanic_threads = unmanic_threads

    def get_unmanic_running_thread(self, name):
        return self._unmanic_threads.get(name)


class UIServer(threading.Thread):
    config = None
    started = False
    io_loop = None
    server = None
    app = None

    def __init__(self, unmanic_data_queues, foreman, developer):
        super(UIServer, self).__init__(name='UIServer')
        self.config = config.Config()

        self.developer = developer
        self.data_queues = unmanic_data_queues
        self.logger = unmanic_data_queues["logging"].get_logger(self.name)
        self.inotifytasks = unmanic_data_queues["inotifytasks"]
        # TODO: Move all logic out of template calling to foreman.
        #  Create methods here to handle the calls and rename to foreman
        self.foreman = foreman
        self.set_logging()
        # Add a singleton for handling the data queues for sending data to unmanic's other processes
        udq = UnmanicDataQueues()
        udq.set_unmanic_data_queues(unmanic_data_queues)
        urt = UnmanicRunningTreads()
        urt.set_unmanic_running_threads(
            {
                'foreman': foreman
            }
        )

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        if self.started:
            self.started = False
        if self.io_loop:
            self.io_loop.add_callback(self.io_loop.stop)

    def set_logging(self):
        if self.config and self.config.get_log_path():
            # Create directory if not exists
            if not os.path.exists(self.config.get_log_path()):
                os.makedirs(self.config.get_log_path())

            # Create file handler
            log_file = os.path.join(self.config.get_log_path(), 'tornado.log')
            file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', interval=1,
                                                                     backupCount=7)
            file_handler.setLevel(logging.INFO)

            # Set tornado.access logging to file. Disable propagation of logs
            tornado_access = logging.getLogger("tornado.access")
            if self.developer:
                tornado_access.setLevel(logging.DEBUG)
            else:
                tornado_access.setLevel(logging.INFO)
            tornado_access.addHandler(file_handler)
            tornado_access.propagate = False

            # Set tornado.application logging to file. Enable propagation of logs
            tornado_application = logging.getLogger("tornado.application")
            if self.developer:
                tornado_application.setLevel(logging.DEBUG)
            else:
                tornado_application.setLevel(logging.INFO)
            tornado_application.addHandler(file_handler)
            tornado_application.propagate = True  # Send logs also to root logger (command line)

            # Set tornado.general logging to file. Enable propagation of logs
            tornado_general = logging.getLogger("tornado.general")
            if self.developer:
                tornado_general.setLevel(logging.DEBUG)
            else:
                tornado_general.setLevel(logging.INFO)
            tornado_general.addHandler(file_handler)
            tornado_general.propagate = True  # Send logs also to root logger (command line)

    def update_tornado_settings(self):
        # Check if this is a development environment or not
        if self.developer:
            tornado_settings['autoreload'] = True
            tornado_settings['serve_traceback'] = True

    def run(self):
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        self.started = True

        # Configure tornado server based on config
        self.update_tornado_settings()

        # Load the app
        self.app = self.make_web_app()

        # TODO: add support for HTTPS

        # Web Server
        self.server = HTTPServer(
            self.app,
            ssl_options=None,
        )

        try:
            self.server.listen(int(self.config.get_ui_port()))
        except socket.error as e:
            self._log("Exception when setting WebUI port {}:".format(self.config.get_ui_port()), message2=str(e),
                      level="warning")
            raise SystemExit

        self.io_loop = IOLoop().current()
        self.io_loop.start()
        self.io_loop.close(True)

        self._log("Leaving UIServer loop...")

    def make_web_app(self):
        # Start with web application routes
        from unmanic.webserver.websocket import UnmanicWebsocketHandler
        app = Application([
            (r"/unmanic/websocket", UnmanicWebsocketHandler),
            (r"/unmanic/downloads/(.*)", DownloadsHandler),
            (r"/(.*)", RedirectHandler, dict(
                url="/unmanic/ui/dashboard/"
            )),
        ], **tornado_settings)

        # Add API routes
        from unmanic.webserver.api_request_router import APIRequestRouter
        app.add_handlers(r'.*', [
            (
                PathMatches(r"/unmanic/api/.*"),
                APIRequestRouter(app)
            ),
        ])

        # Add frontend routes
        from unmanic.webserver.main import MainUIRequestHandler
        app.add_handlers(r'.*', [
            (r"/unmanic/css/(.*)", StaticFileHandler, dict(
                path=tornado_settings['static_css']
            )),
            (r"/unmanic/fonts/(.*)", StaticFileHandler, dict(
                path=tornado_settings['static_fonts']
            )),
            (r"/unmanic/icons/(.*)", StaticFileHandler, dict(
                path=tornado_settings['static_icons']
            )),
            (r"/unmanic/img/(.*)", StaticFileHandler, dict(
                path=tornado_settings['static_img']
            )),
            (r"/unmanic/js/(.*)", StaticFileHandler, dict(
                path=tornado_settings['static_js']
            )),
            (
                PathMatches(r"/unmanic/ui/(.*)"),
                MainUIRequestHandler,
            ),
        ])

        # Add widgets routes
        from unmanic.webserver.plugins import DataPanelRequestHandler
        from unmanic.webserver.plugins import PluginStaticFileHandler
        from unmanic.webserver.plugins import PluginAPIRequestHandler
        app.add_handlers(r'.*', [
            (
                PathMatches(r"/unmanic/panel/[^/]+(/(?!static/|assets$).*)?$"),
                DataPanelRequestHandler
            ),
            (
                PathMatches(r"/unmanic/plugin_api/[^/]+(/(?!static/|assets$).*)?$"),
                PluginAPIRequestHandler
            ),
            (r"/unmanic/panel/.*/static/(.*)", PluginStaticFileHandler, dict(
                path=tornado_settings['static_img']
            )),
        ])

        if self.developer:
            self._log("API Docs - Updating...", level="debug")
            try:
                from unmanic.webserver.api_v2.schema.swagger import generate_swagger_file
                errors = generate_swagger_file()
                for error in errors:
                    self._log(error, level="warn")
                else:
                    self._log("API Docs - Updated successfully", level="debug")
            except Exception as e:
                self._log("Failed to reload API schema", message2=str(e), level="error")

        # Start the Swagger UI. Automatically generated swagger.json can also
        # be served using a separate Swagger-service.
        from swagger_ui import tornado_api_doc
        tornado_api_doc(
            app,
            config_path=os.path.join(os.path.dirname(__file__), "..", "webserver", "docs", "api_schema_v2.json"),
            url_prefix="/unmanic/swagger",
            title="Unmanic application API"
        )

        return app
