#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.taskprobe.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 May 2020, (6:35 PM)

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
from unmanic.libs.unmodels.basemodel import BaseModel
from unmanic.libs.unmodels.tasks import Tasks


class TaskProbe(BaseModel):
    """
    TaskProbe
    """
    task_id = ForeignKeyField(Tasks, backref='probe', on_delete='CASCADE', on_update='CASCADE')
    abspath = TextField(null=False)
    basename = TextField(null=False)
    bit_rate = TextField(null=False)
    format_long_name = TextField(null=False)
    format_name = TextField(null=False)
    size = TextField(null=False)
    duration = TextField(null=False)
