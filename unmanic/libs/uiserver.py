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
import queue
import asyncio
import logging

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from tornado.routing import PathMatches
from tornado.template import Loader
from tornado.web import Application, StaticFileHandler, RedirectHandler

from unmanic import config
from unmanic.libs import common
from unmanic.libs.singleton import SingletonType
from unmanic.webserver.api_request_router import APIRequestRouter
from unmanic.webserver.history import HistoryUIRequestHandler
from unmanic.webserver.main import MainUIRequestHandler, DashboardWebSocket
from unmanic.webserver.plugins import PluginsUIRequestHandler
from unmanic.webserver.settings import SettingsUIRequestHandler
from unmanic.webserver.helpers.element_filebrowser import ElementFileBrowserUIRequestHandler

templates_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'webserver', 'templates'))

tornado_settings = {
    'template_loader': Loader(templates_dir),
    'static_path':     os.path.join(os.path.dirname(__file__), "..", "webserver", "assets"),
    'debug':           True,
    'autoreload':      False,
}


class UnmanicDataQueues(object, metaclass=SingletonType):
    _unmanic_data_queues = []

    def __init__(self):
        pass

    def set_unmanic_data_queues(self, unmanic_data_queues):
        self._unmanic_data_queues = unmanic_data_queues

    def get_unmanic_data_queues(self):
        return self._unmanic_data_queues


class UIServer(threading.Thread):
    config = None
    started = False
    io_loop = None
    server = None
    app = None

    def __init__(self, unmanic_data_queues, foreman, developer):
        super(UIServer, self).__init__(name='UIServer')
        self.config = config.CONFIG()

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
            tornado_access.setLevel(logging.INFO)
            tornado_access.addHandler(file_handler)
            tornado_access.propagate = False

            # Set tornado.application logging to file. Enable propagation of logs
            tornado_application = logging.getLogger("tornado.application")
            tornado_application.setLevel(logging.INFO)
            tornado_application.addHandler(file_handler)
            tornado_application.propagate = True  # Send logs also to root logger (command line)

            # Set tornado.general logging to file. Enable propagation of logs
            tornado_general = logging.getLogger("tornado.general")
            tornado_general.setLevel(logging.INFO)
            tornado_general.addHandler(file_handler)
            tornado_general.propagate = True  # Send logs also to root logger (command line)

    def update_tornado_settings(self):
        # Check if this is a development environment or not
        if self.developer:
            tornado_settings['autoreload'] = True

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
            self.server.listen(int(self.config.UI_PORT))
        except socket.error as e:
            self._log("Exception when setting WebUI port {}:".format(self.config.UI_PORT), message2=str(e), level="warning")
            raise SystemExit

        self.io_loop = IOLoop().current()
        self.io_loop.start()
        self.io_loop.close(True)

        self._log("Leaving UIServer loop...")

    def make_web_app(self):
        # Start with web application routes
        app = Application([
            (r"/assets/(.*)", StaticFileHandler, dict(
                path=tornado_settings['static_path']
            )),
            (r"/dashboard/(.*)", MainUIRequestHandler, dict(
                data_queues=self.data_queues,
                foreman=self.foreman,
            )),
            (r"/dashws", DashboardWebSocket, dict(
                data_queues=self.data_queues,
                foreman=self.foreman,
            )),
            (r"/history/(.*)", HistoryUIRequestHandler, dict(
                data_queues=self.data_queues,
            )),
            (r"/plugins/(.*)", PluginsUIRequestHandler, dict(
                data_queues=self.data_queues,
            )),
            (r"/settings/(.*)", SettingsUIRequestHandler, dict(
                data_queues=self.data_queues,
            )),
            (r"/filebrowser/(.*)", ElementFileBrowserUIRequestHandler, dict(
                data_queues=self.data_queues,
            )),
            (r"/(.*)", RedirectHandler, dict(
                url="/dashboard/"
            )),
        ], **tornado_settings)

        # Add API routes
        app.add_handlers(r'.*', [(
            PathMatches(r"/api/.*"),
            APIRequestRouter(app)
        ), ])

        return app


if __name__ == "__main__":
    print("Starting UI Server")
    data_queues = {
        "scheduledtasks": queue.Queue(),
        "inotifytasks":   queue.Queue()
    }
    settings = None
    uiserver = UIServer(data_queues, settings)
    uiserver.daemon = True
    uiserver.start()
    uiserver.join()
