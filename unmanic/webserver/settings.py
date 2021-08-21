#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.settings.py

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

from unmanic import config
from unmanic.libs import session


class SettingsUIRequestHandler(tornado.web.RequestHandler):
    name = None
    config = None
    session = None

    step = None
    data_queues = None
    components = None

    def initialize(self, data_queues):
        self.name = 'settings'
        self.config = config.Config()
        self.session = session.Session()

        self.step = 'general'
        self.data_queues = data_queues
        self.components = []

    def get(self, path):
        step_list = self.get_query_arguments('step')
        if step_list:
            self.step = step_list[0]
        if self.step == 'plugins':
            # Move plugins to settings for now...
            # This will all be deprecated once migrated to the new frontend
            data = self.get_plugin_data()
            self.render("plugins/plugins.html", config=self.config, data=data, session=self.session)
        else:
            self.components = [x for x in self.request.path.split("/") if x]
            self.render("settings/settings.html", config=self.config, session=self.session)

    def post(self, path):
        if self.get_body_arguments('ajax'):
            self.handle_ajax_post()
        else:
            for config_item in self.config.get_config_keys():
                value = self.get_arguments(config_item)
                if value:
                    self.config.set_config_item(config_item, value[0])
            self.redirect(self.request.uri)

    def handle_ajax_post(self):
        query = self.get_argument('ajax')
        self.set_header("Content-Type", "text/html")
        if query == 'reload_video_stream_encoder_selection':
            self.config.set_config_item('video_codec', self.get_argument('selected_video_codec'))
            self.render("settings/video_encoding/video_stream_encoder.html", config=self.config)
        elif query == 'reload_audio_stream_encoder_selection':
            self.config.set_config_item('audio_codec', self.get_argument('selected_audio_codec'))
            self.render("settings/audio_encoding/audio_stream_encoder.html", config=self.config)
        elif query == 'reload_audio_stream_encoder_cloning_selection':
            self.config.set_config_item('audio_codec_cloning', self.get_argument('selected_audio_codec_cloning'))
            self.render("settings/audio_encoding/audio_stream_encoder_cloning.html", config=self.config)

    def get_plugin_data(self):
        return {
            'plugin_types': [
                {
                    'id':          'library_management_file_test',
                    'name':        'Library Management - File test',
                    'plugin_type': 'library_management.file_test',
                },
                {
                    'id':          'worker_process',
                    'name':        'Worker - Processing file',
                    'plugin_type': 'worker.process_item',
                },
                {
                    'id':          'postprocessor_file_movement',
                    'name':        'Post-processor - File movements',
                    'plugin_type': 'postprocessor.file_move',
                },
                {
                    'id':          'postprocessor_task_results',
                    'name':        'Post-processor - Marking task success/failure',
                    'plugin_type': 'postprocessor.task_result',
                },
            ]
        }
