#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.base_containers.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Sep 2019, (8:13 PM)

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


class Containers(object):
    """
    Containers

    Generic configuration and methods used across all Containers classes
    """

    def container_extension(self):
        """
        Return the container's extension string

        :return:
        """
        return self.extension

    def container_description(self):
        """
        Return the container's description string

        :return:
        """
        return self.description

    def container_supports_subtitles(self):
        """
        Check if this Container supports subtitles

        :return:
        """
        if hasattr(self, 'supports_subtitles'):
            if self.supports_subtitles:
                return True
        return False

    def supported_subtitles(self):
        """
        Check if this Container supports subtitles

        :return:
        """
        if self.container_supports_subtitles():
            return self.subtitle_codecs
        return []

    def unsupported_subtitles(self):
        """
        Check if this Container supports subtitles

        :return:
        """
        if hasattr(self, 'unsupports_codecs'):
            return self.unsubtitle_codecs
        # HDMV streams cannot be written by FFMPEG
        return ['hdmv_pgs_subtitle']
