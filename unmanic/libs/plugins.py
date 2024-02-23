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
from unmanic.libs.library import Library
from unmanic.libs.session import Session
from unmanic.libs.singleton import SingletonType
from unmanic.libs.unmodels import EnabledPlugins, LibraryPluginFlow, Plugins, PluginRepos
from unmanic.libs.unplugins import PluginExecutor


class PluginsHandler(object, metaclass=SingletonType):
    """
    Set plugin version.
    Plugins must be compatible with this version to be installed.
    """
    version: int = 2

    def __init__(self, *args, **kwargs):
        self.settings = config.Config()
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

    @staticmethod
    def get_default_repo():
        return "default"

    def get_plugin_repos(self):
        """
        Returns a list of plugin repos

        :return:
        """
        default_repo = self.get_default_repo()
        repo_list = [
            {
                "path": default_repo
            }
        ]

        repos = PluginRepos.select().order_by(PluginRepos.id.asc())
        for repo in repos:
            repo_dict = repo.model_to_dict()
            if repo_dict.get('path') == default_repo:
                continue
            repo_list.append(repo_dict)

        return repo_list

    def set_plugin_repos(self, repo_list):
        # Ensure list of repo URLs is valid
        for repo_path in repo_list:
            repo_data = self.fetch_remote_repo_data(repo_path)
            if not repo_data:
                return False

        # Remove all existing repos
        PluginRepos.delete().execute()

        # Add new repos
        data = []
        for repo_path in repo_list:
            data.append({"path": repo_path})

        PluginRepos.insert_many(data).execute()

        return True

    def fetch_remote_repo_data(self, repo_path):
        # Fetch remote JSON file
        session = Session()
        uuid = session.get_installation_uuid()
        level = session.get_supporter_level()
        repo = base64.b64encode(repo_path.encode('utf-8')).decode('utf-8')
        api_path = f'plugin_repos/get_repo_data/uuid/{uuid}/level/{level}/repo/{repo}'
        data, status_code = session.api_get(
            'unmanic-api',
            1,
            api_path,
        )
        if status_code >= 500:
            self._log(f"Failed to fetch plugin repo from '{api_path}'. Code:{status_code}", level="debug")
        return data

    def update_plugin_repos(self):
        """
        Updates the local cached data of plugin repos

        :return:
        """
        plugins_directory = self.settings.get_plugins_path()
        if not os.path.exists(plugins_directory):
            os.makedirs(plugins_directory)
        current_repos_list = self.get_plugin_repos()
        for repo in current_repos_list:
            repo_path = repo.get('path')
            repo_id = self.get_plugin_repo_id(repo_path)

            # Fetch remote JSON file
            repo_data = self.fetch_remote_repo_data(repo_path)

            # Dumb object to local JSON file
            repo_cache = self.get_repo_cache_file(repo_id)
            self._log("Repo cache file '{}'.".format(repo_cache), level="info")
            try:
                with open(repo_cache, 'w') as f:
                    json.dump(repo_data, f, indent=4)
            except json.JSONDecodeError as e:
                self._log("Unable to update plugin repo '{}'.".format(repo_path), str(e), level="error")
        return True

    def get_settings_of_all_installed_plugins(self):
        all_settings = {}

        # First fetch all enabled plugins
        order = [
            {
                "column": 'name',
                "dir":    'asc',
            },
        ]
        installed_plugins = self.get_plugin_list_filtered_and_sorted(order=order)

        # Fetch settings for each plugin
        plugin_executor = PluginExecutor()
        for plugin in installed_plugins:
            plugin_settings, plugin_settings_meta = plugin_executor.get_plugin_settings(plugin.get('plugin_id'))
            all_settings[plugin.get('plugin_id')] = plugin_settings

        # Return modules
        return all_settings

    def read_repo_data(self, repo_id):
        repo_cache = self.get_repo_cache_file(repo_id)
        if os.path.exists(repo_cache):
            with open(repo_cache) as f:
                repo_data = json.load(f)
            return repo_data
        return {}

    def get_plugin_info(self, plugin_id):
        plugin_info = {}
        plugin_directory = os.path.join(self.settings.get_plugins_path(), plugin_id)
        info_file = os.path.join(plugin_directory, 'info.json')
        if os.path.exists(info_file):
            # Read plugin info.json
            with open(info_file) as json_file:
                plugin_info = json.load(json_file)
        return plugin_info

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
                # Only show plugins that are compatible with this version
                # Plugins will require a 'compatibility' entry in their info.json file.
                #   This must list the plugin handler versions that it is compatible with
                if self.version not in plugin.get('compatibility', []):
                    continue

                plugin_package_url = "{0}/{1}/{1}-{2}.zip".format(repo_data_directory, plugin.get('id'), plugin.get('version'))
                plugin_changelog_url = "{0}/{1}/changelog.md".format(repo_data_directory, plugin.get('id'))

                # Check if plugin is already installed:
                plugin_status = {
                    'installed': False,
                }
                plugin_info = self.get_plugin_info(plugin.get('id'))
                if plugin_info:
                    local_version = plugin_info.get('version')
                    # Parse the currently installed version number and check if it matches
                    remote_version = plugin.get('version')
                    if local_version == remote_version:
                        plugin_status = {
                            'installed':        True,
                            'update_available': False,
                        }
                    else:
                        # There is an update available
                        self.flag_plugin_for_update_by_id(plugin.get("id"))
                        plugin_status = {
                            'installed':        True,
                            'update_available': True,
                        }

                return_list.append(
                    {
                        'plugin_id':     plugin.get('id'),
                        'name':          plugin.get('name'),
                        'author':        plugin.get('author'),
                        'description':   plugin.get('description'),
                        'version':       plugin.get('version'),
                        'icon':          plugin.get('icon', ''),
                        'tags':          plugin.get('tags'),
                        'status':        plugin_status,
                        'package_url':   plugin_package_url,
                        'changelog_url': plugin_changelog_url,
                        'repo_name':     repo_meta.get('name'),
                    }
                )
        return return_list

    def get_installable_plugins_list(self, filter_repo_id=None):
        """
        Return a list of plugins that can be installed
        Optionally filter by repo

        :param filter_repo_id:
        :return:
        """
        return_list = []

        # First fetch a list of available repos
        current_repos_list = self.get_plugin_repos()
        for repo in current_repos_list:
            repo_path = repo.get('path')
            repo_id = self.get_plugin_repo_id(repo_path)
            if filter_repo_id and repo_id != int(filter_repo_id):
                # Filtering by repo ID and this one does not match
                continue
            repo_data = self.read_repo_data(repo_id)
            plugins_in_repo = self.get_plugins_in_repo_data(repo_data)
            for plugin_data in plugins_in_repo:
                plugin_data['repo_id'] = str(repo_id)
            return_list += plugins_in_repo

        return return_list

    def read_remote_changelog_file(self, changelog_url):
        r = requests.get(changelog_url, timeout=1)
        if r.status_code == 200:
            return r.text
        return ''

    def notify_site_of_plugin_install(self, plugin):
        """
        Notify the unmanic.app site API of the installation.
        This is used for metric stats so that we can get a count of plugin downloads.

        :param plugin:
        :return:
        """
        # Post
        session = Session()
        uuid = session.get_installation_uuid()
        level = session.get_supporter_level()
        post_data = {
            "uuid":      uuid,
            "level":     level,
            "plugin_id": plugin.get("plugin_id"),
            "author":    plugin.get("author"),
            "version":   plugin.get("version"),
        }
        try:
            repo_data, status_code = session.api_post('unmanic-api', 1, 'plugin_repos/record_install', post_data)
            if not repo_data.get('success'):
                session.register_unmanic()
        except Exception as e:
            self._log("Exception while logging plugin install.", str(e), level="debug")
            return False

    def install_plugin_by_id(self, plugin_id, repo_id=None):
        """
        Find the matching plugin info for the given plugin ID.
        Download the plugin if it is found and return the result.
        If it is not found, return False.

        :param plugin_id:
        :param repo_id:
        :return:
        """
        plugin_list = self.get_installable_plugins_list(filter_repo_id=repo_id)
        for plugin in plugin_list:
            if plugin.get('plugin_id') == plugin_id:
                success = self.download_and_install_plugin(plugin)

                if success:
                    try:
                        # Write the plugin info to the DB
                        plugin_directory = self.get_plugin_path(plugin.get("plugin_id"))
                        result = self.write_plugin_data_to_db(plugin, plugin_directory)
                        if result:
                            self._log("Installed plugin '{}'".format(plugin_id), level="info")

                        # Ensure the plugin module is reloaded (if it was previously loaded)
                        plugin_executor = PluginExecutor()
                        plugin_executor.reload_plugin_module(plugin.get('plugin_id'))

                        return result
                    except Exception as e:
                        self._log("Exception while installing plugin '{}'.".format(plugin), str(e), level="exception")

        return False

    def install_plugin_from_path_on_disk(self, abspath):
        """
        Install a plugin from a ZIP file on disk

        :param abspath:
        :return:
        """
        # TODO: Ensure that this is a zip file
        try:
            plugin_info = self.install_plugin(abspath)

            # Set the plugin_id variable used when writing data to DB.
            # The returned 'plugin_info' is just a readout of the info.json file which has this set to 'id'
            plugin_info['plugin_id'] = plugin_info.get('id')

            # Cleanup zip file
            if os.path.isfile(abspath):
                os.remove(abspath)

            # Write the plugin info to the DB
            plugin_directory = self.get_plugin_path(plugin_info.get("plugin_id"))
            result = self.write_plugin_data_to_db(plugin_info, plugin_directory)
            if result:
                self._log("Installed plugin '{}'".format(plugin_info.get("plugin_id")), level="info")

            # Ensure the plugin module is reloaded (if it was previously loaded)
            plugin_executor = PluginExecutor()
            plugin_executor.reload_plugin_module(plugin_info.get('plugin_id'))

            return result
        except Exception as e:
            self._log("Exception while installing plugin from zip '{}'.".format(abspath), str(e), level="exception")

        return False

    def download_and_install_plugin(self, plugin):
        """
        Download and install a given plugin

        :param plugin:
        :return:
        """
        self._log("Installing plugin '{}'".format(plugin.get("name")), level='debug')
        # Try to fetch URL
        try:
            # Fetch remote zip file
            destination = self.download_plugin(plugin)

            # Install downloaded plugin
            self.install_plugin(destination, plugin.get("plugin_id"))

            # Cleanup zip file
            if os.path.isfile(destination):
                os.remove(destination)

            self.notify_site_of_plugin_install(plugin)

            return True

        except Exception as e:
            success = False
            self._log("Exception while installing plugin '{}'.".format(plugin), str(e), level="exception")

        return False

    def download_plugin(self, plugin):
        """
        Download a given plugin to a temp directory

        :param plugin:
        :return:
        """
        # Fetch remote zip file
        destination = self.get_plugin_download_cache_path(plugin.get("plugin_id"), plugin.get("version"))
        self._log("Downloading plugin '{}' to '{}'".format(plugin.get("package_url"), destination), level='debug')
        with requests.get(plugin.get("package_url"), stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=128):
                    f.write(chunk)
        return destination

    def install_plugin(self, zip_file, plugin_id=None):
        """
        Install a given plugin from a zip file

        :param zip_file:
        :param plugin_id:
        :return:
        """
        # Read plugin ID from zip contents info.json if no plugin_id was provided
        if not plugin_id:
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                plugin_info = json.loads(zip_ref.read('info.json'))
            plugin_id = plugin_info.get('id')
        # Create plugin destination directory based on plugin ID
        plugin_directory = self.get_plugin_path(plugin_id)
        # Prevent installation if destination has a git repository. This plugin is probably under development
        self._log(os.path.join(str(plugin_directory), '.git'))
        if os.path.exists(os.path.join(str(plugin_directory), '.git')):
            raise Exception("Plugin directory contains a git repository. Uninstall this source version before installing.")
        # Extract zip file contents
        self._log("Extracting plugin to '{}'".format(plugin_directory), level='debug')
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(str(plugin_directory))
        # Return installed plugin info
        return self.get_plugin_info(plugin_id)

    @staticmethod
    def write_plugin_data_to_db(plugin, plugin_directory):
        # Add installed plugin to database
        plugin_data = {
            Plugins.plugin_id:        plugin.get("plugin_id"),
            Plugins.name:             plugin.get("name"),
            Plugins.author:           plugin.get("author"),
            Plugins.version:          plugin.get("version"),
            Plugins.tags:             plugin.get("tags"),
            Plugins.description:      plugin.get("description"),
            Plugins.icon:             plugin.get("icon"),
            Plugins.local_path:       plugin_directory,
            Plugins.update_available: False,
        }
        plugin_entry = Plugins.get_or_none(plugin_id=plugin.get("plugin_id"))
        if plugin_entry is not None:
            # Update the existing entry
            update_query = (Plugins
                            .update(plugin_data)
                            .where(Plugins.plugin_id == plugin.get("plugin_id")))
            update_query.execute()
        else:
            # Insert a new entry
            Plugins.insert(plugin_data).execute()

        return True

    def get_total_plugin_list_count(self):
        task_query = Plugins.select().order_by(Plugins.id.desc())
        return task_query.count()

    def get_plugin_list_filtered_and_sorted(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                            enabled=None, plugin_id=None, plugin_type=None, library_id=None):
        try:
            query = (Plugins.select())

            if plugin_type:
                if library_id is not None:
                    join_condition = (
                        (LibraryPluginFlow.plugin_id == Plugins.id) & (LibraryPluginFlow.plugin_type == plugin_type) & (
                        LibraryPluginFlow.library_id == library_id))
                else:
                    join_condition = (
                        (LibraryPluginFlow.plugin_id == Plugins.id) & (LibraryPluginFlow.plugin_type == plugin_type))
                query = query.join(LibraryPluginFlow, join_type='LEFT OUTER JOIN', on=join_condition)

            if id_list:
                query = query.where(Plugins.id.in_(id_list))

            if search_value:
                query = query.where((Plugins.name.contains(search_value)) | (Plugins.author.contains(search_value)) | (
                    Plugins.tags.contains(search_value)))

            if plugin_id is not None:
                query = query.where(Plugins.plugin_id.in_([plugin_id]))

            # Deprecate this "enabled" status as plugins are now enabled when the are assigned to a library
            if enabled is not None:
                raise Exception("Fetching plugins by 'enabled' status is deprecated")

            if library_id is not None:
                join_condition = (
                    (EnabledPlugins.plugin_id == Plugins.id) & (EnabledPlugins.library_id == library_id))
                query = query.join(EnabledPlugins, join_type='LEFT OUTER JOIN', on=join_condition)
                query = query.where(EnabledPlugins.plugin_id != None)

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
            # Unload plugin modules
            try:
                PluginExecutor.unload_plugin_module(record.get('plugin_id'))
            except Exception as e:
                self._log("Exception while unloading python module {}:".format(record.get('plugin_id')), message2=str(e),
                          level="exception")

            # Remove from disk
            plugin_directory = self.get_plugin_path(record.get('plugin_id'))
            self._log("Removing plugin files from disk '{}'".format(plugin_directory), level='debug')
            try:
                # Delete the info file first to prevent any other process trying to read the plugin.
                # Without the info file, the plugin is effectivly uninstalled
                info_file = os.path.join(plugin_directory, 'info.json')
                if os.path.exists(info_file):
                    os.remove(info_file)
                # Cleanup the rest of the plugin directory
                shutil.rmtree(plugin_directory)
            except Exception as e:
                self._log("Exception while removing directory {}:".format(plugin_directory), message2=str(e),
                          level="exception")

        # Unlink from library by ID in DB
        EnabledPlugins.delete().where(EnabledPlugins.plugin_id.in_(plugin_table_ids)).execute()

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

    def set_plugin_flow(self, plugin_type, library_id, flow):
        """
        Update the plugin flow for all plugins in a given plugin type

        :param plugin_type:
        :param library_id:
        :param flow:
        :return:
        """
        # Delete all current flow data for this plugin type
        delete_query = LibraryPluginFlow.delete().where(
            (LibraryPluginFlow.plugin_type == plugin_type) & (LibraryPluginFlow.library_id == library_id))
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
            plugin_flow = self.set_plugin_flow_position_for_single_plugin(plugin_info, plugin_type, library_id, priority)
            priority += 1

            if not plugin_flow:
                success = False

        return success

    @staticmethod
    def set_plugin_flow_position_for_single_plugin(plugin_info: Plugins, plugin_type: str, library_id: int, priority: int):
        """
        Update the plugin flow for a single plugin and type with the provided priority.

        :param plugin_info:
        :param plugin_type:
        :param library_id:
        :param priority:
        :return:
        """
        pass
        # Save the plugin flow
        flow_dict = {
            'plugin_id':   plugin_info.id,
            'library_id':  library_id,
            'plugin_name': plugin_info.plugin_id,
            'plugin_type': plugin_type,
            'position':    priority,
        }
        plugin_flow = LibraryPluginFlow.create(**flow_dict)

        return plugin_flow

    def get_enabled_plugin_modules_by_type(self, plugin_type, library_id=None):
        """
        Return a list of enabled plugin modules when given a plugin type

        Runners are filtered by the given 'plugin_type' and sorted by
        configured order of execution.

        If no library ID is provided, this will return all installed plugins for that type.
        This case should only be used for plugin runner types that are not associated with a library.

        :param plugin_type:
        :param library_id:
        :return:
        """
        # Refresh session
        s = Session()
        s.register_unmanic()

        # First fetch all enabled plugins
        order = [
            {
                "model":  LibraryPluginFlow,
                "column": 'position',
                "dir":    'asc',
            },
            {
                "column": 'name',
                "dir":    'asc',
            },
        ]
        enabled_plugins = self.get_plugin_list_filtered_and_sorted(order=order, plugin_type=plugin_type, library_id=library_id)

        # Fetch all plugin modules from the given list of enabled plugins
        plugin_executor = PluginExecutor()
        plugin_data = plugin_executor.get_plugin_data_by_type(enabled_plugins, plugin_type)

        # Return modules
        return plugin_data

    def exec_plugin_runner(self, data, plugin_id, plugin_type):
        """
        Execute a plugin runner

        :param data:
        :param plugin_id:
        :param plugin_type:
        :return:
        """
        plugin_executor = PluginExecutor()
        return plugin_executor.execute_plugin_runner(data, plugin_id, plugin_type)

    def get_incompatible_enabled_plugins(self, frontend_messages=None):
        """
        Ensure that the currently installed plugins are compatible with this PluginsHandler version

        :param frontend_messages:
        :return:
        :rtype:
        """
        # Fetch all libraries
        all_libraries = Library.get_all_libraries()

        def add_frontend_message(plugin_id, name):
            # If the frontend messages queue was included in request, append a message
            if frontend_messages:
                frontend_messages.put(
                    {
                        'id':      'incompatiblePlugin_{}'.format(plugin_id),
                        'type':    'error',
                        'code':    'incompatiblePlugin',
                        'message': name,
                        'timeout': 0
                    }
                )

        # Fetch all enabled plugins
        incompatible_list = []
        for library in all_libraries:
            enabled_plugins = self.get_plugin_list_filtered_and_sorted(library_id=library.get('id'))

            # Ensure only compatible plugins are enabled
            # If all enabled plugins are compatible, then return true
            for record in enabled_plugins:
                try:
                    # Ensure plugin is compatible
                    plugin_info = self.get_plugin_info(record.get('plugin_id'))
                except Exception as e:
                    plugin_info = None
                    self._log("Exception while fetching plugin info for {}:".format(record.get('plugin_id')), message2=str(e),
                              level="exception")
                if plugin_info:
                    # Plugins will require a 'compatibility' entry in their info.json file.
                    #   This must list the plugin handler versions that it is compatible with
                    if self.version in plugin_info.get('compatibility', []):
                        continue

                incompatible_list.append(
                    {
                        'plugin_id': record.get('plugin_id'),
                        'name':      record.get('name'),
                    }
                )
                add_frontend_message(record.get('plugin_id'), record.get('name'))

        return incompatible_list

    @staticmethod
    def get_plugin_types_with_flows():
        """
        Returns a list of all available plugin types

        :return:
        """
        return_plugin_types = []
        plugin_ex = PluginExecutor()
        types_list = plugin_ex.get_all_plugin_types()
        # Filter out the types without flows
        for plugin_type in types_list:
            if plugin_type.get('has_flow'):
                return_plugin_types.append(plugin_type.get('id'))
        return return_plugin_types

    def get_enabled_plugin_flows_for_plugin_type(self, plugin_type, library_id):
        """
        Fetch all enabled plugin flows for a plugin type

        :param plugin_type:
        :param library_id:
        :return:
        """
        return_plugin_flow = []
        for plugin_module in self.get_enabled_plugin_modules_by_type(plugin_type, library_id=library_id):
            return_plugin_flow.append(
                {
                    "plugin_id":   plugin_module.get("plugin_id"),
                    "name":        plugin_module.get("name", ""),
                    "author":      plugin_module.get("author", ""),
                    "description": plugin_module.get("description", ""),
                    "version":     plugin_module.get("version", ""),
                    "icon":        plugin_module.get("icon", ""),
                }
            )
        return return_plugin_flow
