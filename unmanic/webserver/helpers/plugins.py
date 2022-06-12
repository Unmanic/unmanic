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
import hashlib

from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.unplugins import PluginExecutor


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
    plugin_executor = PluginExecutor()
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
            "update_available": plugin_result.get('update_available'),
        }
        # Check if plugin is able to be configured
        has_config = False
        plugin_settings, plugin_settings_meta = plugin_executor.get_plugin_settings(plugin_result.get('plugin_id'))
        if plugin_settings:
            has_config = True
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
            'has_config':  has_config,
        }
        return_data["results"].append(item)

    # Return results
    return return_data


def get_plugin_types_with_flows():
    """
    Returns a list of all available plugin types

    :return:
    """
    return PluginsHandler.get_plugin_types_with_flows()


def get_enabled_plugin_flows_for_plugin_type(plugin_type, library_id):
    """
    Fetch all enabled plugin flows for a plugin type

    :param plugin_type:
    :param library_id:
    :return:
    """
    plugin_handler = PluginsHandler()
    return plugin_handler.get_enabled_plugin_flows_for_plugin_type(plugin_type, library_id)


def get_enabled_plugin_data_panels():
    """
    Returns a list of all enabled plugin data panels

    :return:
    """
    plugin_handler = PluginsHandler()
    return plugin_handler.get_enabled_plugin_modules_by_type('frontend.panel')


def exec_data_panels_plugin_runner(data, plugin_id):
    """
    Exec a frontend.panel plugin runner

    :param data:
    :param plugin_id:
    :return:
    """
    plugin_handler = PluginsHandler()
    return plugin_handler.exec_plugin_runner(data, plugin_id, 'frontend.panel')


def get_enabled_plugin_plugin_apis():
    """
    Returns a list of all enabled plugin APIs

    :return:
    """
    plugin_handler = PluginsHandler()
    return plugin_handler.get_enabled_plugin_modules_by_type('frontend.plugin_api')


def exec_plugin_api_plugin_runner(data, plugin_id):
    """
    Exec a frontend.plugin_api plugin runner

    :param data:
    :param plugin_id:
    :return:
    """
    plugin_handler = PluginsHandler()
    return plugin_handler.exec_plugin_runner(data, plugin_id, 'frontend.plugin_api')


def save_enabled_plugin_flows_for_plugin_type(plugin_type, library_id, plugin_flow):
    """
    Save a plugin flow given the plugin type and library ID

    :param plugin_type:
    :param library_id:
    :param plugin_flow:
    :return:
    """
    plugins = PluginsHandler()
    return plugins.set_plugin_flow(plugin_type, library_id, plugin_flow)


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


def get_plugin_settings(plugin_id: str, library_id=None):
    """
    Given a plugin installation ID, return a list of plugin settings for that plugin

    :param plugin_id:
    :param library_id:
    :return:
    """
    settings = []

    # Check plugin for settings
    plugin_executor = PluginExecutor()
    plugin_settings, plugin_settings_meta = plugin_executor.get_plugin_settings(plugin_id, library_id=library_id)
    if plugin_settings:
        for key in plugin_settings:
            form_input = {
                "key_id":         hashlib.md5(key.encode('utf8')).hexdigest(),
                "key":            key,
                "value":          plugin_settings.get(key),
                "input_type":     None,
                "label":          None,
                "description":    None,
                "tooltip":        None,
                "select_options": [],
                "slider_options": {},
                "display":        "visible",
                "sub_setting":    False,
            }

            plugin_setting_meta = plugin_settings_meta.get(key, {})

            # Set input type for form
            form_input['input_type'] = plugin_setting_meta.get('input_type', None)
            if not form_input['input_type']:
                form_input['input_type'] = "text"
                if isinstance(form_input['value'], bool):
                    form_input['input_type'] = "checkbox"

            # Handle unsupported input types (where they may be supported in future versions of Unmanic)
            supported_input_types = [
                "text",
                "textarea",
                "select",
                "checkbox",
                "slider",
                "browse_directory",
            ]
            if form_input['input_type'] not in supported_input_types:
                form_input['input_type'] = "text"

            # Set input display options
            form_input['display'] = plugin_setting_meta.get('display', 'visible')
            form_input['sub_setting'] = plugin_setting_meta.get('sub_setting', False)

            # Set input label text
            form_input['label'] = plugin_setting_meta.get('label', None)
            if not form_input['label']:
                form_input['label'] = key

            # Set input description text
            form_input['description'] = plugin_setting_meta.get('description', '')

            # Set input tooltip text
            form_input['tooltip'] = plugin_setting_meta.get('tooltip', '')

            # Set options if form input is select
            if form_input['input_type'] == 'select':
                form_input['select_options'] = plugin_setting_meta.get('select_options', [])
                if not form_input['select_options']:
                    # No options are given. Revert back to text input
                    form_input['input_type'] = 'text'

            # Set options if form input is slider
            if form_input['input_type'] == 'slider':
                slider_options = plugin_setting_meta.get('slider_options')
                if not slider_options:
                    # No options are given. Revert back to text input
                    form_input['input_type'] = 'text'
                else:
                    form_input['slider_options'] = {
                        'min':    slider_options.get('min', '0'),
                        'max':    slider_options.get('max', '1'),
                        'step':   slider_options.get('step', '1'),
                        'suffix': slider_options.get('suffix', ''),
                    }

            settings.append(form_input)
    return settings


def get_plugin_changelog(plugin_id):
    """
    Given a plugin installation ID, return a list of lines read from the plugin's changelog

    :param plugin_id:
    :return:
    """
    # Fetch plugin changelog
    plugin_executor = PluginExecutor()
    return plugin_executor.get_plugin_changelog(plugin_id)


def get_plugin_long_description(plugin_id):
    """
    Given a plugin installation ID, return a list of lines read from the plugin's changelog

    :param plugin_id:
    :return:
    """
    # Fetch plugin changelog
    plugin_executor = PluginExecutor()
    return plugin_executor.get_plugin_long_description(plugin_id)


def prepare_plugin_info_and_settings(plugin_id, prefer_local=True, library_id=None):
    """
    Returns a object of plugin metadata and current settings for the requested plugin_id

    :param prefer_local:
    :param plugin_id:
    :param library_id:
    :return:
    """
    plugins_handler = PluginsHandler()

    plugin_installed = True
    plugin_results = plugins_handler.get_plugin_list_filtered_and_sorted(plugin_id=plugin_id)

    if not plugin_results:
        # This plugin is not installed
        plugin_installed = False

    if not plugin_results or not prefer_local:
        # Try to fetch it from the repository
        plugin_list = plugins_handler.get_installable_plugins_list()
        for plugin in plugin_list:
            if plugin.get('plugin_id') == plugin_id:
                # Create changelog text from remote changelog text file
                plugin['changelog'] = plugins_handler.read_remote_changelog_file(plugin.get('changelog_url'))
                # Create list as the 'plugin_results' var above will also have returned a list if any results were found.
                plugin_results = [plugin]
                break

    # Iterate over plugins and append them to the plugin data
    plugin_data = {}
    for plugin_result in plugin_results:
        # Set plugin status
        plugin_status = {
            "installed":        plugin_result.get('installed', False),
            "update_available": plugin_result.get('update_available', False),
        }
        # Set params as required in template
        plugin_data = {
            'id':          plugin_result.get('id'),
            'plugin_id':   plugin_result.get('plugin_id'),
            'icon':        plugin_result.get('icon'),
            'name':        plugin_result.get('name'),
            'description': plugin_result.get('description'),
            'tags':        plugin_result.get('tags'),
            'author':      plugin_result.get('author'),
            'version':     plugin_result.get('version'),
            'changelog':   plugin_result.get('changelog', ''),
            'status':      plugin_status,
            'settings':    [],
        }
        if plugin_installed:
            plugin_data['settings'] = get_plugin_settings(plugin_result.get('plugin_id'), library_id=library_id)
            plugin_data['changelog'] = "".join(get_plugin_changelog(plugin_result.get('plugin_id')))
            plugin_data['description'] += "\n" + "".join(
                get_plugin_long_description(plugin_result.get('plugin_id')))
        break

    return plugin_data


def check_if_plugin_is_installed(plugin_id):
    """
    Returns true if the given plugin is installed

    :param plugin_id:
    :return:
    """
    plugins_handler = PluginsHandler()

    plugin_installed = True
    plugin_results = plugins_handler.get_plugin_list_filtered_and_sorted(plugin_id=plugin_id)

    if not plugin_results:
        # This plugin is not installed
        plugin_installed = False

    return plugin_installed


def update_plugin_settings(plugin_id, settings, library_id=None):
    """
    Updates the settings for the requested plugin_id

    :param plugin_id:
    :param settings:
    :param library_id:
    :return:
    """
    # Fetch plugin info (and settings if any)
    plugin_data = prepare_plugin_info_and_settings(plugin_id, library_id=library_id)

    # If no plugin data was found for the posted plugin table ID, then return a failure response
    if not plugin_data:
        return False

    # Loop over all plugin settings in order to find matches in the posted params
    settings_to_save = {}
    for s in settings:
        key = s.get('key')
        key_id = s.get('key_id')
        input_type = s.get('input_type')
        # Check if setting is in params
        value = s.get('value')
        # Check if value should be boolean
        if input_type == 'checkbox':
            if isinstance(value, str):
                value = True if value.lower() == 'true' else False
            elif isinstance(value, int):
                value = True if value > 0 else False
        # Add that to our dictionary of settings to save
        settings_to_save[key] = value

    # If we found settings that need to be saved, save them...
    if settings_to_save:
        plugin_executor = PluginExecutor()
        saved_all_settings = plugin_executor.save_plugin_settings(plugin_data.get('plugin_id'),
                                                                  settings_to_save,
                                                                  library_id=library_id)
        # If the save function was successful
        if saved_all_settings:
            # Update settings in plugin data that will be returned
            return True

    return False


def reset_plugin_settings(plugin_id, library_id=None):
    """
    Reset a plugin's settings back to defaults (or global config if a library ID is provided)

    :param plugin_id:
    :param library_id:
    :return:
    """
    # Fetch plugin info (and settings if any)
    plugin_data = prepare_plugin_info_and_settings(plugin_id, library_id=library_id)

    # If no plugin data was found for the posted plugin table ID, then return a failure response
    if not plugin_data:
        return False

    # Reset the plugin settings
    plugin_executor = PluginExecutor()
    return plugin_executor.reset_plugin_settings(plugin_data.get('plugin_id'), library_id=library_id)


def prepare_installable_plugins_list():
    """
    Return a list of plugins able to be installed.
    At the moment this does not employ any pagination. The lists are small enough
    that it can all be done frontend. However that may change in the future.

    :return:
    """
    plugins = PluginsHandler()
    # Fetch a list of plugin data cached locally
    return plugins.get_installable_plugins_list()


def install_plugin_by_id(plugin_id, repo_id=None):
    """
    Install a plugin given its Plugin ID

    :param plugin_id:
    :param repo_id:
    :return:
    """

    # Fetch a list of plugin data cached locally
    plugins = PluginsHandler()
    return plugins.install_plugin_by_id(plugin_id, repo_id)


def save_plugin_repos_list(repos_list):
    plugins = PluginsHandler()
    return plugins.set_plugin_repos(repos_list)


def prepare_plugin_repos_list():
    """
    Return a list of plugin repos available to download from

    :return:
    """
    return_repos = []

    plugins = PluginsHandler()
    # Fetch the data again from the database
    current_repos = plugins.get_plugin_repos()

    # Remove the default plugin repo from the list
    default_repo = plugins.get_default_repo()
    for repo in current_repos:
        if not repo.get("path").startswith(default_repo):
            return_repos.append(repo)

    # Append metadata from repo cache files
    for repo in return_repos:
        repo_path = repo.get('path')
        repo_id = plugins.get_plugin_repo_id(repo_path)
        repo_data = plugins.read_repo_data(repo_id)
        repo_metadata = repo_data.get('repo', {})
        repo['id'] = repo_metadata.get('id')
        repo['icon'] = repo_metadata.get('icon')
        repo['name'] = repo_metadata.get('name')

    return return_repos


def reload_plugin_repos_data():
    """
    Reloads all plugin repos data from the configured URL path

    :return:
    """
    plugins = PluginsHandler()
    return plugins.update_plugin_repos()
