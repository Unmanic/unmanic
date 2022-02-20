#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.settings_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     20 Aug 2021, (2:30 PM)

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

import tornado.log

from unmanic import config
from unmanic.libs.installation_link import Links
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiError, BaseApiHandler
from unmanic.webserver.api_v2.schema.schemas import RequestLibraryByIdSchema, RequestRemoteInstallationLinkConfigSchema, \
    SettingsLibrariesListSchema, SettingsLibraryConfigReadAndWriteSchema, SettingsLibraryPluginConfigExportSchema, \
    SettingsReadAndWriteSchema, \
    SettingsRemoteInstallationDataSchema, \
    SettingsRemoteInstallationLinkConfigSchema, SettingsSystemConfigSchema, \
    RequestSettingsRemoteInstallationAddressValidationSchema
from unmanic.webserver.helpers import plugins


class ApiSettingsHandler(BaseApiHandler):
    config = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/settings/read",
            "supported_methods": ["GET"],
            "call_method":       "get_all_settings",
        },
        {
            "path_pattern":      r"/settings/write",
            "supported_methods": ["POST"],
            "call_method":       "write_settings",
        },
        {
            "path_pattern":      r"/settings/configuration",
            "supported_methods": ["GET"],
            "call_method":       "get_system_configuration",
        },
        {
            "path_pattern":      r"/settings/link/validate",
            "supported_methods": ["POST"],
            "call_method":       "validate_remote_installation",
        },
        {
            "path_pattern":      r"/settings/link/read",
            "supported_methods": ["POST"],
            "call_method":       "read_link_config",
        },
        {
            "path_pattern":      r"/settings/link/write",
            "supported_methods": ["POST"],
            "call_method":       "write_link_config",
        },
        {
            "path_pattern":      r"/settings/libraries",
            "supported_methods": ["GET"],
            "call_method":       "get_all_libraries",
        },
        {
            "path_pattern":      r"/settings/library/read",
            "supported_methods": ["POST"],
            "call_method":       "read_library_config",
        },
        {
            "path_pattern":      r"/settings/library/write",
            "supported_methods": ["POST"],
            "call_method":       "write_library_config",
        },
        {
            "path_pattern":      r"/settings/library/remove",
            "supported_methods": ["DELETE"],
            "call_method":       "remove_library",
        },
        {
            "path_pattern":      r"/settings/library/export",
            "supported_methods": ["POST"],
            "call_method":       "export_library_plugin_config",
        },
    ]

    def initialize(self, **kwargs):
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()
        self.config = config.Config()

    def get_all_settings(self):
        """
        Settings - read
        ---
        description: Returns the application settings.
        responses:
            200:
                description: 'Sample response: Returns the application settings.'
                content:
                    application/json:
                        schema:
                            SettingsReadAndWriteSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            settings = self.config.get_config_as_dict()
            response = self.build_response(
                SettingsReadAndWriteSchema(),
                {
                    "settings": settings,
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def write_settings(self):
        """
        Settings - save a dictionary of settings
        ---
        description: Save a given dictionary of settings.
        requestBody:
            description: Requested a dictionary of settings to save.
            required: True
            content:
                application/json:
                    schema:
                        SettingsReadAndWriteSchema
        responses:
            200:
                description: 'Successful request; Returns success status'
                content:
                    application/json:
                        schema:
                            BaseSuccessSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(SettingsReadAndWriteSchema())

            # Save settings - writing to file.
            # Throws exception if settings fail to save
            self.config.set_bulk_config_items(json_request.get('settings', {}))

            self.write_success()
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def get_system_configuration(self):
        """
        Settings - read the system configuration
        ---
        description: Returns the system configuration.
        responses:
            200:
                description: 'Sample response: Returns the system configuration.'
                content:
                    application/json:
                        schema:
                            SettingsSystemConfigSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            from unmanic.libs.system import System
            system = System()
            system_info = system.info()
            response = self.build_response(
                SettingsSystemConfigSchema(),
                {
                    "configuration": system_info,
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def validate_remote_installation(self):
        """
        Settings - validate a remote installation address
        ---
        description: Validate a remote installation address
        requestBody:
            description: The details of the remote installation to validate
            required: True
            content:
                application/json:
                    schema:
                        RequestSettingsRemoteInstallationAddressValidationSchema
        responses:
            200:
                description: 'Sample response: Returns the remote installation data.'
                content:
                    application/json:
                        schema:
                            SettingsRemoteInstallationDataSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestSettingsRemoteInstallationAddressValidationSchema())

            # Fetch all data from the remote installation
            # Throws exception if the provided address is invalid
            links = Links()
            data = links.validate_remote_installation(json_request.get('address'))

            response = self.build_response(
                SettingsRemoteInstallationDataSchema(),
                {
                    "installation": data,
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def read_link_config(self):
        """
        Settings - read the configuration of a remote installation link
        ---
        description: Read the configuration of a remote installation link
        requestBody:
            description: The UUID of the remote installation
            required: True
            content:
                application/json:
                    schema:
                        RequestRemoteInstallationLinkConfigSchema
        responses:
            200:
                description: 'Sample response: Returns the remote installation link configuration.'
                content:
                    application/json:
                        schema:
                            SettingsRemoteInstallationLinkConfigSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestRemoteInstallationLinkConfigSchema())

            # Fetch all data from the remote installation
            # Throws exception if the provided address is invalid
            links = Links()
            data = links.read_remote_installation_link_config(json_request.get('uuid'))

            response = self.build_response(
                SettingsRemoteInstallationLinkConfigSchema(),
                {
                    "link_config":                     {
                        "address":                         data.get('address'),
                        "available":                       data.get('available', False),
                        "name":                            data.get('name'),
                        "version":                         data.get('version'),
                        "last_updated":                    data.get('last_updated', 1),
                        "enable_receiving_tasks":          data.get('enable_receiving_tasks'),
                        "enable_sending_tasks":            data.get('enable_sending_tasks'),
                        "enable_task_preloading":          data.get('enable_task_preloading'),
                        "enable_distributed_worker_count": data.get('enable_distributed_worker_count', False),
                    },
                    "distributed_worker_count_target": data.get('distributed_worker_count_target', 0),
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def write_link_config(self):
        """
        Settings - write the configuration of a remote installation link
        ---
        description: Write the configuration of a remote installation link
        requestBody:
            description: The UUID of the remote installation and its configuration
            required: True
            content:
                application/json:
                    schema:
                        SettingsRemoteInstallationLinkConfigSchema
        responses:
            200:
                description: 'Successful request; Returns success status'
                content:
                    application/json:
                        schema:
                            BaseSuccessSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(SettingsRemoteInstallationLinkConfigSchema())

            # Update a single remote installation config by matching the UUID
            links = Links()
            links.update_single_remote_installation_link_config(json_request.get('link_config'),
                                                                json_request.get('distributed_worker_count_target', 0))

            self.write_success()
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def get_all_libraries(self):
        """
        Settings - get list of all libraries
        ---
        description: Returns a list of all libraries.
        responses:
            200:
                description: 'Sample response: Returns a list of all libraries.'
                content:
                    application/json:
                        schema:
                            SettingsLibrariesListSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            from unmanic.libs.library import Library
            libraries = Library.get_all_libraries()
            response = self.build_response(
                SettingsLibrariesListSchema(),
                {
                    "libraries": libraries,
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def read_library_config(self):
        """
        Settings - read the configuration of one library
        ---
        description: Read the configuration of one library
        requestBody:
            description: The ID of the library
            required: True
            content:
                application/json:
                    schema:
                        RequestLibraryByIdSchema
        responses:
            200:
                description: 'Sample response: Returns the remote installation link configuration.'
                content:
                    application/json:
                        schema:
                            SettingsLibraryConfigReadAndWriteSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestLibraryByIdSchema())

            library_settings = {
                "library_config": {
                    "id":             0,
                    "name":           '',
                    "path":           '/',
                    "enable_scanner": False,
                    "enable_inotify": False,
                },
                "plugins":        {
                    "enabled_plugins": [],
                }
            }
            if json_request.get('id'):
                # Read the library
                from unmanic.libs.library import Library
                library_config = Library(json_request.get('id'))
                library_settings = {
                    "library_config": {
                        "id":             library_config.get_id(),
                        "name":           library_config.get_name(),
                        "path":           library_config.get_path(),
                        "enable_scanner": library_config.get_enable_scanner(),
                        "enable_inotify": library_config.get_enable_inotify(),
                    },
                    "plugins":        {
                        "enabled_plugins": library_config.get_enabled_plugins(),
                    }
                }

            response = self.build_response(
                SettingsLibraryConfigReadAndWriteSchema(),
                library_settings
            )

            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def write_library_config(self):
        """
        Settings - write the configuration of one library
        ---
        description: Write the configuration of one library
        requestBody:
            description: Requested a dictionary of settings to save.
            required: True
            content:
                application/json:
                    schema:
                        SettingsLibraryConfigReadAndWriteSchema
        responses:
            200:
                description: 'Successful request; Returns success status'
                content:
                    application/json:
                        schema:
                            BaseSuccessSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            from unmanic.libs.library import Library
            json_request = self.read_json_request(SettingsLibraryConfigReadAndWriteSchema())

            # Parse library config
            library_config = json_request['library_config']

            # Check if this save requires a new library entry
            library_id = library_config.get('id', 0)
            if int(library_id) > 0:
                # Fetch existing library by ID
                library = Library(library_id)
            else:
                # Create a new library
                library = Library.create(library_config)

            # Update library config
            library.set_name(library_config.get('name', library.get_name()))
            library.set_path(library_config.get('path', library.get_path()))
            library.set_enable_scanner(library_config.get('enable_scanner', library.get_enable_scanner()))
            library.set_enable_inotify(library_config.get('enable_inotify', library.get_enable_inotify()))

            # Parse plugin config
            plugin_config = json_request.get('plugins', {})
            if library_config is not None:
                # Update enabled plugins (if provided)
                enabled_plugins = plugin_config.get('enabled_plugins')
                if enabled_plugins is not None:
                    library.set_enabled_plugins(enabled_plugins)

                # TODO: Update plugin flow

            # Save config
            library.save()

            self.write_success()
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def remove_library(self):
        """
        Plugins - remove
        ---
        description: Remove a library
        requestBody:
            description: Requested a library to remove.
            required: True
            content:
                application/json:
                    schema:
                        RequestLibraryByIdSchema
        responses:
            200:
                description: 'Successful request; Returns success status'
                content:
                    application/json:
                        schema:
                            BaseSuccessSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            from unmanic.libs.library import Library
            json_request = self.read_json_request(RequestLibraryByIdSchema())

            # Fetch existing library by ID
            library = Library(json_request.get('id'))

            # Delete the library
            if not library.delete():
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to remove library by its ID")
                self.write_error()
                return

            self.write_success()
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    def export_library_plugin_config(self):
        """
        Settings - export the plugin configuration of one library
        ---
        description: Export the plugin configuration of one library
        requestBody:
            description: The ID of the library
            required: True
            content:
                application/json:
                    schema:
                        RequestLibraryByIdSchema
        responses:
            200:
                description: 'Sample response: Returns the remote installation link configuration.'
                content:
                    application/json:
                        schema:
                            SettingsLibraryPluginConfigExportSchema
            400:
                description: Bad request; Check `messages` for any validation errors
                content:
                    application/json:
                        schema:
                            BadRequestSchema
            404:
                description: Bad request; Requested endpoint not found
                content:
                    application/json:
                        schema:
                            BadEndpointSchema
            405:
                description: Bad request; Requested method is not allowed
                content:
                    application/json:
                        schema:
                            BadMethodSchema
            500:
                description: Internal error; Check `error` for exception
                content:
                    application/json:
                        schema:
                            InternalErrorSchema
        """
        try:
            json_request = self.read_json_request(RequestLibraryByIdSchema())

            # Read the library
            from unmanic.libs.library import Library
            library_config = Library(json_request.get('id'))

            # Get list of enabled plugins with their settings
            enabled_plugins = []
            for enabled_plugin in library_config.get_enabled_plugins(include_settings=True):
                enabled_plugins.append({
                    'plugin_id': enabled_plugin.get('plugin_id'),
                    'settings':  enabled_plugin.get('settings'),
                })

            # Create plugin flow
            plugin_flow = {}
            for plugin_type in plugins.get_plugin_types_with_flows():
                plugin_flow[plugin_type] = []
                flow = plugins.get_enabled_plugin_flows_for_plugin_type(plugin_type, json_request.get('id'))
                for f in flow:
                    plugin_flow[plugin_type].append(f.get('plugin_id'))

            plugin_settings = {
                "plugins": {
                    "enabled_plugins": enabled_plugins,
                    "plugin_flow":     plugin_flow,
                },
            }

            response = self.build_response(
                SettingsLibraryPluginConfigExportSchema(),
                plugin_settings
            )

            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
