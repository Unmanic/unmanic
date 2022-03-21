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
import os
import random

from unmanic.config import Config
from unmanic.libs import common
from unmanic.libs.unmodels import EnabledPlugins, Libraries, LibraryPluginFlow, Plugins, Tasks


def generate_random_library_name():
    names = [
        "Willes", "Here", "Helry", "Vyncent", "Burgwy", "Homas Yournet", "Roguy Eldys", "George Ewes", "Hearda",
        "Mathye Gedde", "Wynfre", "Gauwill", "Aldhert", "Ryany", "Reward", "Atwulf", "Amer", "Alten Yourner", "Reda", "Oled",
        "Anthohn Dene", "Rarder", "Artin Borne", "Eadwean", "Freyny Loray", "Breda", "Gauwalt Nynsell", "Lodwy", "Exam",
        "Alters Corby", "Wilhye", "Gery", "Raffin", "Ceolbehrt", "Jamath", "George Sone", "Geoffrey Nette", "Eadund", "Dunne",
        "Gilda", "Aered", "Lafa", "Eadulf", "Eanmaed", "Cyni", "Draffin", "Nichye", "Reder", "Aldwid", "Conbad", "Munda",
        "Willex", "Ichohn", "Orkold", "Gyleon", "Ealard", "Helmund", "Nother", "Bertio", "Phamund Erett", "Cuthre", "Aewald",
        "Aehehrt", "Folke", "Ales", "Chury Kypwe", "Liamund", "Rewalt Wyne", "Arryn", "Charlip", "Georguy", "Lare", "Aenward",
        "Eanwald", "Ashwid", "Britheard", "Cholas", "Eolhed", "Anwulf", "Eorcorht", "Piersym", "Godre", "Edward", "Dreder",
        "Geoffry", "Wyny", "Hardwy", "Witio", "Grewis", "Chilew", "Gare", "Arnwulf", "Masym Arren", "Iged", "Uwan", "Coenwy",
        "Saefa", "Thiles", "Cyne", "Exard", "Ichas Horne", "Rewilh Morley", "Edmur Ferry", "Wine", "Ered", "Lacio", "Elres",
        "Gaenbyrtf", "Stomund", "Riffin Maley", "Thiliam Save", "Walda", "Giles Drighte", "Robern Finchey", "Wulfa", "James",
        "Stiny Fane", "Driffin", "Andrers", "Beorhtio", "Balda", "Warder", "Bealdu", "Dene", "Andren", "Stephye", "Ealcar",
        "Richye Corby", "Ament Anes", "Tharry", "Germund", "Ralphye Payney"
    ]
    adjectives = [
        "awesome", "adorable", "abounding", "aspiring", "beloved", "blue", "blissful", "creamy", "cavernous", "content",
        "droopy", "excited", "enchanted", "enormous", "extroverted", "exciting", "gullible", "gaseous", "grumpy", "giant",
        "handsome", "hefty", "harmless", "happy", "hairy", "humdrum", "invincible", "illiterate", "inexperienced", "impolite",
        "illustrious", "impartial", "innocent""jovial", "juvenile", "joyful", "jumpy", "jagged", "joyous", "kooky", "large",
        "likeable", "mountainous", "momentous", "minty", "nocturnal", "nautical", "organic", "overcooked", "productive",
        "plush", "polished", "queasy", "quirky", "quintessential", "reminiscent", "remarkable", "ragged", "rowdy", "soggy",
        "sudden", "scandalous", "secretive", "spry", "squiggly", "smooth", "sulky", "scented", "spicy", "sticky", "slushy",
        "symptomatic", "tart", "turbulent", "tiresome", "typical", "xyloid", "xanthic", "zealous", "zany",
    ]
    return "{name}, the {adjective} library".format(name=random.choice(names), adjective=random.choice(adjectives))


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
        if not default_library_path:
            default_library_path = common.get_default_library_path()

        # Fetch all libraries from DB
        configured_libraries = Libraries.select()

        # Ensure that at least the default path was added.
        # If the libraries path is empty, then we should add the default path
        if not configured_libraries:
            default_library = {
                'id':     1,
                'name':   generate_random_library_name(),
                'path':   default_library_path,
                'locked': False,
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
                'id':     lib.id,
                'name':   lib.name,
                'path':   lib.path,
                'locked': lib.locked,
            })

        # Return the list of libraries
        return libraries

    @staticmethod
    def within_library_count_limits(frontend_messages=None):
        # Fetch level from session
        from unmanic.libs.session import Session
        s = Session()
        s.register_unmanic()
        if s.level > 1:
            return True

        # Fetch all enabled plugins
        library_count = Libraries.select().count()

        def add_frontend_message():
            # If the frontend messages queue was included in request, append a message
            if frontend_messages:
                frontend_messages.put(
                    {
                        'id':      'libraryEnabledLimits',
                        'type':    'error',
                        'code':    'libraryEnabledLimits',
                        'message': '',
                        'timeout': 0
                    }
                )

        # Ensure enabled plugins are within limits
        # Function was returned above if the user was logged in and able to use infinite
        if library_count > s.library_count:
            add_frontend_message()
            return False
        return True

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
        query = EnabledPlugins.delete()
        query = query.where(EnabledPlugins.library_id == self.model.id)
        return query.execute()

    def __trim_plugin_flow(self, plugin_ids: list):
        """
        Trim the plugin flow removing entries not in the given plugin ids list

        :param plugin_ids:
        :return:
        """
        query = LibraryPluginFlow.delete()
        query = query.where((LibraryPluginFlow.library_id == self.model.id) & (LibraryPluginFlow.plugin_id.not_in(plugin_ids)))
        return query.execute()

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

    def get_locked(self):
        return self.model.locked

    def set_locked(self, value):
        self.model.locked = value

    def get_enable_scanner(self):
        return self.model.enable_scanner

    def set_enable_scanner(self, value):
        self.model.enable_scanner = value

    def get_enable_inotify(self):
        return self.model.enable_inotify

    def set_enable_inotify(self, value):
        self.model.enable_inotify = value

    def get_enabled_plugins(self, include_settings=False):
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
            plugin_settings, plugin_settings_meta = plugin_executor.get_plugin_settings(enabled_plugin.get('plugin_id'),
                                                                                        library_id=self.model.id)
            if plugin_settings:
                has_config = True
            # Add plugin to list of enabled plugins
            item = {
                'plugin_id':   enabled_plugin.get('plugin_id'),
                'name':        enabled_plugin.get('name'),
                'description': enabled_plugin.get('description'),
                'icon':        enabled_plugin.get('icon'),
                'has_config':  has_config,
            }
            if include_settings:
                item['settings'] = plugin_settings
            enabled_plugins.append(item)

        return enabled_plugins

    def get_plugin_flow(self):
        """
        Fetch the plugin flow for a library

        :return:
        """
        plugin_flow = {}
        from unmanic.libs.plugins import PluginsHandler
        plugin_handler = PluginsHandler()
        from unmanic.libs.unplugins import PluginExecutor
        plugin_ex = PluginExecutor()
        for plugin_type in plugin_ex.get_all_plugin_types():
            # Ignore types without flows
            if not plugin_type.get('has_flow'):
                continue

            # Create list of plugins in this plugin type
            plugin_flow[plugin_type.get('id')] = []
            plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type(plugin_type.get('id'), library_id=self.model.id)
            for plugin_module in plugin_modules:
                plugin_flow[plugin_type.get('id')].append(
                    {
                        "plugin_id":   plugin_module.get("plugin_id"),
                        "name":        plugin_module.get("name", ""),
                        "author":      plugin_module.get("author", ""),
                        "description": plugin_module.get("description", ""),
                        "version":     plugin_module.get("version", ""),
                        "icon":        plugin_module.get("icon", ""),
                    }
                )

        return plugin_flow

    def __set_default_plugin_flow_priority(self, plugin_list):
        from unmanic.libs.unplugins import PluginExecutor
        plugin_executor = PluginExecutor()
        from unmanic.libs.plugins import PluginsHandler
        plugin_handler = PluginsHandler()

        # Fetch current items
        configured_plugin_ids = []
        query = LibraryPluginFlow.select().where(LibraryPluginFlow.library_id == self.model.id)
        for flow_item in query:
            configured_plugin_ids.append(flow_item.plugin_id.plugin_id)

        for plugin in plugin_list:
            # Ignore already configured plugins
            if plugin.get('plugin_id') in configured_plugin_ids:
                continue
            plugin_info = plugin_handler.get_plugin_info(plugin.get('plugin_id'))
            plugin_priorities = plugin_info.get('priorities')
            if plugin_priorities:
                # Fetch the plugin info back from the DB
                plugin_info = Plugins.select().where(Plugins.plugin_id == plugin.get("plugin_id")).first()
                # Fetch all plugin types in this plugin
                plugin_types_in_plugin = plugin_executor.get_all_plugin_types_in_plugin(plugin.get("plugin_id"))
                # Loop over the plugin types in this plugin
                for plugin_type in plugin_types_in_plugin:
                    # get the plugin runner function name for this runner
                    plugin_type_meta = plugin_executor.get_plugin_type_meta(plugin_type)
                    runner_string = plugin_type_meta.plugin_runner()
                    if plugin_priorities.get(runner_string) and int(plugin_priorities.get(runner_string, 0)) > 0:
                        # If the runner has a priority set and that value is greater than 0 (default that wont set anything),
                        # Save the priority
                        PluginsHandler.set_plugin_flow_position_for_single_plugin(
                            plugin_info,
                            plugin_type,
                            self.model.id,
                            plugin_priorities.get(runner_string)
                        )

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
        plugin_ids = []
        for plugin_info in plugin_list:
            plugin = Plugins.get(plugin_id=plugin_info.get('plugin_id'))
            plugin_ids.append(plugin.id)
            if plugin:
                data.append({
                    "library_id":  self.model.id,
                    "plugin_id":   plugin,
                    "plugin_name": plugin.name,
                })

        # Delete all plugin flows for plugins not to be enabled for this library
        self.__trim_plugin_flow(plugin_ids)

        # Insert plugins
        EnabledPlugins.insert_many(data).execute()

        # Add default flow for newly added plugins
        self.__set_default_plugin_flow_priority(plugin_list)

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
            raise Exception("Unable to remove the default library")

        # Ensure we are not trying to delete a locked library
        if self.get_locked():
            raise Exception("Unable to remove a locked library")

        # Remove all enabled plugins
        self.__remove_enabled_plugins()

        # Remove all plugin flows
        self.__trim_plugin_flow([])

        # Delete all tasks with matching library_id
        self.__remove_associated_tasks()

        # Remove the library entry
        return self.model.delete_instance(recursive=True)
