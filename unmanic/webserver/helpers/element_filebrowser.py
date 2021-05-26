#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.element_filebrowser.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Oct 2020, (12:16 PM)

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
import json
import tornado.web


class ElementFileBrowserUIRequestHandler(tornado.web.RequestHandler):
    name = None
    step = None
    components = None

    def initialize(self):
        self.name = 'filebrowser'
        self.step = 'general'
        self.components = []

    def get(self, path):
        if self.get_query_arguments('current_path'):
            current_path = self.get_query_arguments('current_path')[0]
            list_type = self.get_query_arguments('list_type')[0] if self.get_query_arguments('list_type') else "all"
            content_type = "json" if self.get_query_arguments('json') else "ajax"
            input_field = self.get_query_arguments('input_field')[0] if self.get_query_arguments('input_field') else "UNKNOWN"
            title = self.get_query_arguments('title')[0] if self.get_query_arguments('title') else "Choose Directory"
            self.render_path(input_field, title, current_path, list_type, content_type)

    def post(self, path):
        if self.get_body_arguments('current_path'):
            current_path = self.get_argument('current_path')
            list_type = self.get_argument('list_type') if self.get_body_arguments('list_type') else "all"
            content_type = "json" if self.get_body_arguments('json') else "ajax"
            input_field = self.get_argument('input_field') if self.get_body_arguments('input_field') else "UNKNOWN"
            title = self.get_argument('title') if self.get_body_arguments('title') else "Choose Directory"
            self.render_path(input_field, title, current_path, list_type, content_type)

    def render_path(self, input_field, title, current_path, list_type="directories", content_type="ajax"):
        """
        Render a HTML file browser

        :param input_field:
        :param title:
        :param current_path:
        :param list_type:
        :param content_type:
        :return:
        """
        path_data = self.fetch_path_data(current_path, list_type)
        if content_type == "json":
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(path_data))
        else:
            self.set_header("Content-Type", "text/html")
            self.render("global/file-list.html", path_data=path_data, input_field=input_field, title=title)

    def fetch_path_data(self, current_path, list_type="directories"):
        """
        Returns an object filled with data pertaining to a particular path

        :param current_path:
        :param list_type:
        :return:
        """
        directories = []
        files = []
        if list_type == "directories" or list_type == "all":
            directories = self.fetch_directories(current_path)
        if list_type == "files" or list_type == "all":
            files = self.fetch_files(current_path)
        path_data = {
            "current_path": current_path,
            "list_type":    list_type,
            "directories":  directories,
            "files":        files,
            "success":      True,
        }
        return path_data

    def fetch_directories(self, path):
        """
        Fetch a list of directory objects based on a given path

        :param path:
        :return:
        """
        results = []
        if os.path.exists(path):
            # check if this is a root path or if it has a parent
            parent_path = os.path.join(path, '..')
            if os.path.exists(parent_path) and os.path.abspath(parent_path) != path:
                # Path has a parent, Add the double dots
                results.append(
                    {
                        "name":      "..",
                        "full_path": os.path.abspath(parent_path),
                    }
                )
            for item in sorted(os.listdir(path)):
                abspath = os.path.abspath(os.path.join(path, item))
                if os.path.isdir(abspath):
                    results.append(
                        {
                            "name":      item,
                            "full_path": abspath,
                        }
                    )
        else:
            # Path doesn't exist!
            # Just return the root dir as the first directory option
            results.append(
                {
                    "name":      "/",
                    "full_path": "/",
                }
            )
        return results

    def fetch_files(self, path):
        """
        Fetch a list of file objects based on a given path

        :param path:
        :return:
        """
        results = []
        if os.path.exists(path):
            for item in sorted(os.listdir(path)):
                abspath = os.path.abspath(os.path.join(path, item))
                if os.path.isfile(abspath):
                    results.append(
                        {
                            "name":      item,
                            "full_path": abspath,
                        }
                    )
        return results
