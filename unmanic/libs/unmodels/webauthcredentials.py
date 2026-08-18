#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import datetime

from peewee import DateTimeField, TextField

from unmanic.libs.unmodels.lib import BaseModel


class WebAuthCredentials(BaseModel):
    """
    WebAuthCredentials

    The local web UI account. At most one row exists.

    This is unrelated to unmanic.libs.session, which holds the unmanic.app
    supporter account used to unlock features.
    """

    username = TextField(null=False, unique=True)
    password_hash = TextField(null=False)
    created = DateTimeField(null=False, default=datetime.datetime.now)
    updated = DateTimeField(null=False, default=datetime.datetime.now)
