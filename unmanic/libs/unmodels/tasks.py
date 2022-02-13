#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.tasks.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 May 2020, (3:27 PM)

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

from peewee import *
from unmanic.libs.unmodels.lib import BaseModel


class Tasks(BaseModel):
    """
    Tasks
    """
    abspath = TextField(null=False, unique=True)
    cache_path = TextField(null=True, unique=True)
    priority = BigIntegerField(null=True)
    type = TextField(null=False, default='local')  # (local, remote)
    library_id = IntegerField(null=False, default=1)
    status = TextField(null=False)  # (pending, in_progress, processed)
    success = BooleanField(null=True)
    start_time = DateTimeField(null=True, default=datetime.datetime.now)
    finish_time = DateTimeField(null=True, default=datetime.datetime.now)
    processed_by_worker = TextField(null=True)
    log = TextField(null=False, default='')
