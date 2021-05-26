#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugins_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     03 Mar 2021, (12:10 PM)

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
import json
import tornado.log

from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.libs.unplugins import PluginExecutor
from unmanic.webserver.api_v1.base_api_handler import BaseApiHandler


class ApiPluginsHandler(BaseApiHandler):
    name = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "supported_methods": ["POST"],
            "call_method":       "manage_installed_plugins_list",
            "path_pattern":      r"/api/v1/plugins/installed",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "get_installed_plugin_flow",
            "path_pattern":      r"/api/v1/plugins/flow",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "set_installed_plugin_flow",
            "path_pattern":      r"/api/v1/plugins/flow/save",
        },
        {
            "supported_methods": ["GET"],
            "call_method":       "get_plugin_list",
            "path_pattern":      r"/api/v1/plugins/list",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "get_plugin_info",
            "path_pattern":      r"/api/v1/plugins/info",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "update_plugin_settings",
            "path_pattern":      r"/api/v1/plugins/settings/update",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "install_plugin_by_id",
            "path_pattern":      r"/api/v1/plugins/install",
        },
        {
            "supported_methods": ["GET"],
            "call_method":       "get_repo_list",
            "path_pattern":      r"/api/v1/plugins/repos/list",
        },
        {
            "supported_methods": ["POST"],
            "call_method":       "update_repo_list",
            "path_pattern":      r"/api/v1/plugins/repos/update",
        },
        {
            "supported_methods": ["GET"],
            "call_method":       "update_repos",
            "path_pattern":      r"/api/v1/plugins/repos/fetch",
        },
    ]

    def initialize(self, **kwargs):
        self.name = 'plugins_api'
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    def set_default_headers(self):
        """Set the default response header to be JSON."""
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def get(self, path):
        self.action_route()

    def post(self, path):
        self.action_route()

    def manage_installed_plugins_list(self, *args, **kwargs):
        request_dict = json.loads(self.request.body)

        plugins = PluginsHandler()

        # Uninstall selected plugins
        if request_dict.get("customActionName") == "remove-selected-plugins":
            if not plugins.uninstall_plugins_by_db_table_id(request_dict.get("id")):
                self.write(json.dumps({"success": False}))
                return

        # Update selected plugins
        if request_dict.get("customActionName") == "update-selected-plugins":
            if not plugins.update_plugins_by_db_table_id(request_dict.get("id")):
                self.write(json.dumps({"success": False}))
                return

        # Enable selected plugins
        if request_dict.get("customActionName") == "enable-selected-plugins":
            if not plugins.enable_plugin_by_db_table_id(request_dict.get("id")):
                self.write(json.dumps({"success": False}))
                return

        # Disable selected plugins
        if request_dict.get("customActionName") == "disable-selected-plugins":
            if not plugins.disable_plugin_by_db_table_id(request_dict.get("id")):
                self.write(json.dumps({"success": False}))
                return

        # Return a list of plugins based on the request JSON body
        results = self.prepare_filtered_plugins(request_dict)
        self.write(json.dumps(results))

    def prepare_filtered_plugins(self, request_dict):
        """
        Returns a object of records filtered and sorted
        according to the provided request.

        :param request_dict:
        :return:
        """

        # Generate filters for query
        start = request_dict.get('start')
        length = request_dict.get('length')

        search = request_dict.get('search')
        search_value = search.get("value")

        # Force sort order always by ID desc
        order = [
            {
                "column": 'name',
                "dir":    'asc',
            }
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
            "draw":            request_dict.get('draw'),
            "recordsTotal":    records_total_count,
            "recordsFiltered": records_filtered_count,
            "successCount":    0,
            "failedCount":     0,
            "data":            []
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
                'selected':    False,
            }
            return_data["data"].append(item)

        # Return results
        return return_data

    def update_repo_list(self, *args, **kwargs):
        repos_list = self.get_argument('repos_list')

        if repos_list:
            repos_list = repos_list.splitlines()

        try:
            plugins = PluginsHandler()
            plugins.set_plugin_repos(repos_list)
        except Exception as e:
            tornado.log.app_log.exception("Exception in updating repo list - {}".format(str(e)), exc_info=True)

        self.get_repo_list()

    def get_repo_list(self):
        try:
            plugins = PluginsHandler()
            # Fetch the data again from the database
            current_repos = plugins.get_plugin_repos()

            # Remove the default plugin repo from the list
            return_repos = []
            default_repo = plugins.get_default_repo()
            for repo in current_repos:
                if not repo.get("path").startswith(default_repo):
                    return_repos.append(repo)

            # Return success
            self.write(json.dumps({"success": True, "repos": return_repos}))
        except Exception as e:
            tornado.log.app_log.exception("Exception in fetching the current repo list - {}".format(str(e)), exc_info=True)

            # Return failure
            self.write(json.dumps({"success": False}))

    def update_repos(self, *args, **kwargs):
        plugins = PluginsHandler()
        if plugins.update_plugin_repos():
            # Return success
            self.write(json.dumps({"success": True}))
        else:
            # Return failure
            self.write(json.dumps({"success": False}))

    def get_installed_plugin_flow(self, *args, **kwargs):
        plugin_type = self.get_argument('plugin_type')

        plugin_handler = PluginsHandler()
        plugin_modules = plugin_handler.get_plugin_modules_by_type(plugin_type)

        # Only return the data that we need
        return_plugin_flow = []
        for plugin_module in plugin_modules:
            return_plugin_flow.append(
                {
                    "plugin_id": plugin_module.get("plugin_id"),
                    "name":      plugin_module.get("name"),
                }
            )
        self.write(json.dumps({"success": True, "plugin_flow": return_plugin_flow}))

    def set_installed_plugin_flow(self, *args, **kwargs):
        request_dict = json.loads(self.request.body)

        plugin_type = request_dict.get('plugin_type')
        if not plugin_type:
            # Return failure
            self.write(json.dumps({"success": False, "error": "Missing plugin_type"}))
            return

        flow = request_dict.get('flow', [])

        plugins = PluginsHandler()
        success = plugins.set_plugin_flow(plugin_type, flow)

        if success:
            # Return success
            self.write(json.dumps({"success": True}))
        else:
            # Return failure
            self.write(json.dumps({"success": False}))

    def get_plugin_list(self, *args, **kwargs):
        plugins = PluginsHandler()
        # Fetch a list of plugin data cached locally
        plugin_list = plugins.get_installable_plugins_list()
        self.write(json.dumps({"success": True, "plugins": plugin_list}))

    def install_plugin_by_id(self, *args, **kwargs):
        plugin_id = self.get_argument('plugin_id')

        # Fetch a list of plugin data cached locally
        plugins = PluginsHandler()
        success = plugins.install_plugin_by_id(plugin_id)

        if success:
            # Return success
            self.write(json.dumps({"success": True}))
        else:
            # Return failure
            self.write(json.dumps({"success": False}))

    def __get_plugin_settings(self, plugin_id):
        """
        Given a plugin ID , return a list of plugin settings for that plugin

        :param plugin_id:
        :return:
        """
        settings = []

        # Check plugin for settings
        plugin_executor = PluginExecutor()
        plugin_settings, plugin_settings_meta = plugin_executor.get_plugin_settings(plugin_id)
        if plugin_settings:
            for key in plugin_settings:
                form_input = {
                    "key_id":         hashlib.md5(key.encode('utf8')).hexdigest(),
                    "key":            key,
                    "value":          plugin_settings.get(key),
                    "input_type":     None,
                    "label":          None,
                    "select_options": [],
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
                    "browse_directory",
                ]
                if form_input['input_type'] not in supported_input_types:
                    form_input['input_type'] = "text"

                # Set input label text
                form_input['label'] = plugin_setting_meta.get('label', None)
                if not form_input['label']:
                    form_input['label'] = key

                # Set options if form input is select
                if form_input['input_type'] == 'select':
                    form_input['select_options'] = plugin_setting_meta.get('select_options', [])
                    if not form_input['select_options']:
                        # No options are given. Revert back to text input
                        form_input['input_type'] = 'text'

                settings.append(form_input)
        return settings

    def __get_plugin_changelog(self, plugin_id):
        """
        Given a plugin ID , return a list of lines read from the plugin's changelog

        :param plugin_id:
        :return:
        """
        # Fetch plugin changelog
        plugin_executor = PluginExecutor()
        return plugin_executor.get_plugin_changelog(plugin_id)

    def __get_plugin_info_and_settings(self, plugin_id):
        plugins = PluginsHandler()

        plugin_installed = True
        plugin_results = plugins.get_plugin_list_filtered_and_sorted(plugin_id=plugin_id)
        if not plugin_results:
            # This plugin is not installed
            plugin_installed = False

            # Try to fetch it from the repository
            plugin_list = plugins.get_installable_plugins_list()
            for plugin in plugin_list:
                if plugin.get('id') == plugin_id:
                    # Create changelog text from remote changelog text file
                    plugin['changelog'] = plugins.read_remote_changelog_file(plugin.get('changelog_url'))
                    # Create list as the 'plugin_results' var above will also have returned a list if any results were found.
                    plugin_results = [plugin]
                    break

        # Iterate over plugins and append them to the plugin data
        plugin_data = {}
        for plugin_result in plugin_results:
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
                'settings':    [],
            }
            if plugin_installed:
                plugin_data['settings'] = self.__get_plugin_settings(plugin_result.get('plugin_id'))
                plugin_data['changelog'] = "".join(self.__get_plugin_changelog(plugin_result.get('plugin_id')))
            break

        return plugin_data

    def get_plugin_info(self, *args, **kwargs):
        # Fetch ID of plugin to get Info for
        plugin_id = self.get_argument('plugin_id')

        # Fetch plugin info (and settings if any)
        plugin_data = self.__get_plugin_info_and_settings(plugin_id)

        self.write(json.dumps({"success": True, "plugin_info": plugin_data}))

    def update_plugin_settings(self, *args, **kwargs):
        return_data = {
            "success": False
        }

        # Fetch ID of plugin to get Info for
        plugin_id = self.get_argument('plugin_id')

        # Fetch plugin info (and settings if any)
        plugin_data = self.__get_plugin_info_and_settings(plugin_id)

        # If no plugin data was found for the posted plugin table ID, then return a failure response
        if not plugin_data:
            return return_data

        # Create a dictionary of all posted arguments
        post_params = {}
        for k, v in self.request.arguments.items():
            post_params[k] = v[0].decode("utf-8")

        # Loop over all plugin settings in order to find matches in the posted params
        settings_to_save = {}
        for setting in plugin_data.get('settings'):
            key = setting.get('key')
            key_id = setting.get('key_id')
            input_type = setting.get('input_type')
            # Check if setting is in params
            if key_id in post_params:
                post_value = post_params.get(key_id, '')
                # Check if value should be boolean
                if input_type == 'checkbox':
                    post_value = True if post_value.lower() == 'true' else False
                # Add that to our dictionary of settings to save
                settings_to_save[key] = post_value

        # If we found settings in the post params that need to be saved, save them...
        result = False
        if settings_to_save:
            plugin_executor = PluginExecutor()
            saved_all_settings = plugin_executor.save_plugin_settings(plugin_data.get('plugin_id'), settings_to_save)
            # If the save function was successful
            if saved_all_settings:
                # Update settings in plugin data that will be returned
                plugin_data['settings'] = settings_to_save
                result = True

        self.write(json.dumps({"success": result, "plugin_info": plugin_data}))
