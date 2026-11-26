#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import datetime

import pytest

from tests.support_.webauth_db import create_test_database, destroy_test_database
from unmanic.libs.unmodels.webauthsessions import WebAuthSessions
from unmanic.libs.webauth import sessions


@pytest.mark.unittest
class TestSessionStore(object):
    def setup_method(self):
        self.db = create_test_database([WebAuthSessions])

    def teardown_method(self):
        destroy_test_database(self.db, [WebAuthSessions])

    def test_create_returns_a_high_entropy_token(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        assert isinstance(token, str)
        assert len(token) >= 40
        assert sessions.create_session("10.0.0.1", "pytest", 7, 30) != token

    def test_the_raw_token_is_never_stored(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        row = WebAuthSessions.select().first()
        assert row.token_hash != token
        assert token not in row.token_hash

    def test_lookup_finds_a_live_session(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        assert sessions.lookup_session(token, 7) is not None

    def test_lookup_rejects_unknown_and_malformed_tokens(self):
        sessions.create_session("10.0.0.1", "pytest", 7, 30)
        for bad in [None, "", "not-a-token"]:
            assert sessions.lookup_session(bad, 7) is None

    def test_absolute_expiry_is_enforced(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        row = WebAuthSessions.select().first()
        row.expires = datetime.datetime.now() - datetime.timedelta(seconds=1)
        row.save()
        assert sessions.lookup_session(token, 7) is None

    def test_idle_timeout_is_enforced(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        row = WebAuthSessions.select().first()
        row.last_used = datetime.datetime.now() - datetime.timedelta(days=8)
        row.save()
        assert sessions.lookup_session(token, 7) is None

    def test_a_session_inside_the_idle_window_survives(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        row = WebAuthSessions.select().first()
        row.last_used = datetime.datetime.now() - datetime.timedelta(days=6)
        row.save()
        assert sessions.lookup_session(token, 7) is not None

    def test_expired_sessions_are_deleted_on_lookup(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        row = WebAuthSessions.select().first()
        row.expires = datetime.datetime.now() - datetime.timedelta(seconds=1)
        row.save()
        sessions.lookup_session(token, 7)
        assert WebAuthSessions.select().count() == 0

    def test_revoke_single_session(self):
        first = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        second = sessions.create_session("10.0.0.2", "pytest", 7, 30)
        assert sessions.revoke_session(first) is True
        assert sessions.lookup_session(first, 7) is None
        assert sessions.lookup_session(second, 7) is not None

    def test_revoke_all_sessions(self):
        sessions.create_session("10.0.0.1", "pytest", 7, 30)
        sessions.create_session("10.0.0.2", "pytest", 7, 30)
        assert sessions.revoke_all_sessions() == 2
        assert WebAuthSessions.select().count() == 0

    def test_purge_expired_leaves_live_sessions(self):
        live = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        stale = sessions.create_session("10.0.0.2", "pytest", 7, 30)
        row = WebAuthSessions.get(WebAuthSessions.token_hash == sessions.hash_token(stale))
        row.expires = datetime.datetime.now() - datetime.timedelta(seconds=1)
        row.save()
        assert sessions.purge_expired() == 1
        assert sessions.lookup_session(live, 7) is not None

    def test_list_sessions_flags_the_current_one_and_leaks_no_hashes(self):
        current = sessions.create_session("10.0.0.1", "browser-a", 7, 30)
        sessions.create_session("10.0.0.2", "browser-b", 7, 30)
        listed = sessions.list_sessions(current)
        assert len(listed) == 2
        assert sum(1 for item in listed if item["current"]) == 1
        for item in listed:
            assert "token_hash" not in item

    def test_revoke_session_by_id(self):
        token = sessions.create_session("10.0.0.1", "pytest", 7, 30)
        row = WebAuthSessions.select().first()
        assert sessions.revoke_session_by_id(row.id) is True
        assert sessions.lookup_session(token, 7) is None
        assert sessions.revoke_session_by_id(9999) is False
