#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import os
import shutil
import tempfile

from peewee import SqliteDatabase

from unmanic.libs.unmodels.lib import db

_temp_dirs = []


def create_test_database(models):
    """
    Create an isolated database for a test and create the given tables in it.

    Deliberately a plain SqliteDatabase rather than the SqliteQueueDatabase the
    application uses. The queue database executes statements on a worker thread holding
    its own connection, which does not observe DDL issued from the calling thread within
    a test - queries fail with "no such table" even though the table is on disk. The
    models bind to a DatabaseProxy, so pointing that proxy at a plain database gives the
    same model behaviour without the worker thread.

    A temporary file is used rather than ':memory:', which is private per connection.

    :param models:
    :return:
    """
    temp_dir = tempfile.mkdtemp(prefix="unmanic_tests_db_")
    _temp_dirs.append(temp_dir)
    database = SqliteDatabase(
        os.path.join(temp_dir, "test.db"),
        pragmas=(("foreign_keys", 1),),
    )
    db.initialize(database)
    database.connect(reuse_if_open=True)
    database.create_tables(models)
    return database


def destroy_test_database(database, models):
    """
    Drop the given tables and remove any temporary database directories.

    :param database:
    :param models:
    :return:
    """
    try:
        database.drop_tables(models)
    except Exception:
        pass
    try:
        database.close()
    except Exception:
        pass
    while _temp_dirs:
        shutil.rmtree(_temp_dirs.pop(), ignore_errors=True)
