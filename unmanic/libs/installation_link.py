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
import time

import requests
from urllib3.exceptions import MaxRetryError, NewConnectionError

from unmanic import config
from unmanic.libs import common, session, unlogger
from unmanic.libs.singleton import SingletonType


class Links(object, metaclass=SingletonType):

    def __init__(self, *args, **kwargs):
        self.settings = config.Config()
        self.session = session.Session()
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __format_address(self, address: str):
        address = address.strip()
        if not address.lower().startswith('http'):
            address = "http://{}".format(address)
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
            "address":                config_dict.get('address', '???'),
            "enable_receiving_tasks": config_dict.get('enable_receiving_tasks', False),
            "enable_sending_tasks":   config_dict.get('enable_sending_tasks', False),
            "name":                   config_dict.get('name', '???'),
            "version":                config_dict.get('version', '???'),
            "uuid":                   config_dict.get('uuid', '???'),
            "available":              config_dict.get('available', False),
            "last_updated":           config_dict.get('last_updated', time.time()),
        }

    def validate_remote_installation(self, address: str):
        """
        Validate a remote Unmanic installation by requesting
        its system info and version

        :param address:
        :return:
        """
        address = self.__format_address(address)

        # Fetch config
        url = "{}/unmanic/api/v2/settings/configuration".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        system_configuration_data = res.json()

        # Fetch settings
        url = "{}/unmanic/api/v2/settings/read".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        settings_data = res.json()

        # Fetch version
        url = "{}/unmanic/api/v2/version/read".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        version_data = res.json()

        # Fetch version
        url = "{}/unmanic/api/v2/session/state".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        session_data = res.json()

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
        }

    def update_all_remote_installation_links(self):
        """
        Updates the link status and configuration of linked remote installations

        :return:
        """
        save_settings = False
        installation_id_list = []
        remote_installations = []
        for local_config in self.settings.get_remote_installations():
            # Ensure address is not added twice by comparing installation IDs
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
                installation_data = self.validate_remote_installation(local_config.get('address'))
            except Exception:
                pass

            # Generate updated configured values
            updated_config = self.__generate_default_config(local_config)
            updated_config["available"] = False
            if installation_data:
                # Mark the installation as available
                updated_config["available"] = True

                merge_dict = {
                    "name":    installation_data.get('settings', {}).get('installation_name'),
                    "version": installation_data.get('version'),
                    "uuid":    installation_data.get('session', {}).get('uuid'),
                }
                self.__merge_config_dicts(updated_config, merge_dict)

                # Fetch the corresponding remote configuration for this local installation
                remote_config = self.fetch_remote_installation_link_config_for_this(local_config.get('address'))

                # If the remote configuration is newer than this one, use those values
                # The remote installation will do the same and this will synchronise
                if local_config.get('last_updated', 1) < remote_config.get('last_updated', 1):
                    # Note that the configuration options are reversed when reading from the remote installation config
                    updated_config["enable_receiving_tasks"] = remote_config.get('enable_sending_tasks')
                    updated_config["enable_sending_tasks"] = remote_config.get('enable_receiving_tasks')
                    # Also sync the last_updated flag
                    updated_config['last_updated'] = remote_config.get('last_updated')

                # If the remote config is unable to contact this installation (or it does not have a corresponding config yet)
                #   then also push the configuration
                if not remote_config.get('available'):
                    self.push_remote_installation_link_config(updated_config)

            # Only save to file if the settings have been updated
            if updated_config.get('last_updated') == local_config.get('last_updated'):
                save_settings = True
            remote_installations.append(updated_config)

            # Add UUID to list for next loop
            installation_id_list.append(updated_config.get('uuid', '???'))

        # Update installation data. Only save the config to disk if it was modified
        self.settings.set_config_item('remote_installations', remote_installations, save_settings=save_settings)

        return remote_installations

    def read_remote_installation_link_config(self, uuid):
        """
        Returns the configuration of the remote installation

        :return:
        """
        for remote_installation in self.settings.get_remote_installations():
            if remote_installation.get('uuid') == uuid:
                return remote_installation

        # Ensure we have settings data from the remote installation
        raise Exception("Unable to read installation link configuration.")

    def update_single_remote_installation_link_config(self, configuration: dict):
        """
        Returns the configuration of the remote installation

        :param configuration:
        :return:
        """
        uuid = configuration.get('uuid')
        if not uuid:
            raise Exception("Updating a single installation link configuration requires a UUID.")

        config_exists = False
        remote_installations = []
        for local_config in self.settings.get_remote_installations():
            updated_config = self.__generate_default_config(local_config)

            # If this is the uuid in the config provided, then update our config with the provided values
            if local_config.get('uuid') == uuid:
                config_exists = True
                self.__merge_config_dicts(updated_config, configuration)

            remote_installations.append(updated_config)

        # If the config does not yet exist, the add it now
        if not config_exists:
            remote_installations.append(self.__generate_default_config(configuration))

        # Update installation data and save the config to disk
        self.settings.set_config_item('remote_installations', remote_installations, save_settings=True)

    def fetch_remote_installation_link_config_for_this(self, address: str):
        """
        Fetches and returns the corresponding link configuration from a remote installation

        :param address:
        :return:
        """
        address = self.__format_address(address)
        url = "{}/unmanic/api/v2/settings/link/read".format(address)
        data = {
            "uuid": self.session.uuid
        }
        res = requests.post(url, json=data, timeout=2)
        if res.status_code == 200:
            data = res.json()
            return data.get('link_config')
        return {}

    def push_remote_installation_link_config(self, configuration: dict):
        """
        Pushes the given link config to the remote installation returns the corresponding link configuration from a remote installation

        :param configuration:
        :return:
        """
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

        # Remove some of the other fields. These will need to be adjusted on the remote instance manually
        del updated_config['address']
        del updated_config['available']

        data = {'link_config': updated_config}
        res = requests.post(url, json=data, timeout=2)
        if res.status_code == 200:
            return True
        return False
