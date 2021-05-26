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
        self.config = config.CONFIG()
        self.session = session.Session()

        self.step = 'general'
        self.data_queues = data_queues
        self.components = []

    def get(self, path):
        step_list = self.get_query_arguments('step')
        if step_list:
            self.step = step_list[0]
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

    def current_ffmpeg_command(self):
        from unmanic.webserver.helpers import ffmpegmediator
        example_ffmpeg_args = ffmpegmediator.generate_example_ffmpeg_args(self.config)

        # Create command with infile, outfile and the arguments
        example_command = ['ffmpeg'] + example_ffmpeg_args

        # Return the full example command
        return "{}".format(' '.join(example_command))

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
