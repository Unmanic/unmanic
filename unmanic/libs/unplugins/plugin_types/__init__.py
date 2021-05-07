#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (8:12 PM)

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

import os
from importlib import import_module
from pathlib import Path
import sys
import inspect
import pkgutil

from .plugin_type_base import PluginType

d = os.path.join(Path(__file__).parent)
type_modules_paths = [os.path.join(d, o) for o in os.listdir(d) if os.path.isdir(os.path.join(d, o)) and not o.startswith('_')]


def grab_module(module_name, *args, **kwargs):
    """
    Fetch a module by name and return the instance of that class

    :param module_name:
    :param args:
    :param kwargs:
    :return:
    """
    try:
        if '.' in module_name:
            module_name, class_name = module_name.rsplit('.', 1)
        else:
            class_name = module_name.capitalize()

        module = import_module('.' + module_name, package=__name__)
        module_class = getattr(module, class_name)
        instance = module_class(*args, **kwargs)

        return instance

    except (AttributeError, AssertionError, ModuleNotFoundError):
        raise ImportError('{} is not part of our supported plugin types!'.format(module_name))


def get_all_plugin_types():
    """
    Fetch a list of supported plugin types and
    return a dictionary of their data

    :return:
    """
    return_dic = {}

    for type_modules_path in type_modules_paths:
        plugin_type = os.path.basename(Path(type_modules_path))
        for (_, module_name, _) in pkgutil.iter_modules([type_modules_path]):
            instance = grab_module(plugin_type + '.' + module_name)
            return_data = {
                "name": instance.plugin_type_name(),
                "runner": instance.plugin_runner(),
                "runner_docstring": instance.plugin_runner_docstring(),
            }
            return_dic[plugin_type + '.' + module_name] = return_data

    return return_dic


"""
Import all submodules for this package

"""
for type_modules_path in type_modules_paths:
    plugin_type = os.path.basename(Path(type_modules_path))
    for (_, name, _) in pkgutil.iter_modules([type_modules_path]):

        imported_module = import_module('.' + plugin_type + '.' + name, package=__name__)

        for i in dir(imported_module):
            attribute = getattr(imported_module, i)

            if inspect.isclass(attribute) and issubclass(attribute, PluginType):
                setattr(sys.modules[__name__], name, attribute)

__author__ = 'Josh.5 (jsunnex@gmail.com)'

__all__ = (
    'PluginType',
)
