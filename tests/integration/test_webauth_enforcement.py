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
import tornado.websocket

from tests.support_.webauth_db import create_test_database, destroy_test_database
from tests.support_.webauth_server import BackgroundServer, basic_header, websocket_handshake_headers
from unmanic import config
from unmanic.libs.uiserver import UnmanicWebApplication
from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials
from unmanic.libs.unmodels.webauthsessions import WebAuthSessions
from unmanic.libs.webauth import credentials, sessions

MODELS = [WebAuthCredentials, WebAuthSessions]


class EchoHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        self.write("ok")

    def post(self, *args, **kwargs):
        self.write("ok")


class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self, *args, **kwargs):
        self.write_message("ok")


ROUTES = [
    (r"/unmanic/websocket", EchoWebSocket),
    (r"/unmanic/api/v1/(.*)", EchoHandler),
    (r"/unmanic/api/v2/(.*)", EchoHandler),
    (r"/unmanic/downloads/(.*)", EchoHandler),
    (r"/unmanic/swagger(.*)", EchoHandler),
    (r"/unmanic/panel/(.*)", EchoHandler),
    (r"/unmanic/plugin_api/(.*)", EchoHandler),
    (r"/unmanic/js/(.*)", EchoHandler),
    (r"/unmanic/ui/(.*)", EchoHandler),
    (r"/(.*)", EchoHandler),
]


class WebAuthServerTestBase(object):
    """
    Shared setup: an isolated database, fresh settings, and a real server on a random port.
    """

    def setup_method(self):
        self.db = create_test_database(MODELS)
        config.Config._instances = {}
        self.settings = config.Config(config_path=tempfile.mkdtemp(prefix="unmanic_tests_"))
        credentials.flush_verify_cache()
        # State the starting condition rather than inheriting it: a fresh config directory
        # now defaults to authentication enabled.
        self.settings.set_config_item("auth_enabled", False, save_settings=False)
        self.server = BackgroundServer(lambda: UnmanicWebApplication(list(ROUTES)))
        self.base_url = self.server.start()

    def teardown_method(self):
        self.server.stop()
        destroy_test_database(self.db, MODELS)

    def get(self, path, **kwargs):
        kwargs.setdefault("allow_redirects", False)
        kwargs.setdefault("timeout", 10)
        return requests.get(self.base_url + path, **kwargs)

    def post(self, path, **kwargs):
        kwargs.setdefault("allow_redirects", False)
        kwargs.setdefault("timeout", 10)
        return requests.post(self.base_url + path, **kwargs)

    def enable_auth(self):
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        credentials.set_credential("jordan", "a-good-password")


@pytest.mark.integrationtest
class TestEnforcement(WebAuthServerTestBase):
    def test_behaviour_is_unchanged_when_authentication_is_disabled(self):
        assert self.get("/unmanic/api/v2/version/read").status_code == 200

    def test_enabled_auth_blocks_anonymous_api_access(self):
        self.enable_auth()
        assert self.get("/unmanic/api/v2/version/read").status_code == 401

    def test_no_www_authenticate_header_is_ever_sent(self):
        self.enable_auth()
        response = self.get("/unmanic/api/v2/version/read")
        assert response.headers.get("WWW-Authenticate") is None

    def test_browser_navigation_is_redirected_to_login(self):
        self.enable_auth()
        response = self.get("/unmanic/ui/dashboard/", headers={"Accept": "text/html"})
        assert response.status_code == 302
        assert response.headers["Location"].startswith("/unmanic/login")

    def test_the_redirect_preserves_the_requested_path(self):
        self.enable_auth()
        response = self.get("/unmanic/ui/settings/", headers={"Accept": "text/html"})
        assert "next=" in response.headers["Location"]

    def test_basic_auth_is_accepted(self):
        self.enable_auth()
        response = self.get(
            "/unmanic/api/v2/version/read",
            headers={"Authorization": basic_header("jordan", "a-good-password")},
        )
        assert response.status_code == 200

    def test_basic_auth_with_a_wrong_password_is_rejected(self):
        self.enable_auth()
        response = self.get(
            "/unmanic/api/v2/version/read", headers={"Authorization": basic_header("jordan", "wrong-password")}
        )
        assert response.status_code == 401

    def test_basic_auth_can_be_disabled(self):
        self.enable_auth()
        self.settings.set_config_item("auth_allow_basic", False, save_settings=False)
        response = self.get(
            "/unmanic/api/v2/version/read",
            headers={"Authorization": basic_header("jordan", "a-good-password")},
        )
        assert response.status_code == 401

    def test_cross_origin_post_is_rejected(self):
        self.enable_auth()
        response = self.post(
            "/unmanic/api/v2/version/read",
            data="{}",
            headers={
                "Authorization": basic_header("jordan", "a-good-password"),
                "Origin": "http://evil.example.com",
            },
        )
        assert response.status_code == 403

    def test_same_origin_post_is_allowed(self):
        self.enable_auth()
        response = self.post(
            "/unmanic/api/v2/version/read",
            data="{}",
            headers={
                "Authorization": basic_header("jordan", "a-good-password"),
                "Origin": self.base_url,
            },
        )
        assert response.status_code == 200

    def test_post_without_an_origin_header_is_allowed(self):
        self.enable_auth()
        response = self.post(
            "/unmanic/api/v2/version/read",
            data="{}",
            headers={"Authorization": basic_header("jordan", "a-good-password")},
        )
        assert response.status_code == 200

    def test_cross_site_fetch_to_the_api_is_rejected(self):
        self.enable_auth()
        response = self.get(
            "/unmanic/api/v2/version/read",
            headers={
                "Authorization": basic_header("jordan", "a-good-password"),
                "Sec-Fetch-Site": "cross-site",
            },
        )
        assert response.status_code == 403

    def test_cross_site_navigation_to_the_ui_is_still_allowed(self):
        # The unmanic.app account flow returns cross-site to /unmanic/ui/trigger/.
        self.enable_auth()
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        response = self.get(
            "/unmanic/ui/trigger/",
            headers={"Sec-Fetch-Site": "cross-site"},
            cookies={sessions.COOKIE_NAME: token},
        )
        assert response.status_code == 200

    def test_setup_is_required_when_no_credential_exists(self):
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        response = self.get("/unmanic/ui/dashboard/", headers={"Accept": "text/html"})
        assert response.status_code == 302
        assert response.headers["Location"] == "/unmanic/setup"


@pytest.mark.integrationtest
class TestEveryRouteShapeIsCovered(WebAuthServerTestBase):
    def test_no_route_shape_is_reachable_anonymously(self):
        self.enable_auth()
        paths = [
            "/unmanic/api/v1/pending",
            "/unmanic/api/v2/version/read",
            "/unmanic/downloads/some-file",
            "/unmanic/swagger",
            "/unmanic/panel/some-plugin",
            "/unmanic/plugin_api/some-plugin",
            "/unmanic/js/app.js",
            "/unmanic/ui/dashboard/",
            "/",
        ]
        for path in paths:
            response = self.get(path)
            assert response.status_code in (401, 302), "{} was reachable anonymously ({})".format(
                path, response.status_code
            )

    def test_every_route_shape_is_reachable_once_authenticated(self):
        self.enable_auth()
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        for path in ["/unmanic/api/v2/version/read", "/unmanic/ui/dashboard/", "/unmanic/js/app.js"]:
            response = self.get(path, cookies={sessions.COOKIE_NAME: token})
            assert response.status_code == 200, "{} was blocked when authenticated".format(path)

    def test_websocket_handshake_is_rejected_without_a_session(self):
        # Browsers do not send Authorization on a WS handshake, so the cookie is the only
        # credential the WebSocket can ever carry. Verified against real Chrome, 2026-08-17.
        self.enable_auth()
        response = self.get("/unmanic/websocket", headers=websocket_handshake_headers())
        assert response.status_code in (401, 302)

    def test_websocket_handshake_is_accepted_with_a_session_cookie(self):
        self.enable_auth()
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        response = self.get(
            "/unmanic/websocket",
            headers=websocket_handshake_headers(),
            cookies={sessions.COOKIE_NAME: token},
        )
        assert response.status_code == 101
