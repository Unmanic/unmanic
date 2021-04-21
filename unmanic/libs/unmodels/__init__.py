#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.__init__.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     22 Jun 2019, (1:47 PM)
 
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

from __future__ import absolute_import
import warnings

from .basemodel import BaseModel
from .basemodel import Database
from .basemodel import db
from .historictaskffmpeglog import HistoricTaskFfmpegLog
from .historictaskprobe import HistoricTaskProbe
from .historictaskprobestreams import HistoricTaskProbeStreams
from .historictasks import HistoricTasks
from .historictasksettings import HistoricTaskSettings
from .installation import Installation
from .migrations import Migrations
from .pluginflow import PluginFlow
from .pluginrepos import PluginRepos
from .plugins import Plugins
from .settings import Settings
from .taskprobe import TaskProbe
from .taskprobestreams import TaskProbeStreams
from .tasks import Tasks
from .tasksettings import TaskSettings

__author__ = 'Josh.5 (jsunnex@gmail.com)'

__all__ = (
    'BaseModel',
    'Database',
    'db',
    'HistoricTaskFfmpegLog',
    'HistoricTaskProbe',
    'HistoricTaskProbeStreams',
    'HistoricTasks',
    'HistoricTaskSettings',
    'Installation',
    'Migrations',
    'PluginFlow',
    'PluginRepos',
    'Plugins',
    'Settings',
    'TaskProbe',
    'TaskProbeStreams',
    'Tasks',
    'TaskSettings',
)
