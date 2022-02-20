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
from unmanic.libs.unmodels import EnabledPlugins, Libraries, Plugins, Tasks


class Library(object):
    """
    Library

    Contains all data pertaining to a library

    """

    def __init__(self, library_id: int):
        # Ensure library ID is not 0
        if library_id < 1:
            raise Exception("Library ID cannot be less than 1")
        self.model = Libraries.get_or_none(id=library_id)
        if not self.model:
            raise Exception("Unable to fetch library with ID {}".format(library_id))

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
                'path': default_library_path,
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
        # Ensure ID is removed from data for a create
        if 'id' in data:
            del data['id']
        new_library = Libraries.create(**data)
        return Library(new_library.id)

    def __remove_enabled_plugins(self):
        """
        Remove all enabled plugins

        :return:
        """
        EnabledPlugins.delete().where(EnabledPlugins.library_id == self.model.id).execute()

    def __remove_associated_tasks(self):
        """
        Remove all tasks associated with a library

        :return:
        """
        Tasks.delete().where(Tasks.library_id == self.model.id).execute()

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
        query = self.model.enabled_plugins.select(Plugins, EnabledPlugins.library_id)
        query = query.join(Plugins, join_type='LEFT OUTER JOIN', on=(EnabledPlugins.plugin_id == Plugins.id))
        query = query.order_by(Plugins.name)

        from unmanic.libs.unplugins import PluginExecutor
        plugin_executor = PluginExecutor()

        # Extract required data
        enabled_plugins = []
        for enabled_plugin in query.dicts():
            # Check if plugin is able to be configured
            has_config = False
            plugin_settings, plugin_settings_meta = plugin_executor.get_plugin_settings(enabled_plugin.get('plugin_id'))
            if plugin_settings:
                has_config = True
            # Add plugin to list of enabled plugins
            enabled_plugins.append({
                'library_id':  enabled_plugin.get('library_id'),
                'plugin_id':   enabled_plugin.get('plugin_id'),
                'name':        enabled_plugin.get('name'),
                'description': enabled_plugin.get('description'),
                'icon':        enabled_plugin.get('icon'),
                'has_config':  has_config,
            })

        return enabled_plugins

    def set_enabled_plugins(self, plugin_list: list):
        """
        Update the list of enabled plugins

        :param plugin_list:
        :return:
        """
        # Remove all enabled plugins
        self.__remove_enabled_plugins()

        # Add new repos
        data = []
        for plugin_info in plugin_list:
            plugin = Plugins.get(plugin_id=plugin_info.get('plugin_id'))
            if plugin:
                data.append({
                    "library_id":  self.model.id,
                    "plugin_id":   plugin,
                    "plugin_name": plugin.name,
                })
        EnabledPlugins.insert_many(data).execute()

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

    def delete(self):
        """
        Delete the current library

        :return:
        """
        # Ensure we can never delete library ID 1 (the default library)
        if self.get_id() == 1:
            raise Exception("Unable remove the default library")

        # Remove all enabled plugins
        self.__remove_enabled_plugins()

        # Delete all tasks with matching library_id
        self.__remove_associated_tasks()

        # Remove the library entry
        return self.model.delete_instance(recursive=True)
