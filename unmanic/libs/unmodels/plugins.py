#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugins.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (2:11 PM)

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

from peewee import *
from unmanic.libs.unmodels.lib import BaseModel


class Plugins(BaseModel):
    """
    Plugins
    """
    plugin_id = TextField(null=False, unique=True)
    name = TextField(null=False)
    author = TextField(null=False)
    version = TextField(null=False)
    tags = TextField(null=False)
    description = TextField(null=False)
    icon = TextField(null=False)
    local_path = TextField(null=False)
    # NOTE: Enabled plugins here is deprecated. This is kept for compatibility with older DB
    enabled = BooleanField(null=True, default=False)
    update_available = BooleanField(null=False, default=False)
    position = IntegerField(null=False, default=9999)
