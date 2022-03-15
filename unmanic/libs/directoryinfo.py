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
import json
import os
import configparser


class UnmanicDirectoryInfoException(Exception):
    def __init__(self, message, path):
        errmsg = '%s: file %s' % (message, path)
        Exception.__init__(self, errmsg)
        self.message = message
        self.path = path

    def __repr__(self):
        return self.message

    __str__ = __repr__


class UnmanicDirectoryInfo:
    """
    UnmanicDirectoryInfo

    Manages the reading and writing of the '.unmanic' files located in the directories
    parsed by Unmanic's library scanner or any plugins.

    Legacy support:
        On read, if the config is an INI file, uses ConfigParser.get to fetch information
        and convert it to JSON.
        INI was initially used in order to be a simple syntax for manually editing.
        However, INI is not ideal for managing file names and paths with special characters

    """

    def __init__(self, directory):
        self.path = os.path.join(directory, '.unmanic')
        self.json_data = None
        self.config_parser = None
        # If the path does not exist, do not try to read it
        if not os.path.exists(self.path):
            self.json_data = {}
            return
        # First read JSON data
        try:
            with open(self.path) as infile:
                self.json_data = json.load(infile)
            # Migrate JSON to latest formatting
            self.__migrate_json_formatting()
        except json.decoder.JSONDecodeError:
            pass
        # If we were unable to import the JSON data, attempt to read as INI
        if self.json_data is None:
            try:
                self.config_parser = configparser.ConfigParser(allow_no_value=True)
                self.config_parser.read(self.path)
                # Migrate file to JSON
                self.__migrate_to_json()
            except configparser.MissingSectionHeaderError:
                pass
            except configparser.NoSectionError:
                pass
            except configparser.NoOptionError:
                pass
        # If we still do not have JSON data at this point, something has gone wrong
        if self.json_data is None:
            raise UnmanicDirectoryInfoException("Failed to read directory info", self.path)

    def __migrate_to_json(self):
        """
        Migrate data from INI to JSON

        :return:
        """
        sections = self.config_parser.sections()
        json_data = {}
        for section in sections:
            section_data = {}
            for key in self.config_parser[section]:
                section_data[key.lower()] = self.config_parser.get(section, key)
            json_data[section] = section_data
        self.json_data = json_data

    def __migrate_json_formatting(self):
        """
        Migrate JSON to latest format

        Migration 1:
            As Unmanic may be used on platforms that view files as case-insensitive,
            we should ensure that all keys are also stored this way.

        :return:
        """
        # Ensure all keys are lower case
        sections = [s for s in self.json_data]
        for section in sections:
            # Sections remain case sensitive, but keys must be lowercase
            keys = [k for k in self.json_data[section]]
            for key in keys:
                if key != key.lower():
                    self.json_data[section][key.lower()] = self.json_data[section][key]
                    del self.json_data[section][key]

    def set(self, section, option, value=None):
        """
        Set an option.

        :param section:
        :param option:
        :param value:
        :return:
        """
        # Ensure keys are always lower-case
        option = option.lower()
        if self.json_data is not None:
            if not self.json_data.get(section):
                self.json_data[section] = {}
            self.json_data[section][option] = value
            return
        elif self.config_parser:
            if not self.config_parser.has_section(section):
                self.config_parser.add_section(section)
            self.config_parser.set(section, option, value)
            return
        raise UnmanicDirectoryInfoException("Failed to set section '{}' option '{}' value '{}'".format(section, option, value),
                                            self.path)

    def get(self, section, option):
        """
        Get an option

        :param section:
        :param option:
        :return:
        """
        option = option.lower()
        if self.json_data is not None:
            return self.json_data.get(section, {}).get(option)
        elif self.config_parser:
            return self.config_parser.get(section, option)
        raise UnmanicDirectoryInfoException("Failed to get section '{}' option '{}'".format(section, option), self.path)

    def save(self):
        """
        Saves the data to file.

        :return:
        """
        if self.json_data is not None:
            with open(self.path, 'w') as outfile:
                json.dump(self.json_data, outfile, indent=2)
            return
        elif self.config_parser:
            with open(self.path, 'w') as outfile:
                self.config_parser.write(outfile)
            return
        raise UnmanicDirectoryInfoException("Failed to save directory info", self.path)


if __name__ == '__main__':
    directory_info = UnmanicDirectoryInfo('/tmp/unmanic')
    directory_info.set('test_section', 'key', 'value')
    directory_info.save()
    print(directory_info.get('test_section', 'key'))
    directory_info.set('"section with double quotes"', '"key with double quotes"', '"value with double quotes"')
    directory_info.save()
    print(directory_info.get('"section with double quotes"', '"key with double quotes"'))
