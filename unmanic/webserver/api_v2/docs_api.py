#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.docs_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 Jul 2021, (11:31 AM)

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

import tornado.log
from unmanic.libs import session
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiHandler, BaseApiError


class ApiDocsHandler(BaseApiHandler):
    name = None
    session = None
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/docs/privacypolicy",
            "supported_methods": ["GET"],
            "call_method":       "get_privacy_policy",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'session_api'
        self.session = session.Session()
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def get_privacy_policy(self, *args, **kwargs):
        try:
            privacy_policy_content = []
            privacy_policy_file = os.path.join(os.path.dirname(__file__), '..', 'docs', 'privacy_policy.md')
            if os.path.exists(privacy_policy_file):
                with open(privacy_policy_file, 'r') as f:
                    privacy_policy_content = f.readlines()
            if not privacy_policy_content:
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Unable to read privacy policy.")
                self.write_error()
                return
            else:
                self.write_success({
                    "content": privacy_policy_content,
                })
                return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
