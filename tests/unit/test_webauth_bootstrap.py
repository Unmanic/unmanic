#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import os
import tempfile

import pytest

from tests.support_.webauth_db import create_test_database, destroy_test_database
from unmanic import config
from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials
from unmanic.libs.unmodels.webauthsessions import WebAuthSessions
from unmanic.libs.webauth import bootstrap, credentials

MODELS = [WebAuthCredentials, WebAuthSessions]


@pytest.mark.unittest
class TestEnvironmentBootstrap(object):
    def setup_method(self):
        self.db = create_test_database(MODELS)
        credentials.flush_verify_cache()
        config.Config._instances = {}
        self.config_path = tempfile.mkdtemp(prefix="unmanic_tests_")
        self.settings = config.Config(config_path=self.config_path)
        for key in (bootstrap.ENV_USERNAME, bootstrap.ENV_PASSWORD):
            os.environ.pop(key, None)

    def teardown_method(self):
        destroy_test_database(self.db, MODELS)
        for key in (bootstrap.ENV_USERNAME, bootstrap.ENV_PASSWORD):
            os.environ.pop(key, None)

    def test_no_environment_variables_is_a_no_op(self):
        bootstrap.apply_environment_credentials(self.settings)
        assert credentials.credential_is_configured() is False

    def test_environment_variables_create_the_account(self):
        os.environ[bootstrap.ENV_USERNAME] = "jordan"
        os.environ[bootstrap.ENV_PASSWORD] = "a-good-password"
        bootstrap.apply_environment_credentials(self.settings)
        assert credentials.verify_credential("jordan", "a-good-password") is True

    def test_the_plaintext_password_is_never_written_to_settings_json(self):
        os.environ[bootstrap.ENV_USERNAME] = "jordan"
        os.environ[bootstrap.ENV_PASSWORD] = "a-good-password"
        bootstrap.apply_environment_credentials(self.settings)
        self.settings.set_config_item("auth_enabled", True, save_settings=True)
        with open(os.path.join(self.config_path, "settings.json")) as handle:
            written = handle.read()
        assert "a-good-password" not in written
        assert "auth_password" not in written

    def test_reapplying_the_same_password_does_not_churn_the_hash(self):
        os.environ[bootstrap.ENV_USERNAME] = "jordan"
        os.environ[bootstrap.ENV_PASSWORD] = "a-good-password"
        bootstrap.apply_environment_credentials(self.settings)
        first = WebAuthCredentials.select().first().password_hash
        bootstrap.apply_environment_credentials(self.settings)
        assert WebAuthCredentials.select().first().password_hash == first

    def test_a_changed_environment_password_replaces_the_stored_one(self):
        os.environ[bootstrap.ENV_USERNAME] = "jordan"
        os.environ[bootstrap.ENV_PASSWORD] = "a-good-password"
        bootstrap.apply_environment_credentials(self.settings)
        os.environ[bootstrap.ENV_PASSWORD] = "a-different-password"
        bootstrap.apply_environment_credentials(self.settings)
        assert credentials.verify_credential("jordan", "a-different-password") is True

    def test_an_invalid_environment_password_does_not_crash_startup(self):
        os.environ[bootstrap.ENV_USERNAME] = "jordan"
        os.environ[bootstrap.ENV_PASSWORD] = "short"
        bootstrap.apply_environment_credentials(self.settings)
        assert credentials.credential_is_configured() is False

    def test_disable_auth_turns_the_setting_off(self):
        self.settings.set_config_item("auth_enabled", True, save_settings=False)
        bootstrap.run_disable_auth(self.settings)
        assert self.settings.get_auth_enabled() is False
