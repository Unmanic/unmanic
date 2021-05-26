#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.file_browser_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Apr 2021, (7:06 PM)

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
import os

from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler


class ApiFilebrowserHandler(BaseApiHandler):
    name = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "supported_methods": ["POST"],
            "call_method":       "fetch_directory_listing",
            "path_pattern":      r"/api/v1/filebrowser/list",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'file_browser_api'
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

    def fetch_directory_listing(self, *args, **kwargs):
        current_path = self.get_argument('current_path')
        list_type = self.get_argument('list_type') if self.get_body_arguments('list_type') else "all"

        path_data = self.fetch_path_data(current_path, list_type)

        self.write(json.dumps(path_data))

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
