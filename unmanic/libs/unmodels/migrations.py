#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.migrations.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     22 Jun 2019, (8:01 PM)
 
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

import os
from peewee_migrate import Router
from peewee import *


class Migrations(object):
    """
    Migrations

    Handle all migrations during application start.
    """

    def __init__(self, config):
        # Based on configuration, select database to connect to.
        if config['TYPE'] == 'SQLITE':
            # Create SQLite directory if not exists
            db_file_directory = os.path.dirname(config['FILE'])
            if not os.path.exists(db_file_directory):
                os.makedirs(db_file_directory)
            database = SqliteDatabase(config['FILE'])
            self.router = Router(database=database, migrate_dir=config['MIGRATIONS_DIR'])

    def run_all(self):
        """
        Run all new migrations.
        Migrations that have already been run will be ignored.

        :return:
        """
        self.router.run()
