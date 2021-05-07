#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.__init__.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Sep 2019, (8:06 PM)
 
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
from importlib import import_module
from pathlib import Path
import os
import sys
import inspect
import pkgutil

from ..base_containers import Containers


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
        raise ImportError('{} is not part of our supported containers!'.format(module_name))


def get_all_containers():
    """
    Fetch a list of supported containers and
    return a dictionary of their data

    :return:
    """
    containers_dic = {}

    for (_, module_name, _) in pkgutil.iter_modules([os.path.join(Path(__file__).parent)]):
        instance = grab_module(module_name)
        container_data = {
            "extension":          instance.container_extension(),
            "description":        instance.container_description(),
            "supports_subtitles": instance.container_supports_subtitles(),
        }
        containers_dic[module_name] = container_data

    return containers_dic


"""
Import all submodules for this package

"""
for (_, name, _) in pkgutil.iter_modules([os.path.join(Path(__file__).parent)]):

    imported_module = import_module('.' + name, package=__name__)

    for i in dir(imported_module):
        attribute = getattr(imported_module, i)

        if inspect.isclass(attribute) and issubclass(attribute, Containers):
            setattr(sys.modules[__name__], name, attribute)

__author__ = 'Josh.5 (jsunnex@gmail.com)'

__all__ = (
    'Containers',
)
