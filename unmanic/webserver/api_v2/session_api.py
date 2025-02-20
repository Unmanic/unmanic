#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.session_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Mar 2021, (7:14 PM)

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
from tornado.ioloop import IOLoop

from unmanic.libs import session
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.uiserver import UnmanicDataQueues
from unmanic.webserver.api_v2.base_api_handler import BaseApiHandler, BaseApiError
from unmanic.webserver.api_v2.schema.schemas import SessionAuthCodeSchema, SessionStateSuccessSchema


class ApiSessionHandler(BaseApiHandler):
    session = None
    config = None
    logger = None
    params = None
    unmanic_data_queues = None

    routes = [
        {
            "path_pattern":      r"/session/state",
            "supported_methods": ["GET"],
            "call_method":       "get_session_state",
        },
        {
            "path_pattern":      r"/session/reload",
            "supported_methods": ["POST"],
            "call_method":       "session_reload",
        },
        {
            "path_pattern":      r"/session/logout",
            "supported_methods": ["GET"],
            "call_method":       "session_logout",
        },
        {
            "path_pattern":      r"/session/get_app_auth_code",
            "supported_methods": ["GET"],
            "call_method":       "get_app_auth_code",
        },
    ]

    def initialize(self, **kwargs):
        self.session = session.Session()
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self.params = kwargs.get("params")
        udq = UnmanicDataQueues()
        self.unmanic_data_queues = udq.get_unmanic_data_queues()

    async def get_session_state(self):
        """
        Session - state
        ---
        description: Returns the application session state.
        responses:
            200:
                description: 'Sample response: Returns the application session state.'
                content:
                    application/json:
                        schema:
                            SessionStateSuccessSchema
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
            if not self.session.created:
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Session has not yet been created.")
                self.write_error()
                return
            else:
                response = self.build_response(
                    SessionStateSuccessSchema(),
                    {
                        "level":       self.session.level,
                        "picture_uri": self.session.picture_uri,
                        "name":        self.session.name,
                        "email":       self.session.email,
                        "created":     self.session.created,
                        "uuid":        self.session.uuid,
                    }
                )
                self.write_success(response)
                return
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get('call_method'), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def session_reload(self):
        """
        Session - reload
        ---
        description: Reload the current session.
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
            if not self.session.register_unmanic(force=True):
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to reload session")
                self.write_error()
                return
            else:
                self.write_success()
                return
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get('call_method'), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def session_logout(self):
        """
        Session - log out of session
        ---
        description: Log out of the current session. Remove all session cookies and unlink installation from user account.
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
            if not self.session.sign_out():
                self.set_status(self.STATUS_ERROR_INTERNAL, reason="Failed to log out of session")
                self.write_error()
                return
            else:
                self.write_success()
                return
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get('call_method'), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def get_app_auth_code(self):
        """
        Session - state
        ---
        description: Initiates the device authentication flow.
        responses:
            200:
                description: 'Sample response: Initiates the device authentication flow.'
                content:
                    application/json:
                        schema:
                            SessionAuthCodeSchema
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
            current_loop = IOLoop.current()

            # Run the synchronous init_device_auth_flow in a thread so we don't block the IOLoop.
            device_auth_data = await current_loop.run_in_executor(None, self.session.init_device_auth_flow)
            if not device_auth_data:
                raise Exception("Failed to initiate device authentication flow.")

            user_code = device_auth_data.get("user_code")
            device_code = device_auth_data.get("device_code")
            verification_uri = device_auth_data.get("verification_uri")
            verification_uri_complete = device_auth_data.get("verification_uri_complete")
            interval = device_auth_data.get("interval")
            expires_in = device_auth_data.get("expires_in")

            # Use the existing Tornado loop to run the blocking polling function in the background.
            if self.session.token_poll_task is not None and not self.session.token_poll_task.done():
                self.logger.info("Cancelling the running poll task and starting a new one.")
                self.session.token_poll_task.cancel()
            self.session.token_poll_task = current_loop.run_in_executor(
                None,
                self.session.poll_for_app_token,
                device_code,
                interval,
                expires_in
            )

            response = self.build_response(
                SessionAuthCodeSchema(),
                {
                    "user_code":                 user_code,
                    "device_code":               device_code,
                    "verification_uri":          verification_uri,
                    "verification_uri_complete": verification_uri_complete,
                    "expires_in":                expires_in,
                }
            )
            self.write_success(response)
            return

        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
