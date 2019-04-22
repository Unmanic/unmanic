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


import tornado.web



class SettingsUIRequestHandler(tornado.web.RequestHandler):
    def initialize(self, data_queues, settings):
        self.name        = 'settings'
        self.step        = 'general'
        self.config      = settings
        self.data_queues = data_queues
        self.components  = []

    def get(self, path):
        step_list = self.get_query_arguments('step')
        if step_list:
            self.step = step_list[0]
        if self.get_query_arguments('save'):
            self.write("Hello, world. You are pointing to - '{}'".format(self.get_query_arguments('save')))
        else:
            items = ["Item 1", "Item 2", "Item 3"]
            self.components = [x for x in self.request.path.split("/") if x]
            self.render("settings.html", title="My title", config=self.config, items=items)

    def post(self, path):
        current_config_dict = self.config.get_config_as_dict()
        for config_item in current_config_dict.keys():
            value = self.get_arguments(config_item)
            if value:
                self.config.set_config_item(config_item, value[0])
        self.get(path)
