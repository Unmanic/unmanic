#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.database.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     14 Aug 2021, (12:03 PM)

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
import importlib
import inspect
import os
import sys

from peewee import Model, SqliteDatabase, Field
from peewee_migrate import Migrator, Router

from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.unmodels.lib import BaseModel


class Migrations(object):
    """
    Migrations

    Handle all migrations during application start.
    """

    database = None

    def __init__(self, config):
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)

        # Based on configuration, select database to connect to.
        if config['TYPE'] == 'SQLITE':
            # Create SQLite directory if not exists
            db_file_directory = os.path.dirname(config['FILE'])
            if not os.path.exists(db_file_directory):
                os.makedirs(db_file_directory)
            self.database = SqliteDatabase(
                config['FILE'],
                pragmas=(
                    ('foreign_keys', 1),
                    ('journal_mode', 'wal'),
                ),
            )

            self.router = Router(database=self.database,
                                 migrate_table='migratehistory_{}'.format(config.get('MIGRATIONS_HISTORY_VERSION')),
                                 migrate_dir=config.get('MIGRATIONS_DIR'),
                                 logger=self.logger)

            self.migrator = Migrator(self.database)

    def __run_all_migrations(self):
        """
        Run all new migrations.
        Migrations that have already been run will be ignored.

        :return:
        """
        self.router.run()

    def update_schema(self):
        """
        Bring the database schema up-to-date at application startup.

        This function intentionally does a two-step upgrade:

        1) Auto-sync (additive baseline):
        - Create any missing tables for the discovered models.
        - Add any missing columns to existing tables.
        - Add any missing non-unique indexes declared on models (simple column-name indexes only).

        This step is designed to make a new or slightly-behind database usable
        without requiring hand-written migrations for simple additions.

        2) Explicit migrations (non-additive changes):
        - Run peewee-migrate scripts to perform schema changes that SQLite (and
            this auto-sync) cannot safely or reliably do, e.g.:
            - rename tables/columns
            - drop tables/columns
            - rebuild tables to change constraints (FK/UNIQUE/NOT NULL) or to
                enforce new FK constraints
            - create/modify/drop indexes that are unique, partial, or expression-based
            - data migrations/backfills

        IMPORTANT:
        Because tables/columns are created/added *before* migrations run, migration
        scripts must NOT create tables or add columns unconditionally. Migrations
        must be written defensively (e.g. IF NOT EXISTS for indexes) to avoid
        clashes on fresh installs and should focus on the non-additive operations above.

        NOTE:
        Auto-added indexes are matched only on simple column lists and do not account
        for partial indexes or expression indexes. Any special index requirements
        should be handled explicitly in migrations.

        :return:
        """
        # Fetch all model classes
        discovered_models = inspect.getmembers(sys.modules["unmanic.libs.unmodels"], inspect.isclass)
        all_models = [tup[1] for tup in discovered_models]

        # Start by creating all models
        self.logger.info("Initialising database tables")
        try:
            with self.database.transaction():
                for model in all_models:
                    self.migrator.create_table(model)
                self.migrator()
        except Exception:
            self.database.rollback()
            self.logger.exception("Initialising tables failed")
            raise

        # Migrations will only be used for removing obsolete columns
        self.__run_all_migrations()

        # Newly added fields can be auto added with this function... no need for a migration script
        # Ensure all files are also present for each of the model classes
        self.logger.info("Updating database fields")
        missing_required_columns = []
        for model in all_models:
            if issubclass(model, BaseModel):
                # Fetch all peewee fields for the model class
                # https://stackoverflow.com/questions/22573558/peewee-determining-meta-data-about-model-at-run-time
                fields = model._meta.fields
                table_name = model._meta.table_name
                # loop over the fields and ensure each on exists in the table
                field_keys = [f for f in fields]
                for fk in field_keys:
                    field = fields.get(fk)
                    if isinstance(field, Field):
                        column_name = getattr(field, 'column_name', field.name)
                        if getattr(field, 'primary_key', False):
                            # SQLite cannot safely add primary key columns via ALTER TABLE.
                            # These must be handled explicitly in migrations if ever required.
                            if not any(f for f in self.database.get_columns(table_name) if f.name == column_name):
                                missing_required_columns.append((table_name, column_name, "primary key"))
                            continue
                        if not field.null and field.default is None:
                            # Non-null columns without a default cannot be added safely.
                            if not any(f for f in self.database.get_columns(table_name) if f.name == column_name):
                                missing_required_columns.append((table_name, column_name, "non-null without default"))
                            continue
                        if not any(f for f in self.database.get_columns(table_name) if f.name == column_name):
                            # Field does not exist in DB table
                            self.logger.info("Adding missing column")
                            try:
                                with self.database.transaction():
                                    self.migrator.add_columns(model, **{field.name: field})
                                    self.migrator()
                            except Exception:
                                self.database.rollback()
                                self.logger.exception("Update failed")
                                raise

        if missing_required_columns:
            details = "; ".join(
                "{}.{} ({})".format(table, column, reason)
                for table, column, reason in missing_required_columns
            )
            raise RuntimeError(
                "Database schema requires non-additive migrations for: {}. "
                "Create a migration to add these columns safely.".format(details)
            )

        # Add missing non-unique indexes declared on models
        self.logger.info("Updating database indexes")
        for model in all_models:
            if not issubclass(model, BaseModel):
                continue

            table_name = model._meta.table_name
            try:
                existing_indexes = self.database.get_indexes(table_name)
            except Exception:
                self.logger.exception("Failed to fetch indexes for table %s", table_name)
                continue

            existing_index_columns = set(
                tuple(getattr(idx, 'columns', []))
                for idx in existing_indexes
            )
            existing_index_names = set(
                getattr(idx, 'name', None)
                for idx in existing_indexes
                if getattr(idx, 'name', None)
            )

            declared_indexes = []
            for columns, unique in model._meta.indexes:
                if unique:
                    continue
                if all(isinstance(col, str) for col in columns):
                    compare_columns = []
                    for col in columns:
                        field = model._meta.fields.get(col)
                        compare_columns.append(field.column_name if field else col)
                    declared_indexes.append((tuple(columns), tuple(compare_columns)))

            for field_name, field in model._meta.fields.items():
                if getattr(field, 'index', False) and not getattr(field, 'unique', False):
                    declared_indexes.append(((field_name,), (field.column_name,)))

            for add_columns, compare_columns in declared_indexes:
                if compare_columns in existing_index_columns:
                    continue
                index_name = "{}_{}".format(table_name, "_".join(compare_columns))
                if index_name in existing_index_names:
                    continue
                try:
                    self.logger.info("Adding missing index on %s (%s)", table_name, ", ".join(add_columns))
                    with self.database.transaction():
                        self.migrator.add_index(model, *add_columns, unique=False)
                        self.migrator()
                except Exception:
                    self.database.rollback()
                    self.logger.exception("Failed to add index %s on table %s", add_columns, table_name)
                    raise
