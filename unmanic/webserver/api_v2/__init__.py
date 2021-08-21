#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Oct 2020, (9:07 PM)

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

from .docs_api import ApiDocsHandler
from .filebrowser_api import ApiFilebrowserHandler
from .history_api import ApiHistoryHandler
from .pending_api import ApiPendingHandler
from .plugins_api import ApiPluginsHandler
from .session_api import ApiSessionHandler
from .settings_api import ApiSettingsHandler
from .version_api import ApiVersionHandler
from .workers_api import ApiWorkersHandler

__author__ = 'Josh.5 (jsunnex@gmail.com)'

__all__ = (
    'ApiDocsHandler',
    'ApiFilebrowserHandler',
    'ApiHistoryHandler',
    'ApiPendingHandler',
    'ApiPluginsHandler',
    'ApiSessionHandler',
    'ApiSettingsHandler',
    'ApiVersionHandler',
    'ApiWorkersHandler'
)


def list_all_handlers():
    return __all__
