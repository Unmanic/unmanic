#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.library.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Feb 2022, (12:11 PM)

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
from unmanic.config import Config
from unmanic.libs.unmodels import EnabledPlugins, Libraries, Plugins


class Library(object):
    """
    Library

    Contains all data pertaining to a library

    """

    def __init__(self, library_id: int):
        self.model = Libraries.get(id=library_id)

    @staticmethod
    def get_all_libraries():
        """
        Return a list of all libraries

        :return:
        """
        # Fetch default library path from
        from unmanic.config import Config
        default_library_path = Config().get_library_path()

        # Fetch all libraries from DB
        configured_libraries = Libraries.select()

        # Ensure that at least the default path was added.
        # If the libraries path is empty, then we should add the default path
        if not configured_libraries:
            default_library = {
                'id':   1,
                'name': 'Default',
                'path': default_library_path
            }
            Libraries.create(**default_library)
            return [default_library]

        # Loop over results
        libraries = []
        for lib in configured_libraries:
            # Always update the default library path
            if lib.id == 1 and lib.path != default_library_path:
                lib.path = default_library_path
                lib.save()
            libraries.append({
                'id':   lib.id,
                'name': lib.name,
                'path': lib.path,
            })

        # Return the list of libraries
        return libraries

    @staticmethod
    def create(data: dict):
        """
        Create a new library

        :param data:
        :return:
        """
        new_library = Libraries.create(**data)
        return Library(new_library.id)

    def get_id(self):
        return self.model.id

    def get_name(self):
        return self.model.name

    def set_name(self, value):
        self.model.name = value

    def get_path(self):
        return self.model.path

    def set_path(self, value):
        self.model.path = value

    def get_enable_scanner(self):
        return self.model.enable_scanner

    def set_enable_scanner(self, value):
        self.model.enable_scanner = value

    def get_enable_inotify(self):
        return self.model.enable_inotify

    def set_enable_inotify(self, value):
        self.model.enable_inotify = value

    def get_enabled_plugins(self):
        """
        Get all enabled plugins for this library

        :return:
        """
        # Fetch enabled plugins for this library
        enabled_plugins_query = EnabledPlugins.select().join(Plugins)
        enabled_plugins_query = enabled_plugins_query.where(EnabledPlugins.library_table_id == self.model.id)
        enabled_plugins_query = enabled_plugins_query.order_by(Plugins.name)

        # Extract required data
        enabled_plugins = []
        for enabled_plugin in enabled_plugins_query:
            enabled_plugins.append({
                'library_id':  enabled_plugin.library_table_id.id,
                'plugin_id':   enabled_plugin.plugin_table_id.plugin_id,
                'name':        enabled_plugin.plugin_table_id.name,
                'description': enabled_plugin.plugin_table_id.description,
                'icon':        enabled_plugin.plugin_table_id.icon,
            })

        return enabled_plugins

    def get_plugin_flow(self):
        """
        Get the plugin flow config for this library

        :return:
        """
        # TODO: Fetch plugin flow for this library
        pass

    def save(self):
        """
        Save the data for this library

        :return:
        """
        # Save changes made to model
        self.model.save()

        # If this is the default library path, save to config.library_path object also
        if self.get_id() == 1:
            config = Config()
            config.set_config_item('library_path', self.get_path())
