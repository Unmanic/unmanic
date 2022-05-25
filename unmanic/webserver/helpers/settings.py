#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.settings.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Feb 2022, (5:22 PM)

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
from unmanic import config
from unmanic.libs.library import Library
from unmanic.libs.unplugins import PluginExecutor
from unmanic.webserver.helpers import plugins


def save_library_config(library_id, library_config=None, plugin_config=None):
    """
    Save a complete library configuration

    :param library_id:
    :param library_config:
    :param plugin_config:
    :return:
    """
    # Parse library config
    if plugin_config is None:
        plugin_config = {}
    if library_config is None:
        library_config = {}

    # Check if this save requires a new library entry
    if int(library_id) > 0:
        # Fetch existing library by ID
        new_library = False
        library = Library(library_id)
    else:
        # Create a new library with required data
        new_library = True
        library = Library.create({
            'name': library_config.get('name'),
            'path': library_config.get('path'),
        })
        library_id = library.get_id()

    # Update library config (if the data was given)
    if library_config:
        library.set_name(library_config.get('name', library.get_name()))
        library.set_path(library_config.get('path', library.get_path()))
        library.set_locked(library_config.get('locked', library.get_locked()))
        library.set_enable_remote_only(library_config.get('enable_remote_only', library.get_enable_remote_only()))
        library.set_enable_scanner(library_config.get('enable_scanner', library.get_enable_scanner()))
        library.set_enable_inotify(library_config.get('enable_inotify', library.get_enable_inotify()))
        library.set_priority_score(library_config.get('priority_score', library.get_priority_score()))
        library.set_tags(library_config.get('tags', library.get_tags()))

    # Update enabled plugins (if the data was given)
    enabled_plugins = plugin_config.get('enabled_plugins')
    if enabled_plugins is not None:
        # Ensure plugins are installed (install them if they are not)
        repo_refreshed = False
        for ep in enabled_plugins:
            if not plugins.check_if_plugin_is_installed(ep.get('plugin_id')):
                # Trigger plugin repo refresh if this is the first install
                if not repo_refreshed:
                    plugins.reload_plugin_repos_data()
                    repo_refreshed = True
                # Install the plugin
                if not plugins.install_plugin_by_id(ep.get('plugin_id')):
                    if new_library:
                        library.delete()
                    raise Exception("Failed to install plugin by plugin ID '{}'".format(ep.get('plugin_id')))
        # Enable the plugins against this library
        library.set_enabled_plugins(enabled_plugins)
        # Import settings
        plugin_executor = PluginExecutor()
        for ep in enabled_plugins:
            if ep.get('has_config'):
                plugin_executor.save_plugin_settings(ep.get('plugin_id'), ep.get('settings', {}), library_id=library_id)

    # Update plugin flow (if the data was given)
    plugin_flow = plugin_config.get('plugin_flow')
    if plugin_flow is not None:
        for plugin_type in plugins.get_plugin_types_with_flows():
            flow = []
            for plugin_id in plugin_flow.get(plugin_type, []):
                flow.append({'plugin_id': plugin_id})
            plugins.save_enabled_plugin_flows_for_plugin_type(plugin_type, library_id, flow)

    # Save config
    return library.save()


def save_worker_group_config(data):
    """
    Save a complete worker group configuration

    NOTE: 
        If the worker group is updated in the future with new options, then be sure to apply the save logic to 
        both the create and update methods

    :param data:
    :return:
    """
    from unmanic.libs.worker_group import WorkerGroup

    # Create new worker group
    if not data.get('id'):
        WorkerGroup.create(data)
        return

    # Update existing worker group
    # NOTE: If this is updated in the future with new options, then be sure to apply the same save logic to the create method
    worker_group = WorkerGroup(data.get('id'))
    # Store locked status
    worker_group.set_locked(data.get('locked', worker_group.get_locked()))
    # Store name
    worker_group.set_name(data.get('name', worker_group.get_name()))
    # Store the number of workers
    worker_group.set_number_of_workers(data.get('number_of_workers', worker_group.get_number_of_workers()))

    # Set lists
    worker_group.set_tags(data.get('tags', worker_group.get_tags()))
    worker_group.set_worker_event_schedules(data.get('worker_event_schedules', worker_group.get_worker_event_schedules()))

    # Save config
    return worker_group.save()
