#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.enabledplugins.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     07 Feb 2022, (1:25 PM)

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
from unmanic.libs.unmodels.libraries import Libraries
from unmanic.libs.unmodels.plugins import Plugins


class EnabledPlugins(BaseModel):
    """
    EnabledPlugins
    """
    library_id = ForeignKeyField(Libraries, backref='enabled_plugins', on_delete='CASCADE', on_update='CASCADE')
    plugin_id = ForeignKeyField(Plugins, backref='enabled_libraries', on_delete='CASCADE', on_update='CASCADE')
    plugin_name = TextField(null=False)
