#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import tempfile

import pytest
import requests
import tornado.web

from tests.support_.webauth_db import create_test_database, destroy_test_database
from tests.support_.webauth_server import BackgroundServer
from unmanic import config
from unmanic.libs.uiserver import UnmanicWebApplication
from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials
from unmanic.libs.unmodels.webauthsessions import WebAuthSessions
from unmanic.libs.webauth import credentials, sessions
from unmanic.libs.webauth.throttle import login_throttle
from unmanic.webserver.webauth import LoginActionHandler, LoginPageHandler, LogoutActionHandler

MODELS = [WebAuthCredentials, WebAuthSessions]


class EchoHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        self.write("ok")


@pytest.mark.integrationtest
class TestLoginFlow(object):
    def setup_method(self):
        self.db = create_test_database(MODELS)
        config.Config._instances = {}
        self.settings = config.Config(config_path=tempfile.mkdtemp(prefix="unmanic_tests_"))
        credentials.flush_verify_cache()
        login_throttle.record_success("login:127.0.0.1")
        self.server = BackgroundServer(
            lambda: UnmanicWebApplication([
                (r"/unmanic/login", LoginPageHandler),
                (r"/unmanic/auth/login", LoginActionHandler),
                (r"/unmanic/auth/logout", LogoutActionHandler),
                (r"/(.*)", EchoHandler),
            ])
        )
        self.base_url = self.server.start()
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        credentials.set_credential("jordan", "a-good-password")

    def teardown_method(self):
        self.server.stop()
        destroy_test_database(self.db, MODELS)
        login_throttle.record_success("login:127.0.0.1")

    def _login(self, username="jordan", password="a-good-password", next_path=None):
        body = {"username": username, "password": password}
        if next_path is not None:
            body["next"] = next_path
        return requests.post(
            self.base_url + "/unmanic/auth/login",
            data=body,
            allow_redirects=False,
            timeout=10,
        )

    def test_login_page_is_reachable_without_credentials(self):
        response = requests.get(self.base_url + "/unmanic/login", timeout=10)
        assert response.status_code == 200
        assert "password" in response.text.lower()

    def test_login_page_is_self_contained(self):
        # No external assets, or the guard allowlist would need to open static paths up.
        body = requests.get(self.base_url + "/unmanic/login", timeout=10).text
        assert "<script src=" not in body
        assert '<link rel="stylesheet"' not in body
        assert "<img" not in body

    def test_successful_login_sets_a_session_cookie_and_redirects(self):
        response = self._login()
        assert response.status_code == 302
        assert response.headers["Location"] == "/unmanic/ui/dashboard/"
        cookie = response.headers.get("Set-Cookie")
        assert sessions.COOKIE_NAME in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=Lax" in cookie

    def test_secure_flag_is_absent_without_tls(self):
        assert "Secure" not in self._login().headers.get("Set-Cookie")

    def test_secure_flag_is_present_with_tls(self):
        self.settings.set_config_item("ssl_enabled", True, save_settings=False)
        assert "Secure" in self._login().headers.get("Set-Cookie")

    def test_the_session_cookie_grants_access(self):
        token = self._login().cookies[sessions.COOKIE_NAME]
        response = requests.get(
            self.base_url + "/unmanic/api/v2/version/read",
            cookies={sessions.COOKIE_NAME: token},
            allow_redirects=False,
            timeout=10,
        )
        assert response.status_code == 200

    def test_bad_credentials_do_not_set_a_cookie(self):
        response = self._login(password="wrong-password")
        assert response.status_code == 401
        assert sessions.COOKIE_NAME not in (response.headers.get("Set-Cookie") or "")

    def test_the_error_message_does_not_reveal_which_field_was_wrong(self):
        wrong_password = self._login(password="wrong-password").text
        wrong_user = self._login(username="nobody").text
        assert wrong_password == wrong_user

    def test_next_is_honoured_when_local(self):
        response = self._login(next_path="/unmanic/ui/settings/")
        assert response.headers["Location"] == "/unmanic/ui/settings/"

    def test_next_cannot_redirect_off_site(self):
        response = self._login(next_path="https://evil.example.com")
        assert response.headers["Location"] == "/unmanic/ui/dashboard/"

    def test_logout_revokes_the_session(self):
        token = self._login().cookies[sessions.COOKIE_NAME]
        response = requests.post(
            self.base_url + "/unmanic/auth/logout",
            cookies={sessions.COOKIE_NAME: token},
            allow_redirects=False,
            timeout=10,
        )
        assert response.status_code == 302
        assert WebAuthSessions.select().count() == 0
        after = requests.get(
            self.base_url + "/unmanic/api/v2/version/read",
            cookies={sessions.COOKIE_NAME: token},
            allow_redirects=False,
            timeout=10,
        )
        assert after.status_code == 401

    def test_logout_is_not_reachable_by_get(self):
        token = self._login().cookies[sessions.COOKIE_NAME]
        response = requests.get(
            self.base_url + "/unmanic/auth/logout",
            cookies={sessions.COOKIE_NAME: token},
            allow_redirects=False,
            timeout=10,
        )
        assert response.status_code == 405

    def test_repeated_failures_are_throttled(self):
        last = None
        for _ in range(8):
            last = self._login(password="wrong-password")
        assert last.status_code == 429
        assert last.headers.get("Retry-After") is not None
