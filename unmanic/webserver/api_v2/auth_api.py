#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

from unmanic import config
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.webauth import credentials, guard, sessions
from unmanic.webserver.api_v2.base_api_handler import BaseApiError, BaseApiHandler
from unmanic.webserver.api_v2.schema.schemas import (
    AuthSessionsSuccessSchema,
    AuthStateSuccessSchema,
    RequestAuthConfigureSchema,
    RequestAuthPasswordSchema,
    RequestAuthSessionRevokeSchema,
)


class ApiAuthHandler(BaseApiHandler):
    """
    ApiAuthHandler

    Manage the local web account.

    Unrelated to ApiSessionHandler, which manages the unmanic.app supporter account used
    to unlock features.
    """

    config = None
    params = None
    logger = None

    routes = [
        {
            "path_pattern": r"/auth/state",
            "supported_methods": ["GET"],
            "call_method": "get_auth_state",
        },
        {
            "path_pattern": r"/auth/configure",
            "supported_methods": ["POST"],
            "call_method": "configure_auth",
        },
        {
            "path_pattern": r"/auth/password",
            "supported_methods": ["POST"],
            "call_method": "change_password",
        },
        {
            "path_pattern": r"/auth/sessions",
            "supported_methods": ["GET"],
            "call_method": "list_auth_sessions",
        },
        {
            "path_pattern": r"/auth/sessions/revoke",
            "supported_methods": ["POST"],
            "call_method": "revoke_auth_sessions",
        },
    ]

    def initialize(self, **kwargs):
        self.params = kwargs.get("params")
        self.config = config.Config()
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)

    def __current_token(self):
        cookie = self.request.cookies.get(sessions.COOKIE_NAME)
        return getattr(cookie, "value", None) if cookie is not None else None

    async def get_auth_state(self):
        """
        Auth - read the current authentication state
        ---
        description: Returns whether authentication is enabled and whether this request is authenticated.
        responses:
            200:
                description: 'Sample response: Returns the authentication state.'
                content:
                    application/json:
                        schema:
                            AuthStateSuccessSchema
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
            response = self.build_response(
                AuthStateSuccessSchema(),
                {
                    "enabled": self.config.get_auth_enabled(),
                    "authenticated": guard.session_from_request(self.request) is not None,
                    "username": credentials.get_username(),
                    "allow_basic": self.config.get_auth_allow_basic(),
                },
            )
            self.write_success(response)
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get("call_method"), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def configure_auth(self):
        """
        Auth - enable or disable authentication
        ---
        description: Enable or disable authentication and set the account credentials.
        requestBody:
            description: Requested authentication configuration.
            required: True
            content:
                application/json:
                    schema:
                        RequestAuthConfigureSchema
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
            json_request = self.read_json_request(RequestAuthConfigureSchema())
            enabled = bool(json_request.get("enabled"))

            if enabled:
                username = json_request.get("username") or credentials.get_username()
                password = json_request.get("password")
                if password:
                    try:
                        credentials.set_credential(username, password)
                    except ValueError as e:
                        self.set_status(self.STATUS_ERROR_EXTERNAL, reason=str(e))
                        self.write_error()
                        return
                elif not credentials.credential_is_configured():
                    self.set_status(
                        self.STATUS_ERROR_EXTERNAL, reason="A password is required to enable authentication"
                    )
                    self.write_error()
                    return
            else:
                sessions.revoke_all_sessions()

            self.config.set_config_item("auth_enabled", enabled, save_settings=True)
            self.logger.info("Web authentication %s via API", "enabled" if enabled else "disabled")
            self.write_success()
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get("call_method"), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def change_password(self):
        """
        Auth - change the account password
        ---
        description: Change the account password. Revokes every existing session.
        requestBody:
            description: Requested password change.
            required: True
            content:
                application/json:
                    schema:
                        RequestAuthPasswordSchema
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
            json_request = self.read_json_request(RequestAuthPasswordSchema())
            username = credentials.get_username()
            if not credentials.verify_credential(username, json_request.get("current_password")):
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Current password is incorrect")
                self.write_error()
                return
            try:
                credentials.set_credential(username, json_request.get("new_password"))
            except ValueError as e:
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason=str(e))
                self.write_error()
                return

            # Every session is revoked, then the caller is issued a fresh one so that
            # changing a password does not sign the person making the change out.
            from unmanic.webserver.webauth import set_session_cookie

            sessions.revoke_all_sessions()
            token = sessions.create_session(
                self.request.remote_ip,
                self.request.headers.get("User-Agent"),
                self.config.get_auth_session_idle_timeout_days(),
                self.config.get_auth_session_max_age_days(),
            )
            set_session_cookie(self, token, self.config.get_auth_session_max_age_days())
            self.logger.info("Web authentication password changed")
            self.write_success()
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get("call_method"), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def list_auth_sessions(self):
        """
        Auth - list the live sessions
        ---
        description: Returns the live browser sessions for this installation.
        responses:
            200:
                description: 'Sample response: Returns the live sessions.'
                content:
                    application/json:
                        schema:
                            AuthSessionsSuccessSchema
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
            response = self.build_response(
                AuthSessionsSuccessSchema(),
                {"sessions": sessions.list_sessions(self.__current_token())},
            )
            self.write_success(response)
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get("call_method"), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def revoke_auth_sessions(self):
        """
        Auth - revoke sessions
        ---
        description: Revoke a single session by id, or every session.
        requestBody:
            description: Requested session revocation.
            required: True
            content:
                application/json:
                    schema:
                        RequestAuthSessionRevokeSchema
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
            json_request = self.read_json_request(RequestAuthSessionRevokeSchema())
            if json_request.get("all"):
                sessions.revoke_all_sessions()
            elif json_request.get("id"):
                sessions.revoke_session_by_id(int(json_request.get("id")))
            else:
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Either 'id' or 'all' is required")
                self.write_error()
                return
            self.write_success()
        except BaseApiError as bae:
            self.logger.error("BaseApiError.%s: %s", self.route.get("call_method"), str(bae))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
