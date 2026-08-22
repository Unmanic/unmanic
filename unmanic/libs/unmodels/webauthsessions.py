#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import datetime

from peewee import CharField, DateTimeField, TextField

from unmanic.libs.unmodels.lib import BaseModel


class WebAuthSessions(BaseModel):
    """
    WebAuthSessions

    Live browser sessions for the local web account.

    Only the SHA-256 of each session token is stored, so a leaked database yields
    nothing that can be replayed as a session.
    """

    token_hash = CharField(null=False, unique=True, index=True, max_length=64)
    created = DateTimeField(null=False, default=datetime.datetime.now)
    last_used = DateTimeField(null=False, default=datetime.datetime.now)
    expires = DateTimeField(null=False, default=datetime.datetime.now)
    remote_addr = TextField(null=True)
    user_agent = TextField(null=True)
