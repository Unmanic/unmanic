#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import tornado.web


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
