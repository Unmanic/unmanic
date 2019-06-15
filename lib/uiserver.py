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


import os
import time
import threading
import queue
import socket
import ssl
import tornado.ioloop
import tornado.log as tornado_log
import tornado.web
import tornado.template
from tornado.httpserver import HTTPServer
import asyncio

from webserver.history import HistoryUIRequestHandler
from webserver.main import MainUIRequestHandler
from webserver.settings import SettingsUIRequestHandler

from lib import common

# TODO Move these settings parsing to their own file
settings = {}
settings['template_loader'] = tornado.template.Loader("webserver/templates")
settings['static_path'] = os.path.join(os.path.dirname(__file__), "..", "webserver", "assets")
settings['debug'] = True


class UIServer(threading.Thread):
    def __init__(self, data_queues, settings, workerHandle):
        super(UIServer, self).__init__(name='UIServer')
        self.settings = settings
        self.app = None
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.inotifytasks = data_queues["inotifytasks"]
        self.workerHandle = workerHandle
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.set_logging()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def set_logging(self):
        # TODO: This is not logging to a file correctly
        if self.settings and self.settings.LOG_PATH:
            # Create directory if not exists
            if not os.path.exists(self.settings.LOG_PATH):
                os.makedirs(self.settings.LOG_PATH)
            import logging
            # Create file handler
            log_file = os.path.join(self.settings.LOG_PATH, 'tornado.log')
            file_handler = logging.FileHandler(log_file)
            torando_logger = logging.getLogger("tornado.application")
            file_handler.setLevel(logging.INFO)
            torando_logger.setLevel(logging.INFO)
            torando_logger.addHandler(file_handler)
            tornado_log.enable_pretty_logging()

    def run(self):
        self._log("Settings up UIServer event loop...")
        asyncio.set_event_loop(asyncio.new_event_loop())

        # Load the app
        self.app = self.makeApp()
        self._log("Listening on port 8888")
        self._log(settings['static_path'])
        self.app.listen(8888)

        tornado.ioloop.IOLoop.current().start()

    def makeApp(self):
        return tornado.web.Application([
            (r"/assets/(.*)", tornado.web.StaticFileHandler, dict(
                path=settings['static_path']
            )),
            (r"/history/(.*)", HistoryUIRequestHandler, dict(
                data_queues=self.data_queues,
                workerHandle=self.workerHandle,
                settings=self.settings
            )),
            (r"/settings/(.*)", SettingsUIRequestHandler, dict(
                data_queues=self.data_queues,
                settings=self.settings
            )),
            (r"/(.*)", MainUIRequestHandler, dict(
                data_queues=self.data_queues,
                workerHandle=self.workerHandle,
                settings=self.settings
            )),
        ], **settings)


if __name__ == "__main__":
    print("Starting UI Server")
    data_queues = {
        "scheduledtasks": queue.Queue(),
        "inotifytasks": queue.Queue()
    }
    settings = None
    uiserver = UIServer(data_queues, settings)
    uiserver.daemon = True
    uiserver.start()
    uiserver.join()
