#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.downloads.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     31 Oct 2021, (4:41 PM)

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
import threading
import time
import uuid

from tornado import iostream, web

from unmanic.libs.singleton import SingletonType


class DownloadsLinks(object, metaclass=SingletonType):
    _download_links = {}

    def __remove_expired(self):
        """
        Find and remove expired links

        :return:
        """
        time_now = time.time()
        keys = [t for t in self._download_links]
        lock = threading.RLock()
        with lock:
            for k in keys:
                if k in self._download_links:
                    if self._download_links[k].get('expires', 0) < time_now:
                        # Item has expired. Remove this item
                        del self._download_links[k]

    def generate_download_link(self, link_data):
        link_id = str(uuid.uuid4())
        lock = threading.RLock()
        with lock:
            # Expire in 1 min
            link_data['expires'] = (time.time() + 60)
            self._download_links[link_id] = link_data
        return link_id

    def get_download_link(self, link_id):
        # Find and remove expired links
        self.__remove_expired()
        return self._download_links.get(link_id, {})


class DownloadsHandler(web.RequestHandler):

    async def get(self, link_id):

        # Fetch link from
        download_links = DownloadsLinks()
        link_data = download_links.get_download_link(link_id)
        # Set file details
        abspath = link_data.get('abspath', '')
        basename = link_data.get('basename', '')
        # Return 404 on file not found
        if not os.path.exists(abspath):
            # Link ID must not be valid
            self.write_error(404)
            return

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename={}'.format(basename))

        # Serve file download in 1MB chunks
        with open(abspath, 'rb') as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                try:
                    self.write(data)
                    await self.flush()
                except iostream.StreamClosedError:
                    break
                finally:
                    del data
