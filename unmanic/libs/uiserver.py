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
import threading
import queue
import tornado.ioloop
import tornado.log as tornado_log
import tornado.web
import tornado.template
import tornado.routing
import asyncio
import logging

from unmanic.libs import common
from unmanic.libs.singleton import SingletonType
from unmanic.webserver.api_request_router import APIRequestRouter
from unmanic.webserver.history import HistoryUIRequestHandler
from unmanic.webserver.main import MainUIRequestHandler
from unmanic.webserver.settings import SettingsUIRequestHandler
from unmanic.webserver.helpers.element_filebrowser import ElementFileBrowserUIRequestHandler

templates_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'webserver', 'templates'))

tornado_settings = {
    'template_loader': tornado.template.Loader(templates_dir),
    'static_path':     os.path.join(os.path.dirname(__file__), "..", "webserver", "assets"),
    'debug':           True
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
    def __init__(self, unmanic_data_queues, unmanic_settings, foreman):
        super(UIServer, self).__init__(name='UIServer')
        self.settings = unmanic_settings
        self.ioloop = None
        self.app = None
        self.data_queues = unmanic_data_queues
        self.logger = unmanic_data_queues["logging"].get_logger(self.name)
        self.inotifytasks = unmanic_data_queues["inotifytasks"]
        # TODO: Move all logic out of template calling to foreman.
        #  Create methods here to handle the calls and rename to foreman
        self.foreman = foreman
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.set_logging()
        # Add a singleton for handling the data queues for sending data to unmanic's other processes
        udq = UnmanicDataQueues()
        udq.set_unmanic_data_queues(unmanic_data_queues)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()
        self.ioloop.stop()

    def set_logging(self):
        if self.settings and self.settings.LOG_PATH:
            # Create directory if not exists
            if not os.path.exists(self.settings.LOG_PATH):
                os.makedirs(self.settings.LOG_PATH)

            # Create file handler
            log_file = os.path.join(self.settings.LOG_PATH, 'tornado.log')
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

            tornado_log.enable_pretty_logging()

    def run(self):
        self._log("Setting up UIServer loop...")
        asyncio.set_event_loop(asyncio.new_event_loop())

        self.ioloop = tornado.ioloop.IOLoop.current()

        # Load the app
        self.app = self.make_web_app()

        # Start app
        self._log("Listening on port {}".format(self.settings.UI_PORT))
        self._log(tornado_settings['static_path'])
        self.app.listen(int(self.settings.UI_PORT))

        self.ioloop.start()

        self._log("Leaving UIServer loop...")

    def make_web_app(self):
        # Start with web application routes
        app = tornado.web.Application([
            (r"/assets/(.*)", tornado.web.StaticFileHandler, dict(
                path=tornado_settings['static_path']
            )),
            (r"/dashboard/(.*)", MainUIRequestHandler, dict(
                data_queues=self.data_queues,
                foreman=self.foreman,
                settings=self.settings
            )),
            (r"/history/(.*)", HistoryUIRequestHandler, dict(
                data_queues=self.data_queues,
                settings=self.settings
            )),
            (r"/settings/(.*)", SettingsUIRequestHandler, dict(
                data_queues=self.data_queues,
                settings=self.settings
            )),
            (r"/filebrowser/(.*)", ElementFileBrowserUIRequestHandler, dict(
                data_queues=self.data_queues,
                settings=self.settings
            )),
            (r"/(.*)", tornado.web.RedirectHandler, dict(
                url="/dashboard/"
            )),
        ], **tornado_settings)

        # Add API routes
        app.add_handlers(r'.*', [(
            tornado.routing.PathMatches(r"/api/.*"),
            APIRequestRouter(app, settings=self.settings)
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
