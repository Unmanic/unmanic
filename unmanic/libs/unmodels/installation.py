#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.installation.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Mar 2021, (6:52 AM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import datetime
import uuid
from peewee import *

from unmanic.libs.unmodels.lib import BaseModel


class Installation(BaseModel):
    """
    Installation

    All application installation data
    """
    uuid = UUIDField(null=False, default=uuid.uuid4, unique=True)
    # Store session data here to persist restarts
    level = IntegerField(null=False, default=0)
    picture_uri = TextField(null=True)
    name = TextField(null=True)
    email = TextField(null=True)
    created = DateTimeField(null=True, default=datetime.datetime.now)

    # Store session tokens
    user_access_token = TextField(null=True)
    session_cookies = TextField(null=True)
