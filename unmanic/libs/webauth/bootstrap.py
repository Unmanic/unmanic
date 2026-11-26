#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import getpass
import os

from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.webauth import credentials, sessions

logger = UnmanicLogging.get_logger(name="WebAuthBootstrap")

# Read straight from the environment rather than through Config, so a plaintext password
# is never held on the config object and can never be written out to settings.json.
ENV_USERNAME = "auth_username"
ENV_PASSWORD = "auth_password"


def apply_environment_credentials(settings) -> None:
    """
    Configure the local web account from environment variables, if they are set.

    :param settings:
    :return:
    """
    username = os.environ.get(ENV_USERNAME)
    password = os.environ.get(ENV_PASSWORD)
    if not username or not password:
        return

    if credentials.verify_credential(username, password):
        # Already configured with exactly these credentials; leave the stored hash alone
        # rather than rehashing and invalidating every session on each restart.
        return

    try:
        credentials.set_credential(username, password)
    except ValueError as e:
        logger.error("Ignoring web authentication credentials from the environment: %s", str(e))
        return

    sessions.revoke_all_sessions()
    logger.warning(
        "Configured web authentication credentials from environment variables. Note that these "
        "remain visible to anyone able to run 'docker inspect' on this container."
    )


def run_set_password(settings) -> int:
    """
    Interactively set the local web account credentials and enable authentication.

    :param settings:
    :return:
    """
    print("Configure the Unmanic web UI sign in.")
    print("These credentials control access to this installation only.")
    print("")

    current = credentials.get_username()
    prompt = "Username [{}]: ".format(current) if current else "Username: "
    username = input(prompt).strip() or (current or "")
    if not username:
        print("A username is required.")
        return 1

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("The passwords entered did not match.")
        return 1

    try:
        credentials.set_credential(username, password)
    except ValueError as e:
        print(str(e))
        return 1

    revoked = sessions.revoke_all_sessions()
    settings.set_config_item("auth_enabled", True, save_settings=True)
    print("")
    print("Authentication is now enabled for user '{}'.".format(username))
    if revoked:
        print("Signed out {} existing browser session(s).".format(revoked))
    print("Restart Unmanic for the change to take effect.")
    return 0


def run_disable_auth(settings) -> int:
    """
    Disable authentication. This is the documented lockout recovery path.

    :param settings:
    :return:
    """
    sessions.revoke_all_sessions()
    settings.set_config_item("auth_enabled", False, save_settings=True)
    print("Authentication is now disabled. Restart Unmanic for the change to take effect.")
    return 0
