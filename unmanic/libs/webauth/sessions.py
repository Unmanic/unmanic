#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import datetime
import hashlib
import secrets
from typing import Any, Dict, List, Optional

COOKIE_NAME = "unmanic_session"
TOKEN_BYTES = 32

# last_used is only rewritten when it is at least this stale, to avoid a database
# write on every single request.
TOUCH_INTERVAL_SECONDS = 60


def hash_token(token: str) -> str:
    """
    Hash a session token for storage and lookup.

    :param token:
    :return:
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    remote_addr: Optional[str],
    user_agent: Optional[str],
    idle_timeout_days: int,
    max_age_days: int,
) -> str:
    """
    Create a new session and return its token.

    The token is returned once and never stored; only its hash is persisted.

    :param remote_addr:
    :param user_agent:
    :param idle_timeout_days:
    :param max_age_days:
    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = datetime.datetime.now()
    WebAuthSessions.create(
        token_hash=hash_token(token),
        created=now,
        last_used=now,
        expires=now + datetime.timedelta(days=int(max_age_days)),
        remote_addr=remote_addr,
        user_agent=(user_agent or "")[:512],
    )
    return token


def lookup_session(token: Optional[str], idle_timeout_days: int):
    """
    Return the live session matching a token, or None.

    Expired sessions are deleted as they are encountered.

    :param token:
    :param idle_timeout_days:
    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    if not token or not isinstance(token, str):
        return None
    row = WebAuthSessions.get_or_none(WebAuthSessions.token_hash == hash_token(token))
    if row is None:
        return None

    now = datetime.datetime.now()
    idle_cutoff = now - datetime.timedelta(days=int(idle_timeout_days))
    if row.expires <= now or row.last_used <= idle_cutoff:
        row.delete_instance()
        return None

    if (now - row.last_used).total_seconds() >= TOUCH_INTERVAL_SECONDS:
        row.last_used = now
        row.save()
    return row


def revoke_session(token: Optional[str]) -> bool:
    """
    Delete the session matching a token.

    :param token:
    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    if not token or not isinstance(token, str):
        return False
    deleted = WebAuthSessions.delete().where(WebAuthSessions.token_hash == hash_token(token)).execute()
    return deleted > 0


def revoke_session_by_id(session_id: int) -> bool:
    """
    Delete a session by its row id.

    :param session_id:
    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    deleted = WebAuthSessions.delete().where(WebAuthSessions.id == session_id).execute()
    return deleted > 0


def revoke_all_sessions() -> int:
    """
    Delete every session.

    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    return WebAuthSessions.delete().execute()


def purge_expired() -> int:
    """
    Delete every session past its absolute expiry.

    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    return WebAuthSessions.delete().where(WebAuthSessions.expires <= datetime.datetime.now()).execute()


def list_sessions(current_token: Optional[str]) -> List[Dict[str, Any]]:
    """
    List live sessions for display. Never returns token hashes.

    :param current_token:
    :return:
    """
    from unmanic.libs.unmodels.webauthsessions import WebAuthSessions

    current_hash = hash_token(current_token) if current_token else None
    results = []
    for row in WebAuthSessions.select().order_by(WebAuthSessions.last_used.desc()):
        results.append(
            {
                "id": row.id,
                "created": str(row.created),
                "last_used": str(row.last_used),
                "expires": str(row.expires),
                "remote_addr": row.remote_addr,
                "user_agent": row.user_agent,
                "current": bool(current_hash and row.token_hash == current_hash),
            }
        )
    return results
