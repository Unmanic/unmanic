#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import os

import tornado.template
import tornado.web

from unmanic import config
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.webauth import credentials, guard, sessions
from unmanic.libs.webauth.throttle import login_throttle

logger = UnmanicLogging.get_logger(name="WebAuth")

TEMPLATE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

GENERIC_LOGIN_ERROR = "Invalid username or password"


class AuthTemplateMixin(object):
    """
    AuthTemplateMixin

    The application-wide template_loader points at the built frontend directory and takes
    precedence over get_template_path(), so the loader itself must be replaced. Overriding
    get_template_path() alone silently has no effect.
    """

    def create_template_loader(self, template_path):
        return tornado.template.Loader(TEMPLATE_ROOT)


def set_session_cookie(handler, token, max_age_days):
    """
    Write the session cookie.

    :param handler:
    :param token:
    :param max_age_days:
    :return:
    """
    settings = config.Config()
    kwargs = {
        "httponly": True,
        "path": "/",
        "expires_days": int(max_age_days),
        "samesite": "Lax",
    }
    if settings.get_ssl_enabled():
        # Only set Secure when TLS is on. Setting it over plain HTTP would stop the cookie
        # ever being sent and lock out every LAN user.
        kwargs["secure"] = True
    handler.set_cookie(sessions.COOKIE_NAME, token, **kwargs)


def clear_session_cookie(handler):
    """
    Remove the session cookie.

    :param handler:
    :return:
    """
    handler.clear_cookie(sessions.COOKIE_NAME, path="/")


def throttle_key(handler):
    """
    Build the throttle key for a request.

    :param handler:
    :return:
    """
    return "login:{}".format(handler.request.remote_ip)


class AuthFailureHandler(tornado.web.RequestHandler):
    """
    AuthFailureHandler

    Terminates any request the guard refused. Every HTTP method lands here, so a rejected
    request can never fall through to a real handler.
    """

    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PATCH", "PUT", "OPTIONS")

    def initialize(self, decision=None):
        self.decision = decision

    def _respond(self):
        decision = self.decision
        if decision is not None and decision.status == 302 and decision.redirect_to:
            self.redirect(decision.redirect_to)
            return
        status = 401 if decision is None else decision.status
        reason = "Unauthorized" if decision is None else (decision.reason or "Unauthorized")
        if decision is not None and decision.retry_after:
            self.set_header("Retry-After", str(decision.retry_after))
        # No WWW-Authenticate header is ever sent. Browsers must never cache Basic
        # credentials, or Basic would become an ambient credential and a CSRF vector.
        self.set_status(status)
        self.set_header("Content-Type", 'application/json; charset="utf-8"')
        self.finish({"error": "{}: {}".format(status, reason)})

    def get(self, *args, **kwargs):
        self._respond()

    def head(self, *args, **kwargs):
        self._respond()

    def post(self, *args, **kwargs):
        self._respond()

    def delete(self, *args, **kwargs):
        self._respond()

    def patch(self, *args, **kwargs):
        self._respond()

    def put(self, *args, **kwargs):
        self._respond()

    def options(self, *args, **kwargs):
        self._respond()


class LoginPageHandler(AuthTemplateMixin, tornado.web.RequestHandler):
    """
    LoginPageHandler

    Serves the sign-in page.
    """

    SUPPORTED_METHODS = ("GET", "HEAD")

    def get(self):
        if guard.session_from_request(self.request) is not None:
            self.redirect(guard.safe_next_path(self.get_argument("next", None)))
            return
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.render(
            "auth/login.html",
            error=None,
            next_path=guard.safe_next_path(self.get_argument("next", None)),
        )


class LoginActionHandler(AuthTemplateMixin, tornado.web.RequestHandler):
    """
    LoginActionHandler

    Validates a sign-in attempt and issues a session.
    """

    SUPPORTED_METHODS = ("POST",)

    def post(self):
        settings = config.Config()
        key = throttle_key(self)
        next_path = guard.safe_next_path(self.get_argument("next", None))

        retry_after = login_throttle.retry_after(key)
        if retry_after:
            logger.warning(
                "Web authentication locked out for %s for a further %s seconds",
                self.request.remote_ip,
                retry_after,
            )
            self.set_status(429)
            self.set_header("Retry-After", str(retry_after))
            self.render("auth/login.html", error="Too many attempts. Try again later.", next_path=next_path)
            return

        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        if not credentials.verify_credential(username, password):
            login_throttle.record_failure(key)
            logger.warning("Failed web authentication attempt from %s", self.request.remote_ip)
            self.set_status(401)
            self.render("auth/login.html", error=GENERIC_LOGIN_ERROR, next_path=next_path)
            return

        login_throttle.record_success(key)
        sessions.purge_expired()
        token = sessions.create_session(
            self.request.remote_ip,
            self.request.headers.get("User-Agent"),
            settings.get_auth_session_idle_timeout_days(),
            settings.get_auth_session_max_age_days(),
        )
        set_session_cookie(self, token, settings.get_auth_session_max_age_days())
        logger.info("Successful web authentication from %s", self.request.remote_ip)
        self.redirect(next_path)


class LogoutActionHandler(tornado.web.RequestHandler):
    """
    LogoutActionHandler

    Revokes the current session. POST only, so an image tag cannot trigger it.
    """

    SUPPORTED_METHODS = ("POST",)

    def post(self):
        cookie = self.request.cookies.get(sessions.COOKIE_NAME)
        if cookie is not None and getattr(cookie, "value", None):
            sessions.revoke_session(cookie.value)
        clear_session_cookie(self)
        self.redirect(guard.LOGIN_PATH)
