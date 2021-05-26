#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     19 May 2019, (2:28 PM)
 
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
import time
import tornado.web
import tornado.log

from unmanic import config
from unmanic.libs import history, session


class HistoryUIRequestHandler(tornado.web.RequestHandler):
    name = None
    config = None
    session = None

    data_queues = None
    data = None

    def initialize(self, data_queues):
        self.name = 'history'
        self.config = config.CONFIG()
        self.session = session.Session()

        # TODO: Fetch data queues from uiserver.py
        self.data_queues = data_queues
        self.data = {}

    def get(self, path):
        if self.get_query_arguments('ajax'):
            # Print out the json based on the call
            self.handle_ajax_call(self.get_query_arguments('ajax')[0])
        else:
            self.set_page_data()
            self.render("history/history.html", config=self.config, data=self.data, session=self.session)

    def handle_ajax_call(self, query):
        if query == 'conversionDetails':
            if self.get_query_arguments('jobId')[0]:
                job_data = self.get_historical_job_data_for_template(self.get_query_arguments('jobId')[0])
                # TODO: Make failed response more pretty
                if job_data:
                    if self.get_query_arguments('json'):
                        self.set_header("Content-Type", "application/json")
                        self.write(json.dumps(job_data))
                    else:
                        self.set_header("Content-Type", "text/html")
                        self.render("history/history-conversion-details.html", job_data=job_data)
        if query == 'reloadCompletedTaskList':
            job_id = None
            if self.get_query_arguments('jobId'):
                job_id = self.get_query_arguments('jobId')[0]
            self.set_page_data(job_id)
            if self.get_query_arguments('json'):
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps(self.data))
            else:
                self.set_header("Content-Type", "text/html")
                self.render("history/history-completed-tasks-list.html", config=self.config, data=self.data)

    def get_historical_tasks(self):
        history_logging = history.History(self.config)
        return history_logging.get_historic_task_list()

    def get_historical_job_data_for_template(self, job_id):
        history_logging = history.History(self.config)
        task_data = history_logging.get_historic_task_data_dictionary(job_id)
        if not task_data:
            return False
        # Set params as required in template
        template_task_data = {
            'id':               task_data['id'],
            'task_label':       task_data.get('task_label'),
            'statistics':       {
                'task_success':        task_data.get('task_success'),
                'duration':            '',
                'start_time':          task_data.get('start_time'),
                'finish_time':         task_data.get('finish_time'),
                'start_datetime':      '',
                'finish_datetime':     '',
                'processed_by_worker': task_data.get('processed_by_worker'),
            },
            'source':           {},
            'destination':      {},
            'ffmpeg_log':       '',
            'ffmpeg_log_lines': [],
        }

        # Generate source/destination ffprobe data
        source_file_size = 0
        destination_file_size = 0
        for probe in task_data.get('historictaskprobe_set', []):
            if probe['type'] == 'source':
                template_task_data['source'] = probe
                source_file_size = probe['size']
            elif probe['type'] == 'destination':
                template_task_data['destination'] = probe
                destination_file_size = probe['size']

        # Generate statistics data
        # TODO: Add audio and video encoder data
        template_task_data['statistics']['source_file_size'] = source_file_size
        template_task_data['statistics']['destination_file_size'] = destination_file_size

        for ffmpeg_log in task_data.get('historictaskffmpeglog_set', []):
            template_task_data['ffmpeg_log'] += ffmpeg_log['dump']
            template_task_data['ffmpeg_log_lines'] += self.format_ffmpeg_log_text(ffmpeg_log['dump'].split("\n"))

        try:
            template_task_data['statistics']['start_datetime'] = self.make_pretty_date_string(
                task_data.get('start_time'))
        except KeyError:
            tornado.log.app_log.warning("Error setting start datetime in historical item job data.", exc_info=True)

        try:
            template_task_data['statistics']['finish_datetime'] = self.make_pretty_date_string(
                task_data.get('finish_time'))
        except KeyError:
            tornado.log.app_log.warning("Error setting finish datetime in historical item job data.", exc_info=True)

        try:
            duration = task_data.get('finish_time') - task_data.get('start_time')
            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            pretty_duration = '{:d} hours, {:02d} minutes, {:02d} seconds'.format(int(h), int(m), int(s))
            template_task_data['statistics']['duration'] = pretty_duration
        except KeyError:
            tornado.log.app_log.warning("Error setting duration in historical item job data.", exc_info=True)

        return template_task_data

    def format_ffmpeg_log_text(self, log_lines):
        return_list = []
        pre_text = False
        headers = ['RUNNER:', 'COMMAND:', 'LOG:']
        for i, line in enumerate(log_lines):
            line_text = line

            # Add PRE to lines
            if line_text and pre_text and line_text.rstrip() not in headers:
                line_text = '<pre>{}</pre>'.format(line_text)

            # Add bold to headers
            line_text = line_text if line_text.rstrip() not in headers else '<b>{}</b>'.format(line_text)

            # Replace leading whitespace
            stripped = line.lstrip()
            line_text = "&nbsp;" * (len(line) - len(stripped)) + line_text

            # If log section is COMMAND:
            if 'RUNNER:' in line_text:
                pre_text = False
            elif 'COMMAND:' in line_text:
                pre_text = True
            elif 'LOG:' in line_text:
                pre_text = False
            return_list.append(line_text)
        return return_list

    def set_page_data(self, task_id=None):
        historical_tasks = self.get_historical_tasks()
        self.data['historical_item_list'] = []
        self.data['success_count'] = 0
        self.data['failed_count'] = 0
        self.data['total_count'] = 0
        for task in historical_tasks:
            # Set params as required in template
            item = {
                'id':          task['id'],
                'success':     task['task_success'],
                'selected':    False,
                'task_label':  task['task_label'],
                'finish_date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task['finish_time'])),
            }

            # Check if this item is meant to be selected
            try:
                if task_id == item['id']:
                    item['selected'] = True
            except KeyError:
                tornado.log.app_log.debug("Error locating 'id' in historical item job data.", exc_info=True)
            # Set success status
            if item['success']:
                self.data['success_count'] += 1
            else:
                self.data['failed_count'] += 1
            self.data['total_count'] += 1
            self.data['historical_item_list'].append(item)

    def make_pretty_date_string(self, date):
        return time.strftime('%d %B, %Y - %H:%M:%S', time.gmtime(date))
