#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.workerschedules.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     18 Apr 2022, (4:19 PM)

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

from unmanic.libs.unmodels import WorkerGroups
from unmanic.libs.unmodels.lib import BaseModel


class WorkerSchedules(BaseModel):
    """
    WorkerSchedules
    """
    repetition = TextField(null=False)
    schedule_task = TextField(null=False)
    schedule_time = TextField(null=False)
    schedule_worker_count = IntegerField(null=True)
    # Link to Worker Groups
    worker_group_id = ForeignKeyField(WorkerGroups, backref='worker_schedules', on_delete='CASCADE', on_update='CASCADE')
