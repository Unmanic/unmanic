#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import tempfile

import pytest

from unmanic import config


@pytest.mark.unittest
class TestWebAuthConfig(object):
    def _settings(self):
        config.Config._instances = {}
        return config.Config(config_path=tempfile.mkdtemp(prefix="unmanic_tests_"))

    def test_defaults_are_off_and_permissive_to_machines(self):
        settings = self._settings()
        assert settings.get_auth_enabled() is False
        assert settings.get_auth_allow_basic() is True
        assert settings.get_auth_session_idle_timeout_days() == 7
        assert settings.get_auth_session_max_age_days() == 30
        assert settings.get_auth_trusted_origins() == []

    def test_string_values_from_env_are_coerced(self):
        settings = self._settings()
        settings.set_config_item("auth_enabled", "true", save_settings=False)
        assert settings.get_auth_enabled() is True
        settings.set_config_item("auth_enabled", "false", save_settings=False)
        assert settings.get_auth_enabled() is False
        settings.set_config_item("auth_session_idle_timeout_days", "3", save_settings=False)
        assert settings.get_auth_session_idle_timeout_days() == 3

    def test_a_bare_string_does_not_read_as_enabled(self):
        # The bug this guards: "false" is a truthy Python string.
        settings = self._settings()
        settings.set_config_item("auth_enabled", "no", save_settings=False)
        assert settings.get_auth_enabled() is False

    def test_trusted_origins_accept_comma_separated_string(self):
        settings = self._settings()
        settings.set_config_item(
            "auth_trusted_origins", "https://a.example.com, https://b.example.com", save_settings=False
        )
        assert settings.get_auth_trusted_origins() == ["https://a.example.com", "https://b.example.com"]

    def test_invalid_numbers_fall_back_to_defaults(self):
        settings = self._settings()
        settings.set_config_item("auth_session_idle_timeout_days", "not-a-number", save_settings=False)
        assert settings.get_auth_session_idle_timeout_days() == 7
