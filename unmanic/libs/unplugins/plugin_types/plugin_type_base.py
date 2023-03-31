#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.plugin_type_base.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (8:09 PM)

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
import inspect
import json
from copy import deepcopy


class PluginType(object):
    """
    PluginType

    Generic configuration and methods used across all plugin types
    """
    name = ''
    runner = ''
    runner_docstring = ''
    data_schema = {}
    test_data = {}

    def plugin_type_name(self):
        """
        Return the plugin runner string

        :return:
        """
        return self.name

    def plugin_runner(self):
        """
        Return the plugin runner string

        :return:
        """
        return self.runner

    def plugin_runner_docstring(self):
        """
        Return the plugin runner docstring

        :return:
        """
        return self.runner_docstring

    def get_plugin_runner_function(self, plugin_module):
        plugin_runner = self.plugin_runner()
        # Check if this module contains the given plugin type runner function
        if hasattr(plugin_module, plugin_runner):
            # If it does, add it to the plugin_modules list
            return getattr(plugin_module, plugin_runner)
        return None

    def get_data_schema(self):
        """
        Return the plugin data schema dictionary

        :return:
        """
        return self.data_schema

    def get_test_data(self):
        """
        Return the plugin test data dictionary

        :return:
        """
        return self.test_data

    @staticmethod
    def modify_test_data(d: dict, v: dict):
        dict_str = json.dumps(d)
        for a, b in v.items():
            dict_str = dict_str.replace(a, b)
        return json.loads(dict_str)

    def __data_schema_test_data(self, plugin_id, plugin_runner, result_data, data_schema, data_tree="/"):
        """
        Ensure the test data returned is valid according to the schema

        :param plugin_id:
        :param plugin_runner:
        :param result_data:
        :param data_schema:
        :param data_tree:
        :return:
        """

        def test_data_type(provided_data, expected_data_type):
            # Test for NoneType
            # Callable functions are best tested with the callable function
            # Everything else should be tested with the isinstance function
            if provided_data is None and expected_data_type is None:
                return True
            elif expected_data_type == 'callable':
                if callable(provided_data):
                    return True
            elif isinstance(provided_data, expected_data_type):
                return True
            return False

        errors = []
        if not isinstance(result_data, dict):
            # This runner function is not returning anything
            error = "Plugin '{0} - {1}()' has failed to return any output data.".format(plugin_id, plugin_runner, data_tree)
            errors.append(error)
            return errors
        for key in data_schema:
            schema_meta = data_schema.get(key)
            if schema_meta.get('required'):
                # Ensure the required item is present in result_data
                if not key in result_data:
                    error = "Plugin '{0} - {1}()' is missing required key '{2}{3}' in the output data.".format(plugin_id,
                                                                                                               plugin_runner,
                                                                                                               data_tree, key)
                    errors.append(error)

            # Ensure that data present is of the correct type
            # Recursively check for children elements
            data_type = schema_meta.get('type')
            if key in result_data:
                child_data = result_data.get(key)

                # Test that the data is of the correct type
                # Types can be multiple things for some plugin runners. If type is a list of types,
                #   iterate over that list and test all types.
                correct_type = False
                if isinstance(data_type, list):
                    for dt in data_type:
                        if test_data_type(child_data, dt):
                            correct_type = True
                            break
                else:
                    correct_type = test_data_type(child_data, data_type)

                # If data is not of the correct type, then append the error message
                if not correct_type:
                    error = "Plugin '{0} - {1}()' output data returned incorrect data type in key '{2}{3}'. " \
                            "Expected '{4}', but received '{5}'.".format(plugin_id, plugin_runner,
                                                                         data_tree, key, data_type,
                                                                         type(result_data.get(key)))
                    errors.append(error)
                # Check if data_schema has children
                children_data_schema = schema_meta.get('children')
                if children_data_schema:
                    child_data_tree = "{}{}>".format(data_tree, key)
                    errors += self.__data_schema_test_data(plugin_id, plugin_runner, child_data, children_data_schema,
                                                           data_tree=child_data_tree)

        return errors

    def run_data_schema_tests(self, plugin_id, plugin_module, test_data):
        """
        With a given set of test data, this method tests the provided
        plugin module's data output against the schema dictionary.

        :param plugin_id:
        :param plugin_module:
        :param test_data:
        :return:
        """
        plugin_runner = self.plugin_runner()
        plugin_runner_function = self.get_plugin_runner_function(plugin_module)

        # Get test data
        if not test_data:
            test_data = self.get_test_data()
        test_data_copy = deepcopy(test_data)

        # Get data schema
        data_schema = self.get_data_schema()

        # Execute plugin function
        run_count = 0
        while run_count < 2:
            plugin_runner_function(test_data_copy)
            if not test_data_copy.get('repeat', False):
                break
            run_count += 1

        # Ensure the modified test data is valid according to the schema
        errors = self.__data_schema_test_data(plugin_id, plugin_runner, test_data_copy, data_schema)

        return errors
