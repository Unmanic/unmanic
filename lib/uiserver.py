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
import tornado.web
import tornado.template
from tornado.httpserver import HTTPServer
import asyncio


from webserver.main import MainUIRequestHandler
from webserver.settings import SettingsUIRequestHandler

# TODO Move these settings parsing to their own file
settings = {}
settings['template_loader'] = tornado.template.Loader("webserver/templates")
settings['static_path'] = os.path.join(os.path.dirname(__file__), "..", "webserver", "assets")
settings['debug'] = True

class UIServer(threading.Thread):
    def __init__(self, data_queues, settings, workerHandle):
        super(UIServer, self).__init__(name='UIServer')
        self.settings       = settings
        self.app            = None
        self.data_queues    = data_queues
        self.messages       = data_queues["messages"]
        self.inotifytasks   = data_queues["inotifytasks"]
        self.workerHandle   = workerHandle
        self.abort_flag     = threading.Event()
        self.abort_flag.clear()

    def _log(self, message, message2 = '', level = "info"):
        message = "[{}] {}".format(self.name, message)
        self.messages.put({
              "message":message
            , "message2":message2
            , "level":level
        })

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
            (r"/assets/(.*)", tornado.web.StaticFileHandler,
                dict(path=settings['static_path'])),
            (r"/settings/(.*)", SettingsUIRequestHandler, dict(data_queues=self.data_queues, settings=self.settings)),
            (r"/(.*)", MainUIRequestHandler, dict(data_queues=self.data_queues, workerHandle=self.workerHandle)),
        ], **settings)



if __name__ == "__main__":
    print("Starting UI Server")
    data_queues = {
          "scheduledtasks": queue.Queue()
        , "inotifytasks":   queue.Queue()
        , "messages":       queue.Queue()
    }
    settings = None
    uiserver = UIServer(data_queues, settings)
    uiserver.daemon=True
    uiserver.start()
    uiserver.join()
