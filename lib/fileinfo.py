#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.fileinfo.py
 
    Written by:               Wagner Caixeta <wagner.caixeta@gmail.com>
    Date:                     23 Apr 2020, (15:25:00 PM)
 
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
  
           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""

import os
import re

"""

An object to represent file_info (Filebot pattern to keep filename history)

"""


class FileInfo(object):
    """
    FileInfo

    Attributes:
        path (string): Path of file_info
        entries (array of Entry): Filename history
    """

    def __init__(self, path):
        self.path = path
        self.entries = []

    def append(self, newname, originalname):
        self.entries.append(Entry(newname, self._find_oldest_name(originalname)))

    def load(self):
        if os.path.exists(self.path):
            try:
                f = open(self.path)
                self.entries = []
                for line in f:
                    m = re.search('(.+)="(.+)"', line)
                    if m.group(1) is not None and m.group(2) is not None:
                        self.entries.append(Entry(m.group(1), m.group(2)))
            except IOError:
                print("File not accessible")
            finally:
                f.close()

    def save(self):
        try:
            f = open(self.path, "w")
            for entry in self.entries:
                f.write('%s="%s"\n' % (entry.newname, entry.originalname))
        except IOError:
            print("File not accessible")
        finally:
            f.close()

    def _find_oldest_name(self, filename):
        for entry in self.entries:
            if entry.newname == filename:
                return entry.originalname
        return filename


"""

An object to keep a pair of newname and originalname

"""


class Entry(object):
    """
    Entry

    Attributes:
        newname (string): New name of file
        originalname (string): Old name of file
    """

    def __init__(self, newname, originalname):
        self.newname = newname
        self.originalname = originalname
