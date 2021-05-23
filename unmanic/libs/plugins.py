#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugins.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     03 Mar 2021, (3:52 PM)

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
import base64
import hashlib
import json
import os
import shutil
import zipfile
from operator import attrgetter

import requests

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.session import Session
from unmanic.libs.singleton import SingletonType
from unmanic.libs.unmodels import db, Plugins, PluginRepos
from unmanic.libs.unmodels.pluginflow import PluginFlow
from unmanic.libs.unplugins import plugin_types, PluginExecutor


class PluginsHandler(object, metaclass=SingletonType):
    # Set the default repo to main repo
    default_repo = 'https://unmanic.app/api/v1/unmanic-plugin-repo/uuid'

    def __init__(self, *args, **kwargs):
        self.settings = config.CONFIG()
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    @staticmethod
    def get_plugin_repo_id(repo_path):
        return int(hashlib.md5(repo_path.encode('utf8')).hexdigest(), 16)

    def get_repo_cache_file(self, repo_id):
        plugins_directory = self.settings.get_plugins_path()
        if not os.path.exists(plugins_directory):
            os.makedirs(plugins_directory)
        return os.path.join(plugins_directory, "repo-{}.json".format(repo_id))

    def get_plugin_path(self, plugin_id):
        plugin_directory = os.path.join(self.settings.get_plugins_path(), plugin_id)
        if not os.path.exists(plugin_directory):
            os.makedirs(plugin_directory)
        return plugin_directory

    def get_plugin_download_cache_path(self, plugin_id, plugin_version):
        plugin_directory = self.settings.get_plugins_path()
        return os.path.join(plugin_directory, "{}-{}.zip".format(plugin_id, plugin_version))

    def get_default_repo(self):
        return self.default_repo

    def get_plugin_repos(self):
        """
        Returns a list of plugin repos

        :return:
        """
        session = Session()
        uuid = session.get_installation_uuid()
        default_repo = self.get_default_repo()
        repo_list = [
            {
                "path": "{}/{}".format(default_repo, uuid)
            }
        ]

        repos = PluginRepos.select().order_by(PluginRepos.id.asc())
        for repo in repos:
            repo_dict = repo.model_to_dict()
            if repo_dict.get('path') == "{}/{}".format(default_repo, uuid):
                continue
            repo_list.append(repo_dict)

        return repo_list

    @staticmethod
    def set_plugin_repos(repo_list):
        # Remove all existing repos
        PluginRepos.delete().execute()

        # Add new repos
        data = []
        for repo_path in repo_list:
            data.append({"path": repo_path})

        PluginRepos.insert_many(data).execute()

    def update_plugin_repos(self):
        """
        Updates the local cached data of plugin repos

        :return:
        """
        plugins_directory = self.settings.get_plugins_path()
        if not os.path.exists(plugins_directory):
            os.makedirs(plugins_directory)
        success = True
        current_repos_list = self.get_plugin_repos()
        for repo in current_repos_list:
            repo_path = repo.get('path')
            repo_id = self.get_plugin_repo_id(repo_path)

            # If success, dump JSON to file
            # Else, log error and catch any exceptions
            pass
            # Try to fetch URL
            try:
                # Fetch remote JSON file
                session = Session()
                uuid = session.get_installation_uuid()
                post_data = {
                    "uuid":     uuid,
                    "repo_url": repo_path
                }
                repo_data = session.api_post(1, 'unmanic-plugin-repo/uuid/{}'.format(uuid), post_data)

                # Load JSON to python object
                # repo_data = json.loads(repo_json)
                self._log("Repo info {}.".format(repo_path), repo_data, level="info")

                # Dumb object to local JSON file
                repo_cache = self.get_repo_cache_file(repo_id)
                self._log("Repo cache file '{}'.".format(repo_cache), level="info")
                with open(repo_cache, 'w') as f:
                    json.dump(repo_data, f, indent=4)

            except Exception as e:
                success = False
                self._log("Exception while updating repo {}.".format(repo_path), str(e), level="exception")
        return success

    def read_repo_data(self, repo_id):
        repo_cache = self.get_repo_cache_file(repo_id)
        if os.path.exists(repo_cache):
            with open(repo_cache) as f:
                repo_data = json.load(f)
            return repo_data
        return {}

    def get_plugins_in_repo_data(self, repo_data):
        return_list = []
        if 'repo' in repo_data and 'plugins' in repo_data:
            # Get URLs for plugin downloads
            repo_meta = repo_data.get("repo")
            repo_data_directory = repo_meta.get("repo_data_directory")
            if not repo_data_directory:
                return return_list
            repo_data_directory = repo_data_directory.rstrip('/')
            # if not repo_data_directory.endswith("/"):
            #     repo_data_directory = repo_data_directory + "/"

            # Loop over
            for plugin in repo_data.get("plugins", []):
                plugin["url"] = "{0}/{1}/{1}-{2}.zip".format(repo_data_directory, plugin.get('id'), plugin.get('version'))
                plugin["changelog_url"] = "{0}/{1}/changelog.txt".format(repo_data_directory, plugin.get('id'))

                # Check if plugin is already installed:
                plugin["installed"] = False
                plugin_directory = os.path.join(self.settings.get_plugins_path(), plugin.get('id'))
                if os.path.exists(plugin_directory):
                    # Read plugin info.json
                    info_file = os.path.join(plugin_directory, 'info.json')
                    with open(info_file) as json_file:
                        plugin_info = json.load(json_file)
                    local_version = plugin_info.get('version')
                    # Parse the currently installed version number and check if it matches
                    remote_version = plugin.get('version')
                    if local_version == remote_version:
                        plugin["installed"] = True
                    else:
                        # There is an update available
                        self.flag_plugin_for_update_by_id(plugin.get("id"))

                # If no icon is provide, set a default
                if not plugin["icon"]:
                    plugin["icon"] = "/assets/global/img/plugin-icon-default.svg"
                return_list.append(plugin)
        return return_list

    def get_installable_plugins_list(self):
        return_list = []

        # First fetch a list of available repos
        current_repos_list = self.get_plugin_repos()
        for repo in current_repos_list:
            repo_path = repo.get('path')
            repo_id = self.get_plugin_repo_id(repo_path)
            repo_data = self.read_repo_data(repo_id)
            plugins_in_repo = self.get_plugins_in_repo_data(repo_data)
            return_list = return_list + plugins_in_repo

        return return_list

    def read_remote_changelog_file(self, changelog_url):
        r = requests.get(changelog_url, timeout=1)
        if r.status_code == 200:
            return r.text
        return ''

    def notify_site_of_plugin_install(self, plugin):
        """
        Notify the Unmanic.app site of the install.
        This is used for metric stats so that we can get a count of plugin downloads.

        :param plugin:
        :return:
        """
        # Post
        session = Session()
        uuid = session.get_installation_uuid()
        post_data = {
            "uuid":      uuid,
            "plugin_id": plugin.get("id"),
            "author":    plugin.get("author"),
            "version":   plugin.get("version"),
        }
        try:
            repo_data = session.api_post(1, 'unmanic-plugin/install', post_data)
            if not repo_data.get('success'):
                session.register_unmanic(session.get_installation_uuid())
        except Exception as e:
            self._log("Exception while logging plugin install.", str(e), level="debug")
            return False

    def install_plugin_by_id(self, plugin_id):
        """
        Find the patching plugin info for the given plugin ID.
        Download the plugin if it is found and return the result.
        If it is not found, return False.

        :param plugin_id:
        :return:
        """
        plugin_list = self.get_installable_plugins_list()
        for plugin in plugin_list:
            if plugin.get('id') == plugin_id:
                success = self.install_plugin(plugin)

                if success:
                    try:
                        plugin_directory = self.get_plugin_path(plugin.get("id"))
                        return self.write_plugin_data_to_db(plugin, plugin_directory)
                    except Exception as e:
                        self._log("Exception while saving plugin info for '{}' to DB.".format(plugin), str(e),
                                  level="exception")

        return False

    def install_plugin(self, plugin):
        """
        Download and install a given plugin

        :param plugin:
        :return:
        """
        self._log("Installing plugin '{}'".format(plugin.get("name")), level='debug')
        # Try to fetch URL
        try:
            # Fetch remote zip file
            destination = self.get_plugin_download_cache_path(plugin.get("id"), plugin.get("version"))
            self._log("Downloading plugin '{}' to '{}'".format(plugin.get("url"), destination), level='debug')
            with requests.get(plugin.get("url"), stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                with open(destination, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=128):
                        f.write(chunk)

            # Extract zip file contents
            plugin_directory = self.get_plugin_path(plugin.get("id"))
            self._log("Extracting plugin to '{}'".format(plugin_directory), level='debug')
            with zipfile.ZipFile(destination, "r") as zip_ref:
                zip_ref.extractall(plugin_directory)

            # Cleanup zip file
            if os.path.isfile(destination):
                os.remove(destination)

            self.notify_site_of_plugin_install(plugin)

            return True

        except Exception as e:
            success = False
            self._log("Exception while installing plugin '{}'.".format(plugin), str(e), level="exception")

        return False

    @staticmethod
    def write_plugin_data_to_db(plugin, plugin_directory):
        # Add installed plugin to database
        plugin_data = {
            Plugins.plugin_id:        plugin.get("id"),
            Plugins.name:             plugin.get("name"),
            Plugins.author:           plugin.get("author"),
            Plugins.version:          plugin.get("version"),
            Plugins.tags:             plugin.get("tags"),
            Plugins.description:      plugin.get("description"),
            Plugins.icon:             plugin.get("icon"),
            Plugins.local_path:       plugin_directory,
            Plugins.update_available: False,
        }
        plugin_entry = Plugins.get_or_none(plugin_id=plugin.get("id"))
        if plugin_entry is not None:
            # Update the existing entry
            update_query = (Plugins
                            .update(plugin_data)
                            .where(Plugins.plugin_id == plugin.get("id")))
            update_query.execute()
        else:
            # Insert a new entry
            # Plugins are disable when first installed. This will help to prevent issues with broken plugins
            plugin_data[Plugins.enabled] = False
            Plugins.insert(plugin_data).execute()

        return True

    def get_total_plugin_list_count(self):
        task_query = Plugins.select().order_by(Plugins.id.desc())
        return task_query.count()

    def get_plugin_list_filtered_and_sorted(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                            enabled=None, plugin_id=None, plugin_type=None):
        try:
            query = (Plugins.select())

            if plugin_type:
                join_condition = (
                    (PluginFlow.plugin_id == Plugins.id) &
                    (PluginFlow.plugin_type == plugin_type))
                query = query.join(PluginFlow, join_type='LEFT OUTER JOIN', on=join_condition)

            if id_list:
                query = query.where(Plugins.id.in_(id_list))

            if search_value:
                query = query.where(
                    (Plugins.name.contains(search_value)) |
                    (Plugins.author.contains(search_value)) |
                    (Plugins.tags.contains(search_value))
                )

            if plugin_id is not None:
                query = query.where(Plugins.plugin_id.in_([plugin_id]))

            if enabled is not None:
                query = query.where(Plugins.enabled == enabled)

            # Get order by
            if order:
                for o in order:
                    if o.get("model"):
                        model = o.get("model")
                    else:
                        model = Plugins
                    if o.get("dir") == "asc":
                        order_by = attrgetter(o.get("column"))(model).asc()
                    else:
                        order_by = attrgetter(o.get("column"))(model).desc()

                    query = query.order_by_extend(order_by)

            if length:
                query = query.limit(length).offset(start)

            return query.dicts()

        except Plugins.DoesNotExist:
            # No plugin entries exist yet
            self._log("No plugins exist yet.", level="warning")

    def enable_plugin_by_db_table_id(self, plugin_table_ids):
        self._log("Enable plugins '{}'".format(plugin_table_ids), level='debug')

        # Refresh session
        s = Session()
        s.register_unmanic(s.get_installation_uuid())

        # Update enabled plugins
        if not self.ensure_session_level_for_plugins(s.level):
            return False

        # Enable the matching entries in the table
        Plugins.update(enabled=True).where(Plugins.id.in_(plugin_table_ids)).execute()

        # Fetch records
        records_by_id = self.get_plugin_list_filtered_and_sorted(id_list=plugin_table_ids)

        # Ensure they are now enabled
        for record in records_by_id:
            if record.get('enabled'):
                continue
            self._log("Failed to enable plugin '{}'".format(record.get('plugin_id')), level='debug')
            return False

        return True

    def disable_plugin_by_db_table_id(self, plugin_table_ids):
        self._log("Disable plugins '{}'".format(plugin_table_ids), level='debug')
        # Disable the matching entries in the table
        Plugins.update(enabled=False).where(Plugins.id.in_(plugin_table_ids)).execute()

        # Fetch records
        records_by_id = self.get_plugin_list_filtered_and_sorted(id_list=plugin_table_ids)

        # Ensure they are now disabled
        for record in records_by_id:
            if not record.get('enabled'):
                continue
            self._log("Failed to disable plugin '{}'".format(record.get('plugin_id')), level='debug')
            return False

        return True

    def flag_plugin_for_update_by_id(self, plugin_id):
        self._log("Flagging update available for installed plugin '{}'".format(plugin_id), level='debug')
        # Disable the matching entries in the table
        Plugins.update(update_available=True).where(Plugins.plugin_id == plugin_id).execute()

        # Fetch records
        records = self.get_plugin_list_filtered_and_sorted(plugin_id=plugin_id)

        # Ensure they are now disabled
        for record in records:
            if record.get('update_available'):
                continue
            self._log("Failed to flag plugin for update '{}'".format(record.get('plugin_id')), level='debug')
            return False

        return True

    def uninstall_plugins_by_db_table_id(self, plugin_table_ids: list):
        """
        Remove a Plugin by it's DB table ID column.
        This will also remove the Plugin directory and all it's contents.

        :param plugin_table_ids:
        :return:
        """
        self._log("Uninstall plugins '{}'".format(plugin_table_ids), level='debug')

        # Fetch records
        records_by_id = self.get_plugin_list_filtered_and_sorted(id_list=plugin_table_ids)

        # Remove each plugin from disk
        for record in records_by_id:
            plugin_directory = self.get_plugin_path(record.get('plugin_id'))
            self._log("Removing plugin files from disk '{}'".format(plugin_directory), level='debug')
            try:
                shutil.rmtree(plugin_directory)
            except Exception as e:
                self._log("Exception while removing directory {}:".format(plugin_directory), message2=str(e),
                          level="exception")

        # Delete by ID in DB
        if not Plugins.delete().where(Plugins.id.in_(plugin_table_ids)).execute():
            return False

        return True

    def update_plugins_by_db_table_id(self, plugin_table_ids):
        self._log("Update plugins '{}'".format(plugin_table_ids), level='debug')

        # Fetch records
        records_by_id = self.get_plugin_list_filtered_and_sorted(id_list=plugin_table_ids)

        # Update each plugin in turn
        for record in records_by_id:
            if self.install_plugin_by_id(record.get('plugin_id')):
                continue
            self._log("Failed to update plugin '{}'".format(record.get('plugin_id')), level='debug')
            return False

        return True

    def set_plugin_flow(self, plugin_type, flow):
        # Delete all current flow data for this plugin type
        delete_query = PluginFlow.delete().where(PluginFlow.plugin_type == plugin_type)
        delete_query.execute()

        success = True
        priority = 1
        for plugin in flow:
            plugin_id = plugin.get('plugin_id')

            # Fetch the plugin info
            plugin_info = Plugins.select().where(Plugins.plugin_id == plugin_id).first()
            if not plugin_info:
                continue

            # Save the plugin flow
            flow_dict = {
                'plugin_id':   plugin_info.id,
                'plugin_name': plugin_info.plugin_id,
                'plugin_type': plugin_type,
                'position':    priority,
            }
            plugin_flow = PluginFlow.create(**flow_dict)
            priority += 1

            if not plugin_flow:
                success = False

        return success

    def get_plugin_modules_by_type(self, plugin_type):
        """
        Return a list of enabled plugin modules when given a plugin type

        Runners are filtered by the given 'plugin_type' and sorted by
        configured order of execution.

        :param plugin_type:
        :return:
        """
        # Refresh session
        s = Session()
        s.register_unmanic(s.get_installation_uuid())

        # Update enabled plugins
        self.ensure_session_level_for_plugins(s.level)

        # First fetch all enabled plugins
        order = [
            {
                "model":  PluginFlow,
                "column": 'position',
                "dir":    'asc',
            },
            {
                "column": 'name',
                "dir":    'asc',
            },
        ]
        enabled_plugins = self.get_plugin_list_filtered_and_sorted(order=order, enabled=True, plugin_type=plugin_type)

        # Fetch all plugin modules from the given list of enabled plugins
        plugin_executor = PluginExecutor()
        plugin_data = plugin_executor.get_plugin_data_by_type(enabled_plugins, plugin_type)

        # Return modules
        return plugin_data

    def ensure_session_level_for_plugins(self, level):
        if level > 1:
            # Session level is valid for running plugins
            return True

        if level == 0:
            self._log("Plugin support not available. To enable plugin support, sign in...", level='warning')
        elif level == 1:
            self._log("Plugin support not available. Consider becoming a supporter if you wish to enable plugin support.",
                      level='warning')

        # Disable plugins
        Plugins.update(enabled=False).execute()
        return False

    @staticmethod
    def test_plugin_runner(plugin_id, plugin_type, test_data=None):
        plugin_executor = PluginExecutor()
        return plugin_executor.test_plugin_runner(plugin_id, plugin_type, test_data)
