#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.setup.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     04 May 2020, (10:47 AM)
 
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
import json
import os
import shutil
import sys
import glob
from setuptools import setup, find_packages, Command
import setuptools.command.build_py
import versioninfo

if sys.version_info[0] < 3:
    print("This module version requires Python 3.")
    sys.exit(1)

project_root_dir = os.path.dirname(os.path.realpath(__file__))
src_dir = 'unmanic'

module_name = versioninfo.name()
module_version = versioninfo.version()
module_description = versioninfo.description()
module_author = versioninfo.author()
module_email = versioninfo.email()
module_url = versioninfo.url()
module_classifiers = [
    versioninfo.dev_status(),
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Developers',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Operating System :: POSIX :: Linux',
    'Operating System :: Unix',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Topic :: Multimedia :: Video :: Conversion',
    'Topic :: Internet :: WWW/HTTP',
]


class BuildPyCommand(setuptools.command.build_py.build_py):
    """Custom build command."""

    def run(self):
        setuptools.command.build_py.build_py.run(self)
        self.run_command('write-build-version')


class WriteVersionCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @staticmethod
    def run():
        version_file = os.path.join('.', 'build', 'lib', src_dir, 'version')
        data = {
            'short': versioninfo.version(),
            'long':  versioninfo.full_version(),
        }
        with open(version_file, 'w') as f:
            json.dump(data, f)


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @staticmethod
    def run():
        shutil.rmtree(os.path.abspath(os.path.join(os.path.dirname(__file__), 'build')), ignore_errors=True)
        shutil.rmtree(os.path.abspath(os.path.join(os.path.dirname(__file__), 'dist')), ignore_errors=True)
        shutil.rmtree(os.path.abspath(os.path.join(os.path.dirname(__file__), '*.pyc')), ignore_errors=True)
        shutil.rmtree(os.path.abspath(os.path.join(os.path.dirname(__file__), 'unmanic.egg-info')), ignore_errors=True)
        [shutil.rmtree(f) for f in glob.glob(src_dir + "/**/__pycache__", recursive=True)]


class FullVersionCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @staticmethod
    def run():
        print(versioninfo.full_version())


cmd_class = {
    'build_py':            BuildPyCommand,
    'write-build-version': WriteVersionCommand,
    'clean':               CleanCommand,
    'fullversion':         FullVersionCommand,
}


def requirements():
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'requirements.txt'))) as f:
        return f.read().splitlines()


def requirements_dev():
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'requirements-dev.txt'))) as f:
        return f.read().splitlines()


setup(
    name=module_name,
    version=module_version,
    author=module_author,
    author_email=module_email,
    maintainer=module_author,
    maintainer_email=module_email,
    description=module_description,
    url=module_url,
    classifiers=module_classifiers,
    install_requires=requirements(),
    extras_require={
        'dev': requirements_dev()
    },
    packages=[src_dir],
    entry_points={
        'console_scripts': [
            '%s=%s.service:main' % (module_name, module_name)
        ]
    },
    cmdclass=cmd_class,
)
