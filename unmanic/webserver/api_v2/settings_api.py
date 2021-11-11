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
from unmanic.webserver.api_v2.schema.schemas import RequestRemoteInstallationLinkConfigSchema, \
    SettingsReadAndWriteSchema, SettingsRemoteInstallationDataSchema, \
    SettingsRemoteInstallationLinkConfigSchema, SettingsSystemConfigSchema, \
    RequestSettingsRemoteInstallationAddressValidationSchema


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
