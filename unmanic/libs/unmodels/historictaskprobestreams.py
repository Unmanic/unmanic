#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.historictaskprobestreams.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     02 Oct 2019, (7:03 PM)
 
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
from unmanic.libs.unmodels.historictaskprobe import HistoricTaskProbe


class HistoricTaskProbeStreams(BaseModel):
    """
    HistoricTaskProbeStreams
    """
    historictaskprobe_id = ForeignKeyField(HistoricTaskProbe)
    codec_type = TextField(null=False)
    codec_long_name = TextField(null=False)
    avg_frame_rate = TextField(null=False)
    bit_rate = TextField(null=False)
    coded_height = TextField(null=False)
    coded_width = TextField(null=False)
    height = TextField(null=False)
    width = TextField(null=False)
    duration = TextField(null=False)
    channels = TextField(null=False)
    channel_layout = TextField(null=False)
