#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.filebrowser.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     13 Aug 2021, (2:44 PM)

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
import string

from unmanic.libs import common


def fetch_windows_drives():
    # Credit: https://stackoverflow.com/a/37761506
    return ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]


class DirectoryListing(object):
    """
    DirectoryListing

    Handle directory listing on the host running Unmanic
    """

    def __init__(self, list_type=None):
        self.list_type = 'all'
        if list_type:
            self.list_type = list_type

    def fetch_path_data(self, path):
        """
        Returns an object filled with data pertaining to a particular path

        :param path:
        :param list_type:
        :return:
        """
        directories = []
        files = []
        if self.list_type == "directories" or self.list_type == "all":
            directories = self.fetch_directories(path)
        if self.list_type == "files" or self.list_type == "all":
            files = self.fetch_files(path)
        path_data = {
            "current_path": path,
            "list_type":    self.list_type,
            "directories":  directories,
            "files":        files,
        }
        return path_data

    @staticmethod
    def fetch_directories(path):
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
            elif os.name == "nt":
                # Windows allow selection of drives as parent to root directory
                results.append(
                    {
                        "name":      "..",
                        "full_path": "",
                    }
                )
            try:
                for item in sorted(os.listdir(path)):
                    abspath = os.path.abspath(os.path.join(path, item))
                    if os.path.isdir(abspath):
                        results.append(
                            {
                                "name":      item,
                                "full_path": abspath,
                            }
                        )
            except PermissionError:
                pass
        elif os.name == "nt":
            # If path does not exist and OS is Windows, then list the available drives
            for drive in fetch_windows_drives():
                results.append(
                    {
                        "name":      drive,
                        "full_path": os.path.abspath(os.path.join(drive, os.sep)),
                    }
                )
        else:
            # Path doesn't exist!
            # Just return the root dir as the first directory option
            root_path = common.get_default_root_path()
            results.append(
                {
                    "name":      root_path,
                    "full_path": root_path,
                }
            )
        return results

    @staticmethod
    def fetch_files(path):
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
