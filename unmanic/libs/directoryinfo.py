#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.directoryinfo.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     02 Jul 2021, (10:59 AM)

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
from configparser import ConfigParser


class UnmanicDirectoryInfo(ConfigParser):
    """
    UnmanicDirectoryInfo

    Manages the reading and writing of the '.unmanic' files located in the directories
    parsed by Unmanic's library scanner or any plugins.

    """

    def __init__(self, directory):
        super().__init__(allow_no_value=True)
        self.path = os.path.join(directory, '.unmanic')
        self.read(self.path)

    def set(self, section, option, value=None):
        """
        Set an option.
        Extends ConfigParser.set by ensuring the section exists and creates it if not.

        :param section:
        :param option:
        :param value:
        :return:
        """
        if not self.has_section(section):
            self.add_section(section)
        super().set(section, option, value)

    def save(self):
        """
        Saves the info file.

        :return:
        """
        with open(self.path, 'w') as configfile:
            self.write(configfile)


if __name__ == '__main__':
    directory_info = UnmanicDirectoryInfo('/tmp/unmanic')
    directory_info.get('normalise_aac', 'key')
