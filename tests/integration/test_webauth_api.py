#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import json
import tempfile

import pytest
import requests

from tests.support_.webauth_db import create_test_database, destroy_test_database
from tests.support_.webauth_server import BackgroundServer
from unmanic import config
from unmanic.libs.uiserver import UnmanicWebApplication
from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials
from unmanic.libs.unmodels.webauthsessions import WebAuthSessions
from unmanic.libs.webauth import credentials, sessions
from unmanic.webserver.api_v2.auth_api import ApiAuthHandler

MODELS = [WebAuthCredentials, WebAuthSessions]


@pytest.mark.integrationtest
class TestAuthApi(object):
    def setup_method(self):
        self.db = create_test_database(MODELS)
        config.Config._instances = {}
        self.settings = config.Config(config_path=tempfile.mkdtemp(prefix="unmanic_tests_"))
        credentials.flush_verify_cache()
        # State the starting condition rather than inheriting it: a fresh config directory
        # now defaults to authentication enabled.
        self.settings.set_config_item("auth_enabled", False, save_settings=False)
        self.server = BackgroundServer(
            lambda: UnmanicWebApplication([(r"/unmanic/api/v2/auth/(.*)", ApiAuthHandler)])
        )
        self.base_url = self.server.start()

    def teardown_method(self):
        self.server.stop()
        destroy_test_database(self.db, MODELS)

    def _cookies(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        return {sessions.COOKIE_NAME: token}

    def _get(self, path, **kwargs):
        kwargs.setdefault("timeout", 10)
        kwargs.setdefault("allow_redirects", False)
        return requests.get(self.base_url + path, **kwargs)

    def _post(self, path, payload, **kwargs):
        kwargs.setdefault("timeout", 10)
        kwargs.setdefault("allow_redirects", False)
        return requests.post(self.base_url + path, data=json.dumps(payload), **kwargs)

    def test_state_reports_when_authentication_is_disabled(self):
        response = self._get("/unmanic/api/v2/auth/state")
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_configure_can_enable_auth_while_it_is_off(self):
        response = self._post(
            "/unmanic/api/v2/auth/configure",
            {"enabled": True, "username": "jordan", "password": "a-good-password"},
        )
        assert response.status_code == 200
        assert self.settings.get_auth_enabled() is True
        assert credentials.verify_credential("jordan", "a-good-password") is True

    def test_configure_rejects_a_short_password(self):
        response = self._post(
            "/unmanic/api/v2/auth/configure",
            {"enabled": True, "username": "jordan", "password": "short"},
        )
        assert response.status_code == 400

    def test_configure_rejects_enabling_with_no_password_at_all(self):
        response = self._post("/unmanic/api/v2/auth/configure", {"enabled": True})
        assert response.status_code == 400
        assert self.settings.get_auth_enabled() is False

    def test_state_never_returns_the_password_hash(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        response = self._get("/unmanic/api/v2/auth/state", cookies=self._cookies())
        assert response.status_code == 200
        assert "password_hash" not in response.text
        assert "scrypt" not in response.text

    def test_password_change_requires_the_current_password(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        response = self._post(
            "/unmanic/api/v2/auth/password",
            {"current_password": "wrong-password", "new_password": "another-good-password"},
            cookies=self._cookies(),
        )
        assert response.status_code == 400
        assert credentials.verify_credential("jordan", "a-good-password") is True

    def test_password_change_revokes_other_sessions_but_keeps_the_caller_signed_in(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        sessions.create_session("10.0.0.2", "other-browser", 7, 30)
        response = self._post(
            "/unmanic/api/v2/auth/password",
            {"current_password": "a-good-password", "new_password": "another-good-password"},
            cookies=self._cookies(),
        )
        assert response.status_code == 200
        assert WebAuthSessions.select().count() == 1
        assert sessions.COOKIE_NAME in response.headers.get("Set-Cookie")

    def test_sessions_can_be_listed_and_revoked(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        sessions.create_session("10.0.0.2", "other-browser", 7, 30)
        cookies = self._cookies()
        listed = self._get("/unmanic/api/v2/auth/sessions", cookies=cookies).json()
        assert len(listed["sessions"]) == 2
        response = self._post("/unmanic/api/v2/auth/sessions/revoke", {"all": True}, cookies=cookies)
        assert response.status_code == 200
        assert WebAuthSessions.select().count() == 0

    def test_revoke_requires_an_id_or_all(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        response = self._post("/unmanic/api/v2/auth/sessions/revoke", {}, cookies=self._cookies())
        assert response.status_code == 400

    def test_endpoints_require_authentication_once_enabled(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        assert self._get("/unmanic/api/v2/auth/state").status_code == 401

    def test_disabling_auth_revokes_every_session(self):
        credentials.set_credential("jordan", "a-good-password")
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        cookies = self._cookies()
        response = self._post("/unmanic/api/v2/auth/configure", {"enabled": False}, cookies=cookies)
        assert response.status_code == 200
        assert self.settings.get_auth_enabled() is False
        assert WebAuthSessions.select().count() == 0
