#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import base64

import pytest

from tests.support_.webauth_db import create_test_database, destroy_test_database
from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials
from unmanic.libs.webauth import credentials


@pytest.mark.unittest
class TestCredentialStore(object):
    def setup_method(self):
        self.db = create_test_database([WebAuthCredentials])
        credentials.flush_verify_cache()

    def teardown_method(self):
        destroy_test_database(self.db, [WebAuthCredentials])

    def test_no_credential_configured_initially(self):
        assert credentials.credential_is_configured() is False
        assert credentials.get_username() is None

    def test_set_then_verify(self):
        credentials.set_credential("jordan", "a-good-password")
        assert credentials.credential_is_configured() is True
        assert credentials.get_username() == "jordan"
        assert credentials.verify_credential("jordan", "a-good-password") is True

    def test_wrong_username_or_password_rejected(self):
        credentials.set_credential("jordan", "a-good-password")
        assert credentials.verify_credential("jordan", "wrong") is False
        assert credentials.verify_credential("someone", "a-good-password") is False

    def test_username_comparison_is_case_sensitive(self):
        credentials.set_credential("jordan", "a-good-password")
        assert credentials.verify_credential("Jordan", "a-good-password") is False

    def test_setting_a_credential_replaces_rather_than_appends(self):
        credentials.set_credential("jordan", "first-password")
        credentials.set_credential("jordan", "second-password")
        assert WebAuthCredentials.select().count() == 1
        assert credentials.verify_credential("jordan", "first-password") is False
        assert credentials.verify_credential("jordan", "second-password") is True

    def test_plaintext_password_is_never_stored(self):
        credentials.set_credential("jordan", "a-good-password")
        row = WebAuthCredentials.select().first()
        assert "a-good-password" not in row.password_hash

    def test_password_length_is_validated(self):
        with pytest.raises(ValueError):
            credentials.set_credential("jordan", "short")
        with pytest.raises(ValueError):
            credentials.set_credential("jordan", "x" * (credentials.MAX_PASSWORD_LENGTH + 1))

    def test_username_is_validated(self):
        with pytest.raises(ValueError):
            credentials.set_credential("", "a-good-password")
        with pytest.raises(ValueError):
            credentials.set_credential("   ", "a-good-password")

    def test_verify_with_no_credential_configured_is_false(self):
        assert credentials.verify_credential("jordan", "a-good-password") is False

    def test_clear_credential(self):
        credentials.set_credential("jordan", "a-good-password")
        credentials.clear_credential()
        assert credentials.credential_is_configured() is False


@pytest.mark.unittest
class TestBasicHeaderVerification(object):
    def setup_method(self):
        self.db = create_test_database([WebAuthCredentials])
        credentials.flush_verify_cache()
        credentials.set_credential("jordan", "a-good-password")

    def teardown_method(self):
        destroy_test_database(self.db, [WebAuthCredentials])

    @staticmethod
    def _header(raw):
        return "Basic " + base64.b64encode(raw.encode("utf-8")).decode("ascii")

    def test_valid_header_accepted(self):
        assert credentials.verify_basic_header(self._header("jordan:a-good-password")) is True

    def test_invalid_header_rejected(self):
        assert credentials.verify_basic_header(self._header("jordan:wrong")) is False
        assert credentials.verify_basic_header(self._header("nope:a-good-password")) is False

    def test_malformed_headers_rejected_without_raising(self):
        for bad in [None, "", "Basic", "Basic !!!!not-base64!!!!", "Bearer abc", self._header("no-colon")]:
            assert credentials.verify_basic_header(bad) is False

    def test_password_containing_a_colon_is_handled(self):
        credentials.set_credential("jordan", "pass:with:colons")
        credentials.flush_verify_cache()
        assert credentials.verify_basic_header(self._header("jordan:pass:with:colons")) is True

    def test_repeat_verification_is_served_from_cache(self):
        header = self._header("jordan:a-good-password")
        assert credentials.verify_basic_header(header) is True
        calls = []
        original = credentials.verify_password

        def counting(password, encoded):
            calls.append(password)
            return original(password, encoded)

        credentials.verify_password = counting
        try:
            assert credentials.verify_basic_header(header) is True
        finally:
            credentials.verify_password = original
        assert calls == [], "second verification should have been served from the cache"

    def test_cache_is_flushed_when_the_credential_changes(self):
        header = self._header("jordan:a-good-password")
        assert credentials.verify_basic_header(header) is True
        credentials.set_credential("jordan", "a-different-password")
        assert credentials.verify_basic_header(header) is False

    def test_failures_are_not_cached(self):
        # A rejected header must not be remembered as rejected: once the credential
        # actually matches it, the very same header has to start working.
        bad = self._header("jordan:wrong-password")
        assert credentials.verify_basic_header(bad) is False
        credentials.set_credential("jordan", "wrong-password")
        assert credentials.verify_basic_header(bad) is True
