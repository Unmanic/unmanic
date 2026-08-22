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
from unmanic.webserver.webauth import SetupActionHandler, SetupPageHandler

MODELS = [WebAuthCredentials, WebAuthSessions]


class EchoHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        self.write("ok")


@pytest.mark.integrationtest
class TestSetupFlow(object):
    def setup_method(self):
        self.db = create_test_database(MODELS)
        config.Config._instances = {}
        self.settings = config.Config(config_path=tempfile.mkdtemp(prefix="unmanic_tests_"))
        credentials.flush_verify_cache()
        login_throttle.record_success("login:127.0.0.1")
        self.server = BackgroundServer(
            lambda: UnmanicWebApplication([
                (r"/unmanic/setup", SetupPageHandler),
                (r"/unmanic/auth/setup", SetupActionHandler),
                (r"/(.*)", EchoHandler),
            ])
        )
        self.base_url = self.server.start()
        self.settings.set_config_item("auth_enabled", True, save_settings=False)

    def teardown_method(self):
        self.server.stop()
        destroy_test_database(self.db, MODELS)
        login_throttle.record_success("login:127.0.0.1")

    def _submit(self, username="jordan", password="a-good-password", confirm=None):
        body = {
            "username": username,
            "password": password,
            "confirm": confirm if confirm is not None else password,
        }
        return requests.post(
            self.base_url + "/unmanic/auth/setup", data=body, allow_redirects=False, timeout=10
        )

    def test_setup_page_is_served_when_no_credential_exists(self):
        response = requests.get(self.base_url + "/unmanic/setup", timeout=10)
        assert response.status_code == 200

    def test_the_setup_page_states_it_is_not_internet_protection(self):
        body = requests.get(self.base_url + "/unmanic/setup", timeout=10).text
        assert "does not make Unmanic safe to" in body

    def test_other_routes_redirect_to_setup(self):
        response = requests.get(
            self.base_url + "/unmanic/ui/dashboard/",
            headers={"Accept": "text/html"},
            allow_redirects=False,
            timeout=10,
        )
        assert response.status_code == 302
        assert response.headers["Location"] == "/unmanic/setup"

    def test_submitting_setup_creates_the_account_and_signs_in(self):
        response = self._submit()
        assert response.status_code == 302
        assert response.headers["Location"] == "/unmanic/ui/dashboard/"
        assert credentials.credential_is_configured() is True
        assert sessions.COOKIE_NAME in response.headers.get("Set-Cookie")

    def test_mismatched_confirmation_is_rejected(self):
        response = self._submit(confirm="something-else")
        assert response.status_code == 400
        assert credentials.credential_is_configured() is False

    def test_short_password_is_rejected(self):
        response = self._submit(password="short", confirm="short")
        assert response.status_code == 400
        assert credentials.credential_is_configured() is False

    def test_setup_routes_return_404_once_a_credential_exists(self):
        self._submit()
        assert requests.get(self.base_url + "/unmanic/setup", timeout=10).status_code == 404
        assert self._submit(username="someone-else").status_code == 404

    def test_setup_cannot_be_used_to_replace_an_existing_credential(self):
        self._submit()
        self._submit(username="attacker", password="attacker-password")
        assert credentials.get_username() == "jordan"

    def test_setup_page_is_self_contained(self):
        # The page carries inline JS for live validation. Inline is fine; an external file
        # would not be, because the guard allowlist deliberately opens no static paths.
        body = requests.get(self.base_url + "/unmanic/setup", timeout=10).text
        assert "<script src=" not in body
        assert '<link rel="stylesheet"' not in body
        assert "<img" not in body
        assert "<script>" in body, "live validation script is missing"

    def test_setup_page_advertises_the_length_rule_the_server_enforces(self):
        body = requests.get(self.base_url + "/unmanic/setup", timeout=10).text
        assert str(credentials.MIN_PASSWORD_LENGTH) in body
        assert str(credentials.MAX_PASSWORD_LENGTH) in body
