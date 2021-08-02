#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugins.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     01 Aug 2021, (9:35 AM)

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
from unmanic.libs.plugins import PluginsHandler


def prepare_filtered_plugins(params):
    """
    Returns a object of records filtered and sorted
    according to the provided request.

    :param params:
    :return:
    """
    start = params.get('start', 0)
    length = params.get('length', 0)

    search_value = params.get('search_value', '')

    # Note that plugins can be ordered in multiple ways. So this must be a list
    order = [
        params.get('order', {
            "column": 'name',
            "dir":    'desc',
        })
    ]

    # Fetch Plugins
    plugins = PluginsHandler()
    # Get total count
    records_total_count = plugins.get_total_plugin_list_count()
    # Get quantity after filters (without pagination)
    records_filtered_count = plugins.get_plugin_list_filtered_and_sorted(order=order, start=0, length=0,
                                                                         search_value=search_value).count()
    # Get filtered/sorted results
    plugin_results = plugins.get_plugin_list_filtered_and_sorted(order=order, start=start, length=length,
                                                                 search_value=search_value)

    # Build return data
    return_data = {
        "recordsTotal":    records_total_count,
        "recordsFiltered": records_filtered_count,
        "results":         []
    }

    # Iterate over plugins and append them to the plugin data
    for plugin_result in plugin_results:
        # Set plugin status
        plugin_status = {
            "enabled":          plugin_result.get('enabled'),
            "update_available": plugin_result.get('update_available'),
        }
        # Set params as required in template
        item = {
            'id':          plugin_result.get('id'),
            'plugin_id':   plugin_result.get('plugin_id'),
            'icon':        plugin_result.get('icon'),
            'name':        plugin_result.get('name'),
            'description': plugin_result.get('description'),
            'tags':        plugin_result.get('tags'),
            'author':      plugin_result.get('author'),
            'version':     plugin_result.get('version'),
            'status':      plugin_status,
        }
        return_data["results"].append(item)

    # Return results
    return return_data


def enable_plugins(plugin_table_ids):
    """
    Enables a list of plugins

    :param plugin_table_ids:
    :return:
    """
    plugins_handler = PluginsHandler()
    return plugins_handler.enable_plugin_by_db_table_id(plugin_table_ids)


def disable_plugins(plugin_table_ids):
    """
    Disables a list of plugins

    :param plugin_table_ids:
    :return:
    """
    plugins_handler = PluginsHandler()
    return plugins_handler.disable_plugin_by_db_table_id(plugin_table_ids)


def remove_plugins(plugin_table_ids):
    """
    Removes/Uninstalls a list of plugins

    :param plugin_table_ids:
    :return:
    """
    plugins_handler = PluginsHandler()
    return plugins_handler.uninstall_plugins_by_db_table_id(plugin_table_ids)


def update_plugins(plugin_table_ids):
    """
    Removes/Uninstalls a list of plugins

    :param plugin_table_ids:
    :return:
    """
    plugins_handler = PluginsHandler()
    return plugins_handler.update_plugins_by_db_table_id(plugin_table_ids)
