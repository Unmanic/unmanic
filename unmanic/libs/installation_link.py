#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.installation_link.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     28 Oct 2021, (7:24 PM)

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
import os.path
import queue
import threading
import time

import requests
from requests.auth import HTTPBasicAuth
from requests_toolbelt import MultipartEncoder

from unmanic import config
from unmanic.libs import common, session, task, unlogger
from unmanic.libs.library import Library
from unmanic.libs.session import Session
from unmanic.libs.singleton import SingletonType


class RequestHandler:

    def __init__(self, *args, **kwargs):
        self.auth = kwargs.get('auth', '')
        # Set username (could be passed in as None)
        self.username = ''
        if kwargs.get('username'):
            self.username = kwargs.get('username')
        # Set password (could be passed in as None)
        self.password = ''
        if kwargs.get('password'):
            self.password = kwargs.get('password')

    def __get_request_auth(self):
        request_auth = None
        if self.auth and self.auth.lower() == 'basic':
            request_auth = HTTPBasicAuth(self.username, self.password)
        return request_auth

    def get(self, url, **kwargs):
        return requests.get(url, auth=self.__get_request_auth(), **kwargs)

    def post(self, url, **kwargs):
        return requests.post(url, auth=self.__get_request_auth(), **kwargs)

    def delete(self, url, **kwargs):
        return requests.delete(url, auth=self.__get_request_auth(), **kwargs)


class Links(object, metaclass=SingletonType):
    _network_transfer_lock = {}

    def __init__(self, *args, **kwargs):
        self.settings = config.Config()
        self.session = session.Session()
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __format_address(self, address: str):
        # Strip all whitespace
        address = address.strip()
        # Add http if it does not exist
        if not address.lower().startswith('http'):
            address = "http://{}".format(address)
        # Strip any trailing slashes
        address = address.rstrip('/')
        return address

    def __merge_config_dicts(self, config_dict, compare_dict):
        for key in config_dict.keys():
            if config_dict.get(key) != compare_dict.get(key) and compare_dict.get(key) is not None:
                # Apply the new value
                config_dict[key] = compare_dict.get(key)
                # Also flag the dict as updated
                config_dict['last_updated'] = time.time()

    def __generate_default_config(self, config_dict: dict):
        return {
            "address":                         config_dict.get('address', '???'),
            "auth":                            config_dict.get('auth', 'None'),
            "username":                        config_dict.get('username', ''),
            "password":                        config_dict.get('password', ''),
            "enable_receiving_tasks":          config_dict.get('enable_receiving_tasks', False),
            "enable_sending_tasks":            config_dict.get('enable_sending_tasks', False),
            "enable_task_preloading":          config_dict.get('enable_task_preloading', True),
            "preloading_count":                config_dict.get('preloading_count', 2),
            "enable_checksum_validation":      config_dict.get('enable_checksum_validation', False),
            "enable_config_missing_libraries": config_dict.get('enable_config_missing_libraries', False),
            "enable_distributed_worker_count": config_dict.get('enable_distributed_worker_count', False),
            "name":                            config_dict.get('name', '???'),
            "version":                         config_dict.get('version', '???'),
            "uuid":                            config_dict.get('uuid', '???'),
            "available":                       config_dict.get('available', False),
            "task_count":                      config_dict.get('task_count', 0),
            "last_updated":                    config_dict.get('last_updated', time.time()),
        }

    def acquire_network_transfer_lock(self, url, transfer_limit=1, lock_type='send'):
        """
        Limit transfers to each installation to 1 at a time

        :param url:
        :param transfer_limit:
        :param lock_type:
        :return:
        """
        time_now = time.time()
        lock = threading.RLock()
        # Limit maximum transfer limit to 5
        if transfer_limit > 5:
            transfer_limit = 5
        # Acquire a lock if one is available
        with lock:
            for tx_lock in range(transfer_limit):
                lock_key = "[{}-{}]-{}".format(lock_type, tx_lock, url)
                if self._network_transfer_lock.get(lock_key, {}).get('expires', 0) < time_now:
                    # Create new upload lock that will expire in 1 minute
                    self._network_transfer_lock[lock_key] = {
                        'expires': (time_now + 60),
                    }
                    # Return success
                    return lock_key
            # Failed to acquire network transfer lock
            return False

    def release_network_transfer_lock(self, lock_key):
        """
        Expire the transfer lock for the given lock_key

        :param lock_key:
        :return:
        """
        lock = threading.RLock()
        with lock:
            # Expire the lock for this address
            self._network_transfer_lock[lock_key] = {}
            return True

    def remote_api_get(self, remote_config: dict, endpoint: str, timeout=2):
        """
        GET to remote installation API

        :param remote_config:
        :param endpoint:
        :param timeout:
        :return:
        """
        request_handler = RequestHandler(
            auth=remote_config.get('auth'),
            username=remote_config.get('username'),
            password=remote_config.get('password'),
        )
        address = self.__format_address(remote_config.get('address'))
        url = "{}{}".format(address, endpoint)
        res = request_handler.get(url, timeout=timeout)
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [400, 404, 405, 500]:
            json_data = res.json()
            self._log("Error while executing GET on remote installation API - {}. Message: '{}'".format(
                endpoint,
                json_data.get('error')),
                message2=json_data.get('traceback', []), level='error')
        return {}

    def remote_api_post(self, remote_config: dict, endpoint: str, data: dict, timeout=2):
        """
        POST to remote installation API

        :param remote_config:
        :param endpoint:
        :param data:
        :param timeout:
        :return:
        """
        request_handler = RequestHandler(
            auth=remote_config.get('auth'),
            username=remote_config.get('username'),
            password=remote_config.get('password'),
        )
        address = self.__format_address(remote_config.get('address'))
        url = "{}{}".format(address, endpoint)
        res = request_handler.post(url, json=data, timeout=timeout)
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [400, 404, 405, 500]:
            json_data = res.json()
            self._log("Error while executing POST on remote installation API - {}. Message: '{}'".format(
                endpoint,
                json_data.get('error')),
                message2=json_data.get('traceback', []), level='error')
            return json_data
        return {}

    def remote_api_post_file(self, remote_config: dict, endpoint: str, path: str):
        """
        Send a file to the remote installation
        No timeout is set so the request will continue until closed

        :param remote_config:
        :param endpoint:
        :param path:
        :return:
        """
        request_handler = RequestHandler(
            auth=remote_config.get('auth'),
            username=remote_config.get('username'),
            password=remote_config.get('password'),
        )
        address = self.__format_address(remote_config.get('address'))
        url = "{}{}".format(address, endpoint)
        # NOTE: If you remove a content type from the upload (text/plain) the file upload fails
        # NOTE2: The 'ith open(path, "rb") as f' method reads the file into memory before uploading.
        #   This is slow and not ideal for devices with small amounts of ram.
        #   ```
        #       with open(path, "rb") as f:
        #           files = {"fileName": (os.path.basename(path), f, 'text/plain')}
        #           res = requests.post(url, files=files)
        #   ```
        m = MultipartEncoder(fields={'fileName': (os.path.basename(path), open(path, 'rb'), 'text/plain')})
        res = request_handler.post(url, data=m, headers={'Content-Type': m.content_type})
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [400, 404, 405, 500]:
            json_data = res.json()
            self._log("Error while uploading file to remote installation API - {}. Message: '{}'".format(
                endpoint,
                json_data.get('error')),
                message2=json_data.get('traceback', []), level='error')
        return {}

    def remote_api_delete(self, remote_config: dict, endpoint: str, data: dict, timeout=2):
        """
        DELETE to remote installation API

        :param remote_config:
        :param endpoint:
        :param data:
        :param timeout:
        :return:
        """
        request_handler = RequestHandler(
            auth=remote_config.get('auth'),
            username=remote_config.get('username'),
            password=remote_config.get('password'),
        )
        address = self.__format_address(remote_config.get('address'))
        url = "{}{}".format(address, endpoint)
        res = request_handler.delete(url, json=data, timeout=timeout)
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [400, 404, 405, 500]:
            json_data = res.json()
            self._log("Error while executing DELETE on remote installation API - {}. Message: '{}'".format(
                endpoint,
                json_data.get('error')),
                message2=json_data.get('traceback', []), level='error')
        return {}

    def remote_api_get_download(self, remote_config: dict, endpoint: str, path: str):
        """
        Download a file from a remote installation

        :param remote_config:
        :param endpoint:
        :param path:
        :return:
        """
        request_handler = RequestHandler(
            auth=remote_config.get('auth'),
            username=remote_config.get('username'),
            password=remote_config.get('password'),
        )
        address = self.__format_address(remote_config.get('address'))
        url = "{}{}".format(address, endpoint)
        with request_handler.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        f.write(chunk)
        return True

    def validate_remote_installation(self, address: str, **kwargs):
        """
        Validate a remote Unmanic installation by requesting
        its system info and version

        :param address:
        :param username:
        :param password:
        :return:
        """
        address = self.__format_address(address)

        request_handler = RequestHandler(
            auth=kwargs.get('auth'),
            username=kwargs.get('username'),
            password=kwargs.get('password'),
        )

        # Fetch config
        url = "{}/unmanic/api/v2/settings/configuration".format(address)
        res = request_handler.get(url, timeout=2)
        if res.status_code != 200:
            if res.status_code in [400, 404, 405, 500]:
                json_data = res.json()
                self._log("Error while fetching remote installation config. Message: '{}'".format(json_data.get('error')),
                          message2=json_data.get('traceback', []), level='error')
            return {}
        system_configuration_data = res.json()

        # Fetch settings
        url = "{}/unmanic/api/v2/settings/read".format(address)
        res = request_handler.get(url, timeout=2)
        if res.status_code != 200:
            if res.status_code in [400, 404, 405, 500]:
                json_data = res.json()
                self._log("Error while fetching remote installation settings. Message: '{}'".format(json_data.get('error')),
                          message2=json_data.get('traceback', []), level='error')
            return {}
        settings_data = res.json()

        # Fetch version
        url = "{}/unmanic/api/v2/version/read".format(address)
        res = request_handler.get(url, timeout=2)
        if res.status_code != 200:
            if res.status_code in [400, 404, 405, 500]:
                json_data = res.json()
                self._log("Error while fetching remote installation version. Message: '{}'".format(json_data.get('error')),
                          message2=json_data.get('traceback', []), level='error')
            return {}
        version_data = res.json()

        # Fetch version
        url = "{}/unmanic/api/v2/session/state".format(address)
        res = request_handler.get(url, timeout=2)
        if res.status_code != 200:
            if res.status_code in [400, 404, 405, 500]:
                json_data = res.json()
                self._log(
                    "Error while fetching remote installation session state. Message: '{}'".format(json_data.get('error')),
                    message2=json_data.get('traceback', []), level='error')
            return {}
        session_data = res.json()

        # Fetch task count data
        data = {
            "start":  0,
            "length": 1
        }
        url = "{}/unmanic/api/v2/pending/tasks".format(address)
        res = request_handler.post(url, json=data, timeout=2)
        if res.status_code != 200:
            if res.status_code in [400, 404, 405, 500]:
                json_data = res.json()
                self._log(
                    "Error while fetching remote installation pending task list. Message: '{}'".format(json_data.get('error')),
                    message2=json_data.get('traceback', []), level='error')
            return {}
        tasks_data = res.json()

        return {
            'system_configuration': system_configuration_data.get('configuration'),
            'settings':             settings_data.get('settings'),
            'version':              version_data.get('version'),
            'session':              {
                "level":       session_data.get('level'),
                "picture_uri": session_data.get('picture_uri'),
                "name":        session_data.get('name'),
                "email":       session_data.get('email'),
                "uuid":        session_data.get('uuid'),
            },
            'task_count':           int(tasks_data.get('recordsTotal', 0))
        }

    def update_all_remote_installation_links(self):
        """
        Updates the link status and configuration of linked remote installations

        :return:
        """
        save_settings = False
        installation_id_list = []
        remote_installations = []
        distributed_worker_count_target = self.settings.get_distributed_worker_count_target()
        for local_config in self.settings.get_remote_installations():
            # Ensure address is not added twice by comparing installation IDs
            # Items matching these checks will be skipped over and will not be added to the installation list
            #   that will be re-saved
            if local_config.get('uuid') in installation_id_list and local_config.get('uuid', '???') != '???':
                # Do not update this installation. By doing this it will be removed from the list
                save_settings = True
                continue

            # Ensure the address is something valid
            if not local_config.get('address'):
                save_settings = True
                continue

            # Remove any entries that have an unknown address and uuid
            if local_config.get('address') == '???' and local_config.get('uuid') == '???':
                save_settings = True
                continue

            # Fetch updated data
            installation_data = None
            try:
                installation_data = self.validate_remote_installation(local_config.get('address'),
                                                                      auth=local_config.get('auth'),
                                                                      username=local_config.get('username'),
                                                                      password=local_config.get('password'))
            except Exception:
                pass

            # Generate updated configured values
            updated_config = self.__generate_default_config(local_config)
            updated_config["available"] = False
            if installation_data:
                # Mark the installation as available
                updated_config["available"] = True

                # Append the current task count
                updated_config["task_count"] = installation_data.get('task_count', 0)

                merge_dict = {
                    "name":    installation_data.get('settings', {}).get('installation_name'),
                    "version": installation_data.get('version'),
                    "uuid":    installation_data.get('session', {}).get('uuid'),
                }
                self.__merge_config_dicts(updated_config, merge_dict)

                # Fetch the corresponding remote configuration for this local installation
                remote_config = {}
                try:
                    remote_config = self.fetch_remote_installation_link_config_for_this(local_config)
                except requests.exceptions.Timeout:
                    self._log("Request to fetch remote installation config timed out", level='warning')
                    updated_config["available"] = False
                except requests.exceptions.RequestException as e:
                    self._log("Request to fetch remote installation config failed", message2=str(e), level='warning')
                    updated_config["available"] = False
                except Exception as e:
                    self._log("Failed to fetch remote installation config", message2=str(e), level='error')
                    updated_config["available"] = False

                # If the remote configuration is newer than this one, use those values
                # The remote installation will do the same and this will synchronise
                remote_link_config = remote_config.get('link_config', {})
                if local_config.get('last_updated', 1) < remote_link_config.get('last_updated', 1):
                    # Note that the configuration options are reversed when reading from the remote installation config
                    # These items are not synced here:
                    #   - enable_task_preloading
                    #   - enable_checksum_validation
                    #   - enable_config_missing_libraries
                    if updated_config["enable_receiving_tasks"] != remote_link_config.get('enable_sending_tasks'):
                        updated_config["enable_receiving_tasks"] = remote_link_config.get('enable_sending_tasks')
                        save_settings = True
                    if updated_config["enable_sending_tasks"] != remote_link_config.get('enable_receiving_tasks'):
                        updated_config["enable_sending_tasks"] = remote_link_config.get('enable_receiving_tasks')
                        save_settings = True
                    # Update the distributed_worker_count_target
                    distributed_worker_count_target = remote_config.get('distributed_worker_count_target', 0)
                    # Also sync the last_updated flag
                    updated_config['last_updated'] = remote_link_config.get('last_updated')

                # If the remote config is unable to contact this installation (or it does not have a corresponding config yet)
                #   then also push the configuration
                if not remote_link_config.get('available'):
                    try:
                        self.push_remote_installation_link_config(updated_config)
                    except requests.exceptions.Timeout:
                        self._log("Request to push link config to remote installation timed out", level='warning')
                        updated_config["available"] = False
                    except requests.exceptions.RequestException as e:
                        self._log("Request to push link config to remote installation failed", message2=str(e),
                                  level='warning')
                        updated_config["available"] = False
                    except Exception as e:
                        self._log("Failed to push link config to remote installation", message2=str(e), level='error')
                        updated_config["available"] = False

                # Push library configurations for missing remote libraries (if configured to do so)
                if local_config.get('enable_sending_tasks') and local_config.get('enable_config_missing_libraries'):
                    # Fetch remote installation library name list
                    results = self.remote_api_get(local_config, '/unmanic/api/v2/settings/libraries')
                    existing_library_names = []
                    for library in results.get('libraries', []):
                        existing_library_names.append(library.get('name'))
                    # Loop over local libraries and create an import object for each one that is missing
                    for library in Library.get_all_libraries():
                        # Ignore local libraries that are configured for remote only
                        if library.get('enable_remote_only'):
                            continue
                        # For each of the missing libraries, create a new remote library with that config.
                        if library.get('name') not in existing_library_names:
                            # Export library config
                            import_data = Library.export(library.get('id'))
                            # Set library ID to 0 to generate new library from this import
                            import_data['library_id'] = 0
                            # Configure remote library to be fore remote files only
                            import_data['library_config']['enable_remote_only'] = True
                            import_data['library_config']['enable_scanner'] = False
                            import_data['library_config']['enable_inotify'] = False
                            # Import library on remote installation
                            self._log("Importing remote library config '{}'".format(library.get('name')), message2=import_data,
                                      level='debug')
                            result = self.import_remote_library_config(local_config, import_data)
                            if result is None:
                                # There was a connection issue of some kind. This was already logged.
                                continue
                            if result.get('success'):
                                self._log("Successfully imported library '{}'".format(library.get('name')), level='debug')
                                continue
                            self._log("Failed to import library config '{}'".format(library.get('name')),
                                      message2=result.get('error'), level='error')

            # Only save to file if the settings have been updated
            remote_installations.append(updated_config)

            # Add UUID to list for next loop
            installation_id_list.append(updated_config.get('uuid', '???'))

        # Update installation data. Only save the config to disk if it was modified
        settings_dict = {
            'remote_installations':            remote_installations,
            'distributed_worker_count_target': distributed_worker_count_target
        }
        self.settings.set_bulk_config_items(settings_dict, save_settings=save_settings)

        return remote_installations

    def read_remote_installation_link_config(self, uuid: str):
        """
        Returns the configuration of the remote installation

        :param uuid:
        :return:
        """
        for remote_installation in self.settings.get_remote_installations():
            if remote_installation.get('uuid') == uuid:
                # If not yet configured, set default values before returning
                return self.__generate_default_config(remote_installation)

        # Ensure we have settings data from the remote installation
        raise Exception("Unable to read installation link configuration.")

    def update_single_remote_installation_link_config(self, configuration: dict, distributed_worker_count_target=0):
        """
        Returns the configuration of the remote installation

        :param configuration:
        :param distributed_worker_count_target:
        :return:
        """
        uuid = configuration.get('uuid')
        if not uuid:
            raise Exception("Updating a single installation link configuration requires a UUID.")

        current_distributed_worker_count_target = self.settings.get_distributed_worker_count_target()
        force_update_flag = False
        if int(current_distributed_worker_count_target) != int(distributed_worker_count_target):
            force_update_flag = True

        config_exists = False
        remote_installations = []
        for local_config in self.settings.get_remote_installations():
            updated_config = self.__generate_default_config(local_config)

            # If this is the uuid in the config provided, then update our config with the provided values
            if local_config.get('uuid') == uuid:
                config_exists = True
                self.__merge_config_dicts(updated_config, configuration)

            # If this link is configured for distributed worker count, and that count was change,
            #   force the last update flag to be updated so this change is disseminated
            if force_update_flag and configuration.get('enable_distributed_worker_count'):
                updated_config['last_updated'] = time.time()

            remote_installations.append(updated_config)

        # If the config does not yet exist, the add it now
        if not config_exists:
            remote_installations.append(self.__generate_default_config(configuration))

        # Update installation data and save the config to disk
        settings_dict = {
            'remote_installations':            remote_installations,
            'distributed_worker_count_target': distributed_worker_count_target
        }
        self.settings.set_bulk_config_items(settings_dict, save_settings=True)

    def delete_remote_installation_link_config(self, uuid: str):
        """
        Removes a link configuration for a remote installation given its uuid
        If no uuid match is found, returns False

        :param uuid:
        :return:
        """
        removed = False
        updated_list = []
        for remote_installation in self.settings.get_remote_installations():
            if remote_installation.get('uuid') == uuid:
                # Mark the task as having successfully remoted the installation
                removed = True
                continue
            # Only add remote installations that do not match
            updated_list.append(remote_installation)

        # Update installation data and save the config to disk
        settings_dict = {
            'remote_installations': updated_list,
        }
        self.settings.set_bulk_config_items(settings_dict, save_settings=True)
        return removed

    def fetch_remote_installation_link_config_for_this(self, remote_config: dict):
        """
        Fetches and returns the corresponding link configuration from a remote installation

        :param remote_config:
        :return:
        """
        request_handler = RequestHandler(
            auth=remote_config.get('auth'),
            username=remote_config.get('username'),
            password=remote_config.get('password'),
        )
        address = self.__format_address(remote_config.get('address'))
        url = "{}/unmanic/api/v2/settings/link/read".format(address)
        data = {
            "uuid": self.session.uuid
        }
        res = request_handler.post(url, json=data, timeout=2)
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [400, 404, 405, 500]:
            json_data = res.json()
            self._log("Error while fetching remote installation link config. Message: '{}'".format(json_data.get('error')),
                      message2=json_data.get('traceback', []), level='error')
        return {}

    def push_remote_installation_link_config(self, configuration: dict):
        """
        Pushes the given link config to the remote installation returns the corresponding link configuration from a remote installation

        :param configuration:
        :return:
        """
        request_handler = RequestHandler(
            auth=configuration.get('auth'),
            username=configuration.get('username'),
            password=configuration.get('password'),
        )
        address = self.__format_address(configuration.get('address'))
        url = "{}/unmanic/api/v2/settings/link/write".format(address)

        # First generate an updated config
        updated_config = self.__generate_default_config(configuration)

        # Update the bits for the remote instance
        updated_config['uuid'] = self.session.uuid
        updated_config['name'] = self.settings.get_installation_name()
        updated_config['version'] = self.settings.read_version()

        # Configure settings
        updated_config["enable_receiving_tasks"] = configuration.get('enable_sending_tasks')
        updated_config["enable_sending_tasks"] = configuration.get('enable_receiving_tasks')

        # Current task count
        task_handler = task.Task()
        updated_config["task_count"] = int(task_handler.get_total_task_list_count())

        # Fetch local config for distributed_worker_count_target
        distributed_worker_count_target = self.settings.get_distributed_worker_count_target()

        # Remove some of the other fields. These will need to be adjusted on the remote instance manually
        del updated_config['address']
        del updated_config['available']

        data = {
            'link_config':                     updated_config,
            'distributed_worker_count_target': distributed_worker_count_target
        }
        res = request_handler.post(url, json=data, timeout=2)
        if res.status_code == 200:
            return True
        elif res.status_code in [400, 404, 405, 500]:
            json_data = res.json()
            self._log("Error while pushing remote installation link config. Message: '{}'".format(json_data.get('error')),
                      message2=json_data.get('traceback', []), level='error')
        return False

    def check_remote_installation_for_available_workers(self):
        """
        Return a list of installations with workers available for a remote task.
        This list is filtered by:
            - Only installations that are available
            - Only installations that are configured for sending tasks to
            - Only installations that have not pending tasks
            - Only installations that have at least one idle worker that is not paused

        :return:
        """
        installations_with_info = {}
        for lc in self.settings.get_remote_installations():
            local_config = self.__generate_default_config(lc)

            # Only installations that are available
            if not local_config.get('available'):
                continue

            # Only installations that are configured for sending tasks to
            if not local_config.get('enable_sending_tasks'):
                continue

            # No valid UUID, no valid connection. This link may still be syncing
            if len(local_config.get('uuid', '')) < 20:
                continue

            try:
                # Define auth
                # Only installations that have at least one idle worker that is not paused
                results = self.remote_api_get(local_config, '/unmanic/api/v2/workers/status')
                worker_list = results.get('workers_status', [])

                # Only add installations that have not got pending tasks. This is unless we are configured to preload the queue
                max_pending_tasks = 0
                if local_config.get('enable_task_preloading'):
                    # Preload with the number of workers (regardless of the worker status) plus an additional one to account
                    # for delays in the downloads
                    max_pending_tasks = local_config.get('preloading_count')
                results = self.remote_api_post(local_config, '/unmanic/api/v2/pending/tasks', {
                    "start":  0,
                    "length": 1
                })
                if results.get('error'):
                    continue
                current_pending_tasks = int(results.get('recordsFiltered', 0))
                if local_config.get('enable_task_preloading') and current_pending_tasks >= max_pending_tasks:
                    self._log("Remote installation has exceeded the max remote pending task count ({})".format(
                        current_pending_tasks), level='debug')
                    continue

                # Fetch remote installation library name list
                results = self.remote_api_get(local_config, '/unmanic/api/v2/settings/libraries')
                library_names = []
                for library in results.get('libraries', []):
                    library_names.append(library.get('name'))

                # Ensure that worker count is more than 0
                if len(worker_list):
                    installations_with_info[local_config.get('uuid')] = {
                        "address":                local_config.get('address'),
                        "auth":                   local_config.get('auth'),
                        "username":               local_config.get('username'),
                        "password":               local_config.get('password'),
                        "enable_task_preloading": local_config.get('enable_task_preloading'),
                        "preloading_count":       local_config.get('preloading_count'),
                        "library_names":          library_names,
                        "available_slots":        0,
                    }

                available_workers = False
                for worker in worker_list:
                    # Add a slot for each worker regardless of its status
                    installations_with_info[local_config.get('uuid')]['available_slots'] += 1
                    if worker.get('idle') and not worker.get('paused'):
                        # If any workers are idle and not paused then we have an available worker slot
                        available_workers = True
                        installations_with_info[local_config.get('uuid')]['available_workers'] = True
                    elif not worker.get('idle'):
                        # If any workers are busy with a task then also mark that as an an available worker slot
                        available_workers = True
                        installations_with_info[local_config.get('uuid')]['available_workers'] = True

                # Check if this installation is configured for preloading
                if available_workers and local_config.get('enable_task_preloading'):
                    # Add more slots to fill up the pending task queue
                    while not current_pending_tasks > max_pending_tasks:
                        installations_with_info[local_config.get('uuid')]['available_slots'] += 1
                        current_pending_tasks += 1

            except Exception as e:
                self._log("Failed to contact remote installation '{}'".format(local_config.get('address')), message2=str(e),
                          level='warning')
                continue

        return installations_with_info

    def within_enabled_link_limits(self, frontend_messages=None):
        """
        Ensure enabled plugins are within limits

        :param frontend_messages:
        :return:
        """
        # Fetch level from session
        s = Session()
        s.register_unmanic()
        if s.level > 1:
            return True

        # Fetch all linked remote installations
        remote_installations = self.settings.get_remote_installations()

        def add_frontend_message():
            # If the frontend messages queue was included in request, append a message
            if frontend_messages:
                frontend_messages.put(
                    {
                        'id':      'linkedInstallationLimits',
                        'type':    'error',
                        'code':    'linkedInstallationLimits',
                        'message': '',
                        'timeout': 0
                    }
                )

        # Ensure remote installations are within limits
        # Function was returned above if the user was logged in and able to use infinite
        if len(remote_installations) > s.link_count:
            add_frontend_message()
            return False
        return True

    def new_pending_task_create_on_remote_installation(self, remote_config: dict, abspath: str, library_id: int):
        """
        Create a new pending task on a remote installation.
        The remote installation will return the ID of a generated task.

        :param remote_config:
        :param abspath:
        :param library_id:
        :return:
        """
        try:
            request_handler = RequestHandler(
                auth=remote_config.get('auth'),
                username=remote_config.get('username'),
                password=remote_config.get('password'),
            )
            address = self.__format_address(remote_config.get('address'))
            url = "{}/unmanic/api/v2/pending/create".format(address)
            data = {
                "path":       abspath,
                "library_id": library_id,
                "type":       'remote',
            }
            res = request_handler.post(url, json=data, timeout=2)
            if res.status_code in [200, 400]:
                return res.json()
            elif res.status_code in [404, 405, 500]:
                json_data = res.json()
                self._log("Error while creating new remote pending task. Message: '{}'".format(json_data.get('error')),
                          message2=json_data.get('traceback', []), level='error')
            return {}
        except requests.exceptions.Timeout:
            self._log("Request to create remote pending task timed out '{}'".format(abspath), level='warning')
            return None
        except requests.exceptions.RequestException as e:
            self._log("Request to create remote pending task failed '{}'".format(abspath), message2=str(e), level='warning')
            return None
        except Exception as e:
            self._log("Failed to create remote pending task '{}'".format(abspath), message2=str(e), level='error')
        return {}

    def send_file_to_remote_installation(self, remote_config: dict, path: str):
        """
        Send a file to a remote installation.
        The remote installation will return the ID of a generated task.

        :param remote_config:
        :param path:
        :return:
        """
        try:
            results = self.remote_api_post_file(remote_config, '/unmanic/api/v2/upload/pending/file', path)
            if results.get('error'):
                results = {}
            return results
        except requests.exceptions.RequestException as e:
            self._log("Request to upload to remote installation failed", message2=str(e), level='warning')
        except Exception as e:
            self._log("Failed to upload to remote installation", message2=str(e), level='error')
        return {}

    def remove_task_from_remote_installation(self, remote_config: dict, remote_task_id: int):
        """
        Remove a task from the pending queue

        :param remote_config:
        :param remote_task_id:
        :return:
        """
        try:
            data = {
                "id_list": [remote_task_id]
            }
            return self.remote_api_delete(remote_config, '/unmanic/api/v2/pending/tasks', data, timeout=15)
        except requests.exceptions.Timeout:
            self._log("Request to remove remote task timed out", level='warning')
            return None
        except requests.exceptions.RequestException as e:
            self._log("Request to remove remote task failed", message2=str(e), level='warning')
            return None
        except Exception as e:
            self._log("Failed to remove remote pending task", message2=str(e), level='error')
        return {}

    def get_the_remote_library_config_by_name(self, remote_config: dict, library_name: str):
        """
        Fetch a remote library's configuration by its name

        :param remote_config:
        :param library_name:
        :return:
        """
        try:
            # Fetch remote installation libraries
            results = self.remote_api_get(remote_config, '/unmanic/api/v2/settings/libraries', timeout=4)
            for library in results.get('libraries', []):
                if library.get('name') == library_name:
                    return library
        except requests.exceptions.Timeout:
            self._log("Request to set remote task library timed out", level='warning')
            return None
        except requests.exceptions.RequestException as e:
            self._log("Request to set remote task library failed", message2=str(e), level='warning')
            return None
        except Exception as e:
            self._log("Failed to set remote task library", message2=str(e), level='error')
        return {}

    def set_the_remote_task_library(self, remote_config: dict, remote_task_id: int, library_name: str):
        """
        Set the library for the remote task
        Defaults to the remote installation's default library

        :param remote_config:
        :param remote_task_id:
        :param library_name:
        :return:
        """
        try:
            data = {
                "id_list":      [remote_task_id],
                "library_name": library_name,
            }
            results = self.remote_api_post(remote_config, '/unmanic/api/v2/pending/library/update', data, timeout=7)
            if results.get('error'):
                results = {}
            return results
        except requests.exceptions.Timeout:
            self._log("Request to set remote task library timed out", level='warning')
            return None
        except requests.exceptions.RequestException as e:
            self._log("Request to set remote task library failed", message2=str(e), level='warning')
            return None
        except Exception as e:
            self._log("Failed to set remote task library", message2=str(e), level='error')
        return {}

    def get_remote_pending_task_state(self, remote_config: dict, remote_task_id: int):
        """
        Get the remote pending task status

        :param remote_config:
        :param remote_task_id:
        :return:
        """
        try:
            data = {
                "id_list": [remote_task_id]
            }
            results = self.remote_api_post(remote_config, '/unmanic/api/v2/pending/status/get', data, timeout=7)
            return results
        except requests.exceptions.Timeout:
            self._log("Request to get status of remote task timed out", level='warning')
        except requests.exceptions.RequestException as e:
            self._log("Request to get status of remote task failed", message2=str(e), level='warning')
        except Exception as e:
            self._log("Failed to get status of remote pending task", message2=str(e), level='error')
        return None

    def start_the_remote_task_by_id(self, remote_config: dict, remote_task_id: int):
        """
        Start the remote pending task

        :param remote_config:
        :param remote_task_id:
        :return:
        """
        try:
            data = {
                "id_list": [remote_task_id]
            }
            results = self.remote_api_post(remote_config, '/unmanic/api/v2/pending/status/set/ready', data, timeout=7)
            if results.get('error'):
                results = {}
            return results
        except requests.exceptions.Timeout:
            self._log("Request to start remote task timed out", level='warning')
            return None
        except requests.exceptions.RequestException as e:
            self._log("Request to start remote task failed", message2=str(e), level='warning')
            return None
        except Exception as e:
            self._log("Failed to start remote pending task", message2=str(e), level='error')
        return {}

    def get_all_worker_status(self, remote_config: dict):
        """
        Start the remote pending task

        :param remote_config:
        :return:
        """
        try:
            results = self.remote_api_get(remote_config, '/unmanic/api/v2/workers/status')
            return results.get('workers_status', [])
        except requests.exceptions.Timeout:
            self._log("Request to get worker status timed out", level='warning')
        except requests.exceptions.RequestException as e:
            self._log("Request to get worker status failed", message2=str(e), level='warning')
        except Exception as e:
            self._log("Failed to get worker status", message2=str(e), level='error')
        return []

    def get_single_worker_status(self, remote_config: dict, worker_id: str):
        """
        Start the remote pending task

        :param remote_config:
        :param worker_id:
        :return:
        """
        workers_status = self.get_all_worker_status(remote_config)
        for worker in workers_status:
            if worker.get('id') == worker_id:
                return worker
        return {}

    def terminate_remote_worker(self, remote_config: dict, worker_id: str):
        """
        Start the remote pending task

        :param remote_config:
        :param worker_id:
        :return:
        """
        try:
            data = {
                "worker_id": [worker_id]
            }
            return self.remote_api_delete(remote_config, '/unmanic/api/v2/workers/worker/terminate', data)
        except requests.exceptions.Timeout:
            self._log("Request to terminate remote worker timed out", level='warning')
        except requests.exceptions.RequestException as e:
            self._log("Request to terminate remote worker failed", message2=str(e), level='warning')
        except Exception as e:
            self._log("Failed to terminate remote worker", message2=str(e), level='error')
        return {}

    def fetch_remote_task_data(self, remote_config: dict, remote_task_id: int, path: str):
        """
        Fetch the completed remote task data

        :param remote_config:
        :param remote_task_id:
        :param path:
        :return:
        """
        task_data = {}
        try:
            # Request API generate a DL link
            link_info = self.remote_api_get(remote_config,
                                            '/unmanic/api/v2/pending/download/data/id/{}'.format(remote_task_id))
            if link_info.get('link_id'):
                # Download the data file
                res = self.remote_api_get_download(remote_config, '/unmanic/downloads/{}'.format(link_info.get('link_id')),
                                                   path)
                if res and os.path.exists(path):
                    with open(path) as f:
                        task_data = json.load(f)
        except requests.exceptions.Timeout:
            self._log("Request to fetch remote task data timed out", level='warning')
        except requests.exceptions.RequestException as e:
            self._log("Request to fetch remote task data failed", message2=str(e), level='warning')
        except Exception as e:
            self._log("Failed to fetch remote task data", message2=str(e), level='error')
        return task_data

    def fetch_remote_task_completed_file(self, remote_config: dict, remote_task_id: int, path: str):
        """
        Fetch the completed remote task file

        :param remote_config:
        :param remote_task_id:
        :param path:
        :return:
        """
        try:
            # Request API generate a DL link
            link_info = self.remote_api_get(remote_config,
                                            '/unmanic/api/v2/pending/download/file/id/{}'.format(remote_task_id))
            if link_info.get('link_id'):
                # Download the file
                res = self.remote_api_get_download(remote_config, '/unmanic/downloads/{}'.format(link_info.get('link_id')),
                                                   path)
                if res and os.path.exists(path):
                    return True
        except requests.exceptions.Timeout:
            self._log("Request to fetch remote task completed file timed out", level='warning')
        except requests.exceptions.RequestException as e:
            self._log("Request to fetch remote task completed file failed", message2=str(e), level='warning')
        except Exception as e:
            self._log("Failed to fetch remote task completed file", message2=str(e), level='error')
        return False

    def import_remote_library_config(self, remote_config: dict, import_data: dict):
        """
        Import a library config on a remote installation

        :param remote_config:
        :param import_data:
        :return:
        """
        try:
            results = self.remote_api_post(remote_config, '/unmanic/api/v2/settings/library/import', import_data, timeout=60)
            if results.get('error'):
                results = {}
            return results
        except requests.exceptions.Timeout:
            self._log("Request to import remote library timed out", level='warning')
            return None
        except requests.exceptions.RequestException as e:
            self._log("Request to import remote library failed", message2=str(e), level='warning')
            return None
        except Exception as e:
            self._log("Failed to import remote library", message2=str(e), level='error')
        return {}


class RemoteTaskManager(threading.Thread):
    paused = False

    current_task = None
    worker_log = None
    start_time = None
    finish_time = None

    worker_subprocess_percent = None
    worker_subprocess_elapsed = None

    worker_runners_info = {}

    def __init__(self, thread_id, name, installation_info, pending_queue, complete_queue, event):
        super(RemoteTaskManager, self).__init__(name=name)
        self.thread_id = thread_id
        self.name = name
        self.event = event
        self.installation_info = installation_info
        self.pending_queue = pending_queue
        self.complete_queue = complete_queue

        self.links = Links()

        # Create 'redundancy' flag. When this is set, the worker should die
        self.redundant_flag = threading.Event()
        self.redundant_flag.clear()

        # Create 'paused' flag. When this is set, the worker should be paused
        self.paused_flag = threading.Event()
        self.paused_flag.clear()

        # Create logger for this worker
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(self.name)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def get_info(self):
        return {
            'name':              self.name,
            'installation_info': self.installation_info,
        }

    def run(self):
        # A manager should only run for a single task and connection to a single worker.
        # If either of these become unavailable, then the manager should exit
        self._log("Starting remote task manager {} - {}".format(self.thread_id, self.installation_info.get('address')))
        # Pull task
        try:
            # Pending task queue has an item available. Fetch it.
            next_task = self.pending_queue.get_nowait()

            # Configure worker for this task
            self.__set_current_task(next_task)

            # Process the set task
            self.__process_task_queue_item()

        except queue.Empty:
            self._log("Remote task manager started by the pending queue was empty", level="warning")
        except Exception as e:
            self._log("Exception in processing job with {}:".format(self.name), message2=str(e),
                      level="exception")

        self._log("Stopping remote task manager {} - {}".format(self.thread_id, self.installation_info.get('address')))

    def __set_current_task(self, current_task):
        """Sets the given task to the worker class"""
        self.current_task = current_task
        self.worker_log = []

    def __unset_current_task(self):
        self.current_task = None
        self.worker_runners_info = {}
        self.worker_log = []

    def __process_task_queue_item(self):
        """
        Processes the set task.

        :return:
        """
        # Set the progress to an empty string
        self.worker_subprocess_percent = ''
        self.worker_subprocess_elapsed = '0'

        # Log the start of the job
        self._log("Picked up job - {}".format(self.current_task.get_source_abspath()))

        # Mark as being "in progress"
        self.current_task.set_status('in_progress')

        # Start current task stats
        self.__set_start_task_stats()

        # Process the file. Will return true if success, otherwise false
        success = self.__send_task_to_remote_worker_and_monitor()
        # Mark the task as either success or not
        self.current_task.set_success(success)

        # Mark task completion statistics
        self.__set_finish_task_stats()

        # Log completion of job
        self._log("Finished job - {}".format(self.current_task.get_source_abspath()))

        # Place the task into the completed queue
        self.complete_queue.put(self.current_task)

        # Reset the current file info for the next task
        self.__unset_current_task()

    def __set_start_task_stats(self):
        """Sets the initial stats for the start of a task"""
        # Set the start time to now
        self.start_time = time.time()

        # Clear the finish time
        self.finish_time = None

        # Format our starting statistics data
        self.current_task.task.processed_by_worker = self.name
        self.current_task.task.start_time = self.start_time
        self.current_task.task.finish_time = self.finish_time

    def __set_finish_task_stats(self):
        """Sets the final stats for the end of a task"""
        # Set the finish time to now
        self.finish_time = time.time()

        # Set the finish time in the statistics data
        self.current_task.task.finish_time = self.finish_time

    def __write_failure_to_worker_log(self):
        # Append long entry to say the worker was terminated
        self.worker_log.append("\n\nREMOTE TASK FAILED!")
        self.worker_log.append("\nAn error occurred during one of these stages:")
        self.worker_log.append("\n    - while sending task to remote installation")
        self.worker_log.append("\n    - during the remote task processing")
        self.worker_log.append("\n    - while attempting to retrieve the completed task from the remote installation")
        self.worker_log.append("\nCheck Unmanic logs for more information.")
        self.worker_log.append("\nRelevant logs will be prefixed with 'ERROR:Unmanic.{}'".format(self.name))
        self.current_task.save_command_log(self.worker_log)

    def __send_task_to_remote_worker_and_monitor(self):
        """
        Sends the task file to the remote installation to process.
        Monitors progress and then fetches the results

        TODO: Manage network disconnections.
            - This manager object should be able to handle a network disconnect. However, we should terminate
            this manager if the remote task no longer exists.
            - Catch all API request exceptions.
            - Remove the failed_status_count - losing contact should be ok. What matters is when contact is made that
            the task still exists to be downloaded or status updated.

        :return:
        """
        # Set the absolute path to the original file
        original_abspath = self.current_task.get_source_abspath()

        # Ensure file exists
        if not os.path.exists(original_abspath):
            self._log("File no longer exists '{}'. Was it removed?".format(original_abspath), level='warning')
            self.__write_failure_to_worker_log()
            return False

        # Set the remote worker address
        address = self.installation_info.get('address')

        lock_key = None

        # Fetch the library name and path this task is for
        library_id = self.current_task.get_task_library_id()
        try:
            library = Library(library_id)
        except Exception as e:
            self._log("Unable to fetch library config for ID {}".format(library_id), level='exception')
            self.__write_failure_to_worker_log()
            return False
        library_name = library.get_name()
        library_path = library.get_path()

        # Check if we can create the remote task with just a relative path
        #   only create checksum and send file if the remote library path cannot accept relative paths or
        #   it is configured for only receiving remote files
        send_file = False
        library_config = self.links.get_the_remote_library_config_by_name(self.installation_info, library_name)

        # Check if remote library is configured only for receiving remote files
        if library_config.get('enable_remote_only'):
            send_file = True

        # First attempt to create a task with an abspath on the remote installation
        remote_task_id = None
        if not send_file:
            remote_library_id = library_config.get('id')

            # Remove library path from file abspath to create a relative path
            original_relpath = os.path.relpath(original_abspath, library_path)
            # Join remote library path to the relative path to form a remote library abspath to the file
            remote_original_abspath = os.path.join(library_config.get('path'), original_relpath)
            # Post the task creation. This will error if the file does not exist
            info = self.links.new_pending_task_create_on_remote_installation(self.installation_info,
                                                                             remote_original_abspath,
                                                                             remote_library_id)
            if not info:
                self._log("Unable to create remote pending task for path '{}'. Fallback to sending file.".format(
                    remote_original_abspath), level='debug')
                send_file = True
            elif 'path does not exist' in info.get('error', '').lower():
                self._log("Unable to find file in remote library's path '{}'. Fallback to sending file.".format(
                    remote_original_abspath), level='debug')
                send_file = True
            elif 'task already exists' in info.get('error', '').lower():
                self._log("A remote task already exists with the path '{}'. Fallback to sending file.".format(
                    remote_original_abspath), level='error')
                self.__write_failure_to_worker_log()
                return False

            # Set the remote task ID
            remote_task_id = info.get('id')

        if send_file:
            initial_checksum = None
            if self.installation_info.get('enable_checksum_validation', False):
                # Get source file checksum
                initial_checksum = common.get_file_checksum(original_abspath)
            initial_file_size = os.path.getsize(original_abspath)

            # Loop until we are able to upload the file to the remote installation
            info = {}
            while not self.redundant_flag.is_set():
                # For files smaller than 100MB, just transfer them in parallel
                # Smaller files add a lot of time overhead with the waiting in line and it slows the whole process down
                # Larger files benefit from being transferred one at a time.
                if initial_file_size > 100000000:
                    # Check for network transfer lock
                    lock_key = self.links.acquire_network_transfer_lock(address, transfer_limit=1, lock_type='send')
                    if not lock_key:
                        self.event.wait(1)
                        continue

                # Send a file to a remote installation.
                self._log("Uploading file to remote installation '{}'".format(original_abspath), level='debug')
                info = self.links.send_file_to_remote_installation(self.installation_info, original_abspath)
                self.links.release_network_transfer_lock(lock_key)
                if not info:
                    self._log("Failed to upload the file '{}'".format(original_abspath), level='error')
                    self.__write_failure_to_worker_log()
                    return False
                break

            # Set the remote task ID
            remote_task_id = info.get('id')

            # Compare uploaded file md5checksum
            if initial_checksum and info.get('checksum') != initial_checksum:
                self._log("The uploaded file did not return a correct checksum '{}'".format(original_abspath), level='error')
                # Send request to terminate the remote worker then return
                self.links.remove_task_from_remote_installation(self.installation_info, remote_task_id)
                self.__write_failure_to_worker_log()
                return False

        # Ensure at this point we have set the remote_task_id
        if remote_task_id is None:
            self._log("Failed to create remote task. Var remote_task_id is still None", level='error')
            self.__write_failure_to_worker_log()
            return False

        # Set the library of the remote task using the library's name
        while not self.redundant_flag.is_set():
            result = self.links.set_the_remote_task_library(self.installation_info, remote_task_id, library_name)
            if result is None:
                # Unable to reach remote installation
                self.event.wait(2)
                continue
            if not result.get('success'):
                self._log(
                    "Failed to match a remote library named '{}'. Remote installation will use the default library".format(
                        library_name), level='warning')
                # Just log the warning for this. If no matching library name is found it will remain set as the default library
                break
            if result.get('success'):
                break

        # Start the remote task
        while not self.redundant_flag.is_set():
            result = self.links.start_the_remote_task_by_id(self.installation_info, remote_task_id)
            if not result:
                # Unable to reach remote installation
                self.event.wait(2)
                continue
            if not result.get('success'):
                self._log("Failed to set initial remote pending task to status '{}'".format(original_abspath), level='error')
                # Send request to terminate the remote worker then return
                self.links.remove_task_from_remote_installation(self.installation_info, remote_task_id)
                self.__write_failure_to_worker_log()
                return False
            if result.get('success'):
                break

        # Loop while redundant_flag not set (while true because of below)
        worker_id = None
        task_status = ''
        last_status_fetch = 0
        polling_delay = 5
        while task_status != 'complete':
            self.event.wait(1)
            if self.redundant_flag.is_set():
                # Send request to terminate the remote worker then exit
                if worker_id:
                    self.links.terminate_remote_worker(self.installation_info, worker_id)
                break

            # Only fetch the status every 5 seconds
            time_now = time.time()
            if last_status_fetch > (time_now - polling_delay):
                continue

            # Fetch task status
            all_task_states = self.links.get_remote_pending_task_state(self.installation_info, remote_task_id)
            task_status = ''
            polling_delay = 5
            if all_task_states:
                for ts in all_task_states.get('results', []):
                    if str(ts.get('id')) == str(remote_task_id):
                        # Task is complete. Exit loop but do not set redundant flag on link manager
                        task_status = ts.get('status')
                        break
                if not all_task_states.get('results', []):
                    # Remote task list is empty
                    task_status = 'removed'
                elif all_task_states.get('results') and task_status == '':
                    # Remote task list did not contain this task
                    task_status = 'removed'

            # If the task status is 'complete', break the loop here and move onto the result retrieval
            # If all_task_states returned no results (we are unable to connect to the remote installation)
            # If all_task_states did return results but our task_status was found, the remote installation has removed our task
            # If the task status is not 'in_progress', loop here and wait for task to be picked up by a worker
            if task_status == 'complete':
                break
            elif not all_task_states:
                polling_delay = 10
                last_status_fetch = time_now
                continue
            elif task_status == 'removed':
                self._log("Task has been removed by remote installation '{}'".format(original_abspath), level='error')
                self.__write_failure_to_worker_log()
                return False
            elif task_status != 'in_progress':
                # Mark this as the last time run
                last_status_fetch = time_now
                polling_delay = 10
                continue

            # Check if we know the task's worker ID already
            if not worker_id:
                # The task has been picked up by a worker, find out which one...
                workers_status = self.links.get_all_worker_status(self.installation_info)
                if not workers_status:
                    # The request failed for some reason... Perhaps we lost contact with the remote installation
                    # Mark this as the last time run
                    last_status_fetch = time_now
                    continue
                for worker in workers_status:
                    if str(worker.get('current_task')) == str(remote_task_id):
                        worker_id = worker.get('id')

            # Fetch worker progress
            worker_status = self.links.get_single_worker_status(self.installation_info, worker_id)
            if not worker_status:
                # Mark this as the last time run
                last_status_fetch = time_now
                continue

            # Update status
            self.paused = worker_status.get('paused')
            self.worker_log = worker_status.get('worker_log_tail')
            self.worker_runners_info = worker_status.get('runners_info')
            self.worker_subprocess_percent = worker_status.get('subprocess', {}).get('percent')
            self.worker_subprocess_elapsed = worker_status.get('subprocess', {}).get('elapsed')

            # Mark this as the last time run
            last_status_fetch = time_now

        # If the previous loop was broken because this tread needs to terminate, return False here (did not complete)
        if self.redundant_flag.is_set():
            self.worker_log += ["\n\nREMOTE LINK MANAGER TERMINATED!"]
            self.current_task.save_command_log(self.worker_log)
            return False

        self._log("Remote task completed '{}'".format(original_abspath), level='info')

        # Create local cache path to download results
        task_cache_path = self.current_task.get_cache_path()
        # Ensure the cache directory exists
        cache_directory = os.path.dirname(os.path.abspath(task_cache_path))
        if not os.path.exists(cache_directory):
            os.makedirs(cache_directory)

        # Fetch remote task result data
        data = self.links.fetch_remote_task_data(self.installation_info, remote_task_id,
                                                 os.path.join(cache_directory, 'remote_data.json'))

        if not data:
            self._log(
                "Failed to retrieve remote task data for '{}'. NOTE: The cached files have not been removed from the remote host.".format(
                    original_abspath), level='error')
            self.__write_failure_to_worker_log()
            return False
        self.worker_log = [data.get('log')]

        # Save the completed command log
        self.current_task.save_command_log(self.worker_log)

        # Fetch remote task file
        if data.get('task_success'):
            task_label = data.get('task_label')
            self._log(
                "Remote task #{} was successful, proceeding to download the completed file '{}'".format(remote_task_id,
                                                                                                        task_label),
                level='debug')
            # Set the new file out as the extension may have changed
            split_file_name = os.path.splitext(data.get('abspath'))
            file_extension = split_file_name[1].lstrip('.')
            self.current_task.set_cache_path(cache_directory, file_extension)
            # Read the updated cache path
            task_cache_path = self.current_task.get_cache_path()

            # Loop until we are able to upload the file to the remote installation
            while not self.redundant_flag.is_set():
                # Check for network transfer lock
                lock_key = self.links.acquire_network_transfer_lock(address, transfer_limit=2, lock_type='receive')
                if not lock_key:
                    self.event.wait(1)
                    continue
                # Download the file
                self._log("Downloading file from remote installation '{}'".format(task_label), level='debug')
                success = self.links.fetch_remote_task_completed_file(self.installation_info, remote_task_id, task_cache_path)
                self.links.release_network_transfer_lock(lock_key)
                if not success:
                    self._log("Failed to download file '{}'".format(os.path.basename(data.get('abspath'))), level='error')
                    # Send request to terminate the remote worker then return
                    self.links.remove_task_from_remote_installation(self.installation_info, remote_task_id)
                    self.__write_failure_to_worker_log()
                    return False
                break

            # If the previous loop was broken because this tread needs to terminate, return False here (did not complete)
            if self.redundant_flag.is_set():
                self.worker_log += ["\n\nREMOTE LINK MANAGER TERMINATED!"]
                self.current_task.save_command_log(self.worker_log)
                return False

            # Match checksum from task result data with downloaded file
            if self.installation_info.get('enable_checksum_validation', False):
                downloaded_checksum = common.get_file_checksum(task_cache_path)
                if downloaded_checksum != data.get('checksum'):
                    self._log("The downloaded file did not produce a correct checksum '{}'".format(task_cache_path),
                              level='error')
                    # Send request to terminate the remote worker then return
                    self.links.remove_task_from_remote_installation(self.installation_info, remote_task_id)
                    self.__write_failure_to_worker_log()
                    return False

            # Send request to terminate the remote worker then return
            self.links.remove_task_from_remote_installation(self.installation_info, remote_task_id)

            return True

        self.__write_failure_to_worker_log()
        return False
