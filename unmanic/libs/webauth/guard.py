#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

from typing import List, Optional
from urllib.parse import quote, urlsplit

from unmanic import config
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.webauth import credentials, sessions
from unmanic.libs.webauth.throttle import login_throttle

logger = UnmanicLogging.get_logger(name="WebAuth")

DEFAULT_LANDING_PATH = "/unmanic/ui/dashboard/"
LOGIN_PATH = "/unmanic/login"
SETUP_PATH = "/unmanic/setup"

PUBLIC_PATHS = frozenset({LOGIN_PATH, "/unmanic/auth/login"})
SETUP_PATHS = frozenset({SETUP_PATH, "/unmanic/auth/setup"})

# Routes that enrol a credential, or turn authentication on.
#
# These stay closed while authentication is disabled, because an installation with
# authentication off cannot tell its owner apart from anyone else who can reach it. That
# is not a gap in the check, it is the state itself: there is no credential to verify
# against and no session to trust, so nothing presented in-band can prove ownership.
#
# An enrolment token would not fix it either. Any token this application could hand out
# would have to be readable through this same unauthenticated interface, which serves a
# log viewer and a filesystem browser, so an attacker able to reach the port could read it
# just as easily as the owner.
#
# Enrolment is therefore proven out of band, from the host, where that proof already
# exists: `unmanic --set-password`, or the auth_* environment variables. Both require the
# level of access that already implies ownership of the installation. The refusal below
# names them, so someone who tries the API is told where to go rather than left guessing.
AUTH_MUTATION_PATHS = frozenset(
    {
        SETUP_PATH,
        "/unmanic/auth/setup",
        "/unmanic/api/v2/auth/configure",
        "/unmanic/api/v2/auth/password",
        "/unmanic/api/v2/auth/sessions",
        "/unmanic/api/v2/auth/sessions/revoke",
    }
)

ENROLMENT_REQUIRES_HOST_ACCESS = (
    "Authentication is disabled. It is enabled from the host, either by running "
    "'unmanic --set-password' or by setting the auth_enabled, auth_username and "
    "auth_password environment variables. It cannot be enabled over the network, because "
    "an installation with authentication disabled has no way to tell its owner apart from "
    "anyone else who can reach it."
)

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Prefixes a cross-site browser context has no legitimate reason to reach.
# UI routes are deliberately excluded so the unmanic.app account flow, which returns
# cross-site to /unmanic/ui/trigger/, keeps working.
CSRF_GUARDED_PREFIXES = (
    "/unmanic/api/",
    "/unmanic/plugin_api/",
    "/unmanic/panel/",
    "/unmanic/downloads/",
)


class AuthDecision(object):
    """
    AuthDecision

    The outcome of an authorisation check for a single request.
    """

    def __init__(
        self,
        allowed: bool,
        status: int = 401,
        redirect_to: Optional[str] = None,
        reason: str = "",
        retry_after: int = 0,
    ):
        self.allowed = allowed
        self.status = status
        self.redirect_to = redirect_to
        self.reason = reason
        self.retry_after = retry_after


ALLOWED = AuthDecision(True)


def origin_is_allowed(origin: Optional[str], host: Optional[str], trusted_origins: List[str]) -> bool:
    """
    Return True if a request's Origin is acceptable.

    An absent Origin is allowed: browsers always send it on unsafe methods, while curl
    and instance-to-instance calls never do.

    :param origin:
    :param host:
    :param trusted_origins:
    :return:
    """
    if not origin:
        return True
    if origin in (trusted_origins or []):
        return True
    if origin == "null":
        return False
    parsed = urlsplit(origin)
    if not parsed.netloc:
        return False
    return parsed.netloc == host


def sec_fetch_is_allowed(request) -> bool:
    """
    Reject cross-site browser requests to machine-callable routes.

    An absent header allows the request. This matters: browsers do not send
    Sec-Fetch-Site on WebSocket handshakes, so requiring it would break the WebSocket.

    :param request:
    :return:
    """
    if request.headers.get("Sec-Fetch-Site") != "cross-site":
        return True
    return not str(request.path).startswith(CSRF_GUARDED_PREFIXES)


def wants_html(request) -> bool:
    """
    Return True if this looks like a browser navigation that should be redirected to the
    login page rather than given a JSON 401.

    :param request:
    :return:
    """
    if request.method not in ("GET", "HEAD"):
        return False
    return "text/html" in (request.headers.get("Accept") or "")


def safe_next_path(value: Optional[str]) -> str:
    """
    Return a local redirect target, or the dashboard if the value is not a safe local path.

    Blocks absolute URLs, protocol-relative URLs, and backslash or control-character tricks.

    :param value:
    :return:
    """
    if not value or not isinstance(value, str):
        return DEFAULT_LANDING_PATH
    if not value.startswith("/"):
        return DEFAULT_LANDING_PATH
    if value.startswith("//"):
        return DEFAULT_LANDING_PATH
    if any(char in value for char in ("\\", "\r", "\n", "\t")):
        return DEFAULT_LANDING_PATH
    return value


def setup_required() -> bool:
    """
    Return True when authentication is on but no account exists yet.

    :return:
    """
    return not credentials.credential_is_configured()


def session_from_request(request):
    """
    Return the live session for a request's cookie, or None.

    :param request:
    :return:
    """
    settings = config.Config()
    cookie = request.cookies.get(sessions.COOKIE_NAME)
    if cookie is None:
        return None
    token = getattr(cookie, "value", None)
    if not token:
        return None
    return sessions.lookup_session(token, settings.get_auth_session_idle_timeout_days())


def authorise_basic(request) -> Optional[AuthDecision]:
    """
    Verify an HTTP Basic header, bounding how often the expensive verification can run.

    Returns ALLOWED when the header verifies, a refusal while the client is locked out, and
    None when there is nothing to act on, so the caller falls through to its normal refusal.

    Basic is the machine-facing path and is enabled by default, so an unverified header
    reaching scrypt on every request is both an unlimited password oracle and a way to
    occupy the Tornado I/O thread without ever signing in. The order here matters:

      1. An already-verified header is answered from the cache, so a working client is
         never refused because of another client sharing its address.
      2. The throttle is consulted before any verification, so a failing address is
         refused without spending the work it was trying to make us spend.
      3. Only then does the header reach scrypt.

    Failures are counted under their own key, kept separate from the login form so that
    machine traffic and browser sign-ins cannot clear or trip each other's lockout.

    :param request:
    :return:
    """
    header = request.headers.get("Authorization")
    if not header:
        return None

    if credentials.basic_header_is_cached(header):
        return ALLOWED

    key = "basic:{}".format(request.remote_ip)

    retry_after = login_throttle.retry_after(key)
    if retry_after:
        return AuthDecision(
            False, status=429, reason="Too many failed attempts", retry_after=retry_after
        )

    if credentials.verify_basic_header(header):
        login_throttle.record_success(key)
        return ALLOWED

    login_throttle.record_failure(key)
    logger.warning("Failed HTTP Basic authentication attempt from %s", request.remote_ip)
    return None


def authorise(request) -> AuthDecision:
    """
    Decide whether a request may proceed.

    :param request:
    :return:
    """
    settings = config.Config()

    path = str(request.path)

    if not settings.get_auth_enabled():
        # Authentication is off, but the routes that enrol a credential, or turn it on,
        # must not be reachable. See AUTH_MUTATION_PATHS for why this cannot be solved
        # in-band. Everything else behaves exactly as it did before this feature existed.
        if path in AUTH_MUTATION_PATHS:
            return AuthDecision(False, status=403, reason=ENROLMENT_REQUIRES_HOST_ACCESS)
        return ALLOWED

    # CSRF layer 2: origin verification on state-changing requests. Placed above the setup
    # and public branches so it also covers the login and setup POSTs, which are the only
    # unauthenticated writes in the application.
    if request.method in UNSAFE_METHODS:
        if not origin_is_allowed(request.headers.get("Origin"), request.host, settings.get_auth_trusted_origins()):
            return AuthDecision(False, status=403, reason="Cross-origin request rejected")

    # CSRF layer 3: cross-site browser requests to machine-callable routes.
    if not sec_fetch_is_allowed(request):
        return AuthDecision(False, status=403, reason="Cross-site request rejected")

    if setup_required():
        if path in SETUP_PATHS:
            return ALLOWED
        if wants_html(request):
            return AuthDecision(False, status=302, redirect_to=SETUP_PATH, reason="Setup required")
        return AuthDecision(False, status=401, reason="Setup required")

    if path in SETUP_PATHS:
        # Setup is complete; do not advertise that these routes ever existed.
        return AuthDecision(False, status=404, reason="Not found")

    if path in PUBLIC_PATHS:
        return ALLOWED

    if session_from_request(request) is not None:
        return ALLOWED

    if settings.get_auth_allow_basic():
        basic_decision = authorise_basic(request)
        if basic_decision is not None:
            return basic_decision

    if wants_html(request):
        target = "{}?next={}".format(LOGIN_PATH, quote(safe_next_path(path), safe=""))
        return AuthDecision(False, status=302, redirect_to=target, reason="Authentication required")
    return AuthDecision(False, status=401, reason="Authentication required")
