#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugins.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Aug 2021, (3:49 PM)

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
import sys
import traceback

import tornado.web
import tornado.log

from unmanic.webserver.helpers import plugins


def get_plugin_by_path(path):
    # Get the plugin ID from the url
    split_path = path.split('/')
    plugin_type = split_path[2]
    plugin_id = split_path[3]
    if plugin_type == 'plugin_api':
        # Fetch all api plugins
        results = plugins.get_enabled_plugin_plugin_apis()
    else:
        # Fetch all frontend plugins
        results = plugins.get_enabled_plugin_data_panels()
    # Check if their path matches
    plugin_module = None
    for result in results:
        if plugin_id == result.get('plugin_id'):
            plugin_module = result
            break
    return plugin_module


class DataPanelRequestHandler(tornado.web.RequestHandler):
    name = None

    def initialize(self):
        self.name = 'DataPanel'

    def get(self, path):
        self.handle_panel_request()

    def handle_panel_request(self):
        # Get the remainder of the path after the plugin ID. This will be passed as path
        path = list(filter(None, self.request.path.split('/')[4:]))

        # Generate default data
        data = {
            'content_type': 'text/html',
            'content':      "<!doctype html>"
                            "<html>"
                            "<head></head>"
                            "<body></body>"
                            "</html>",
            'path':         "/" + "/".join(path),
            'uri':          self.request.uri,
            'query':        self.request.query,
            'arguments':    self.request.arguments,
        }
        plugin_module = get_plugin_by_path(self.request.path)
        if not plugin_module:
            self.set_status(404)
            self.write('404 Not Found')
            return

        # Run plugin and fetch return data
        if not plugins.exec_data_panels_plugin_runner(data, plugin_module.get('plugin_id')):
            tornado.log.app_log.exception(
                "Exception while carrying out plugin runner on DataPanel '{}'".format(plugin_module.get('plugin_id')))

        self.render_data(data)
        return

    def render_data(self, data):
        self.set_header("Content-Type", data.get('content_type', 'text/html'))
        self.write(data.get('content'))


class PluginAPIRequestHandler(tornado.web.RequestHandler):
    name = None

    def initialize(self):
        self.name = 'PluginAPI'

    def get(self, path):
        self.handle_panel_request()

    def post(self, path):
        self.handle_panel_request()

    def handle_panel_request(self):
        path = list(filter(None, self.request.path.split('/')[4:]))

        # Generate default data
        data = {
            'content_type': 'application/json',
            'content':      {},
            'path':         "/" + "/".join(path),
            'uri':          self.request.uri,
            'query':        self.request.query,
            'arguments':    self.request.arguments,
            'body':         self.request.body,
        }
        plugin_module = get_plugin_by_path(self.request.path)
        if not plugin_module:
            self.set_status(404, reason="404 Not Found")
            status_code = self.get_status()
            self.write({
                'error':    "%(code)d: %(message)s" % {"code": status_code, "message": self._reason},
                'messages': {},
            })
            return

        # Run plugin and fetch return data
        try:
            if not plugins.exec_plugin_api_plugin_runner(data, plugin_module.get('plugin_id')):
                tornado.log.app_log.exception(
                    "Exception while carrying out plugin runner on PluginAPI '{}'".format(plugin_module.get('plugin_id')))
        except Exception as e:
            self.set_status(500, reason="Error running plugin API: {}".format(str(e)))
            status_code = self.get_status()
            exc_info = sys.exc_info()
            traceback_lines = []
            if exc_info and exc_info[0]:
                for line in traceback.format_exception(*exc_info):
                    traceback_lines.append(line)
            self.write({
                'error':     "%(code)d: %(message)s" % {"code": status_code, "message": self._reason},
                'messages':  {},
                'traceback': traceback_lines
            })
            return

        self.render_data(data)

    def render_data(self, data):
        self.set_header("Content-Type", data.get('content_type', 'application/json'))
        self.write(data.get('content'))


class PluginStaticFileHandler(tornado.web.StaticFileHandler):
    """
    A static file handler which serves static content from a plugin '/static/' directory.
    """

    def initialize(self, path, default_filename=None):
        plugin_module = get_plugin_by_path(self.request.path)
        if plugin_module:
            path = os.path.join(plugin_module.get('plugin_path'), 'static')
        super(PluginStaticFileHandler, self).initialize(path, default_filename)
