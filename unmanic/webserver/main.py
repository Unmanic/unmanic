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
import tornado.web
import tornado.websocket
from tornado.routing import PathMatches

from unmanic.libs import session


class MainUIRequestHandler(tornado.web.RequestHandler):
    name = None
    config = None
    session = None
    data_queues = None
    foreman = None
    components = None

    def initialize(self):
        self.name = 'main'
        self.session = session.Session()

    def get(self, path):
        self.set_header("Content-Type", "text/html")
        self.render("index.html")

    def handle_ajax_call(self, query):
        self.set_header("Content-Type", "application/json")
        if query == 'login':
            self.session.register_unmanic(force=True)
            self.redirect("/unmanic/ui/dashboard/")
