#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.workergroups.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     18 Apr 2022, (4:15 PM)

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
from unmanic.libs.unmodels.tags import Tags


class WorkerGroups(BaseModel):
    """
    WorkerGroups
    """
    name = TextField(null=False)
    locked = BooleanField(null=False, default=False)
    number_of_workers = IntegerField(null=False, default=0)
    # ManyToMany Linking fields. Does not create a column in the DB. See linking table below
    tags = ManyToManyField(Tags, backref='tags')

# Generate linking table for the 'tags' field above
# https://docs.peewee-orm.com/en/latest/peewee/relationships.html#manytomanyfield
WorkerGroupTags = WorkerGroups.tags.get_through_model()
