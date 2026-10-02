#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import pytest

from unmanic.libs.webauth import credentials


@pytest.mark.unittest
class TestPasswordHashing(object):
    def test_hash_then_verify_round_trip(self):
        encoded = credentials.hash_password("correct horse battery staple")
        assert credentials.verify_password("correct horse battery staple", encoded) is True

    def test_wrong_password_is_rejected(self):
        encoded = credentials.hash_password("correct horse battery staple")
        assert credentials.verify_password("Correct horse battery staple", encoded) is False
        assert credentials.verify_password("", encoded) is False

    def test_encoded_format_records_its_parameters(self):
        encoded = credentials.hash_password("hunter2")
        parts = encoded.split("$")
        assert len(parts) == 6
        assert parts[0] == "scrypt"
        assert int(parts[1]) == credentials.SCRYPT_N
        assert int(parts[2]) == credentials.SCRYPT_R
        assert int(parts[3]) == credentials.SCRYPT_P

    def test_the_plaintext_never_appears_in_the_encoded_hash(self):
        encoded = credentials.hash_password("hunter2")
        assert "hunter2" not in encoded

    def test_salt_differs_between_hashes_of_the_same_password(self):
        assert credentials.hash_password("hunter2") != credentials.hash_password("hunter2")

    def test_malformed_hashes_are_rejected_and_do_not_raise(self):
        for bad in ["", "not-a-hash", "scrypt$1$2$3", "scrypt$a$b$c$d$e", "bcrypt$1$2$3$4$5", None]:
            assert credentials.verify_password("hunter2", bad) is False

    def test_needs_rehash_detects_weaker_stored_parameters(self):
        current = credentials.hash_password("hunter2")
        assert credentials.needs_rehash(current) is False
        weaker = current.replace("scrypt${}$".format(credentials.SCRYPT_N), "scrypt$1024$", 1)
        assert credentials.needs_rehash(weaker) is True

    def test_unicode_passwords_round_trip(self):
        encoded = credentials.hash_password("pässwörd–✓")
        assert credentials.verify_password("pässwörd–✓", encoded) is True
