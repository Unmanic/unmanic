#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.base_codecs.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     20 Sep 2019, (5:38 PM)
 
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


class Codecs(object):
    """
    Codecs

    Generic configuration and methods used across all codec classes
    """
    name = ''
    encoders = []
    default_encoder = ''
    codec_long_name = ''

    def codec_name(self):
        """
        Return the codec name string

        :return:
        """
        return self.name

    def codec_encoders(self):
        """
        Return the codec encoders list

        :return:
        """
        return self.encoders

    def codec_default_encoder(self):
        """
        Return the codec encoders list

        :return:
        """
        return self.default_encoder

    def codec_description(self):
        """
        Return the codec description string

        :return:
        """
        return self.codec_long_name
