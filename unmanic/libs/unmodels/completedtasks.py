#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.completedtasks.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     30 Sep 2019, (6:46 PM)
 
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


class CompletedTasks(BaseModel):
    """
    CompletedTasks
    """
    task_label = TextField(null=False)
    abspath = TextField(null=False, default='')
    task_success = BooleanField(null=False)
    start_time = DateTimeField(null=False, default=datetime.datetime.now)
    finish_time = DateTimeField(null=False, default=datetime.datetime.now)
    processed_by_worker = TextField(null=False)
