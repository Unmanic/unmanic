#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.session_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Mar 2021, (7:14 PM)

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
import tornado.log

from unmanic.libs import session
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler


class ApiSessionHandler(BaseApiHandler):
    name = None
    session = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "supported_methods": ["GET"],
            "call_method":       "get_sign_out_url",
            "path_pattern":      r"/api/v1/session/unmanic-sign-out-url",
        },
        {
            "supported_methods": ["GET"],
            "call_method":       "get_patreon_login_url",
            "path_pattern":      r"/api/v1/session/unmanic-patreon-login-url",
        },
        {
            "supported_methods": ["GET"],
            "call_method":       "get_patreon_page",
            "path_pattern":      r"/api/v1/session/unmanic-patreon-page",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'plugins_api'
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def get(self, path):
        self.action_route()

    def post(self, path):
        self.action_route()

    def get_sign_out_url(self, *args, **kwargs):
        uuid = self.session.get_installation_uuid()
        sign_out_url = self.session.get_sign_out_url()
        if not sign_out_url:
            self.write(json.dumps({"success": False}))
            return
        else:
            self.write(json.dumps({
                "success": True,
                "uuid":    uuid,
                "data":    {
                    "url": sign_out_url,
                }
            }))
            return

    def get_patreon_login_url(self, *args, **kwargs):
        uuid = self.session.get_installation_uuid()
        patreon_oauth_url = self.session.get_patreon_login_url()
        if not patreon_oauth_url:
            self.write(json.dumps({"success": False}))
            return
        else:
            self.write(json.dumps({
                "success": True,
                "uuid":    uuid,
                "data":    {
                    "url": patreon_oauth_url,
                }
            }))
            return

    def get_patreon_page(self, *args, **kwargs):
        uuid = self.session.get_installation_uuid()
        patreon_sponsor_page_data = self.session.get_patreon_sponsor_page()
        if not patreon_sponsor_page_data:
            self.write(json.dumps({"success": False}))
            return
        else:
            sponsor_page = patreon_sponsor_page_data.get("sponsor_page")
            self.write(json.dumps({
                "success": True,
                "uuid":    uuid,
                "data":    {
                    "sponsor_page": sponsor_page,
                }
            }))
            return
