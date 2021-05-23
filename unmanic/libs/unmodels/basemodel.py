#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.basemodel.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     22 Jun 2019, (1:58 PM)
 
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
from playhouse.sqliteq import SqliteQueueDatabase
from datetime import datetime
from base64 import b64decode
from playhouse.shortcuts import model_to_dict, dict_to_model

# Do not initialise the database until the model is called.
from unmanic.libs.singleton import SingletonType

db = DatabaseProxy()  # Create a proxy for our db.

# Stipulate date and time formats
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_ALT = '{}.%f'.format(TIME_FORMAT)
DATETIME_BASE = '{}T{}'
DATETIME_FORMAT = DATETIME_BASE.format(DATE_FORMAT, TIME_FORMAT)
DATETIME_FORMAT_ALT = DATETIME_BASE.format(DATE_FORMAT, TIME_FORMAT_ALT)


def strpdatetime(string):
    """
    Parses the datetime from a string.

    """
    if string is not None:
        try:
            return datetime.strptime(string, DATETIME_FORMAT)
        except ValueError:
            return datetime.strptime(string, DATETIME_FORMAT_ALT)


def strpdate(string):
    """
    Parses the date from a string.

    """
    if string is not None:
        return datetime.strptime(string, DATE_FORMAT).date()


def strptime(string):
    """
    Parses the time from a string.

    """
    if string is not None:
        try:
            return datetime.strptime(string, TIME_FORMAT).time()
        except ValueError:
            return datetime.strptime(string, TIME_FORMAT_ALT).time()


class NoSuchFieldError(TypeError):
    """
    Indicates that the field does not exist in this model

    """
    pass


class NullError(TypeError):
    """
    Indicates that the respective field was set to NULL but must not be NULL.

    """
    pass


class Database:
    """
    Database

    Select a database to connect to
    """

    @staticmethod
    def select_database(config):
        # Based on configuration, use a different database.
        if config['TYPE'] == 'SQLITE':
            # use SqliteQueueDatabase
            database = SqliteQueueDatabase(
                config['FILE'],
                use_gevent=False,
                autostart=True,
                queue_max_size=None,
                results_timeout=15.0,
                pragmas=(
                    ('foreign_keys', 1),
                    ('journal_mode', 'wal'),
                )
            )

            db.initialize(database)
            db.connect()
        return db


class BaseModel(Model):
    """
    BaseModel

    Generic configuration and methods used across all Model classes
    """

    class Meta:
        database = db

    def get_fields(self):
        """
        Return a dictionary of this models field metadata

        :return:
        """
        return self._meta.fields

    def get_current_field_values_dict(self):
        """
        Return a dictionary of this models fields and their current values

        :return:
        """
        return self.__data__

    def parse_field_value_by_type(self, field_id, value):
        """
        Fetches the field type for this field.
        Return the passed value with the correct type.

        :param field_id:
        :param value:
        :return:
        """
        model_fields = self.get_fields()

        if field_id not in model_fields.keys():
            raise NoSuchFieldError()

        # Set the field from model
        field = model_fields[field_id]

        if value is None:
            if not field.null:
                raise NullError()
            return value

        if isinstance(field, BooleanField):
            if isinstance(value, (bool, int)):
                return bool(value)
            elif value.lower() in ['t', 'true', '1']:
                return True
            elif value.lower() in ['f', 'false', '0']:
                return False
            return False
        elif isinstance(field, IntegerField):
            return int(value)
        elif isinstance(field, FloatField):
            return float(value)
        elif isinstance(field, DecimalField):
            return float(value)
        elif isinstance(field, DateTimeField):
            return strpdatetime(value)
        elif isinstance(field, DateField):
            return strpdate(value)
        elif isinstance(field, TimeField):
            return strptime(value)
        elif isinstance(field, BlobField):
            return b64decode(value)

        return value

    def model_to_dict(self):
        """
        Retrieve all related objects recursively and
        then converts the resulting objects to a dictionary.

        :return:
        """
        return model_to_dict(self, backrefs=True)
