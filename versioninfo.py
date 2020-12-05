#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.versioninfo.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     04 May 2020, (10:52 AM)
 
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

import io
import os
import subprocess
import sys

import unmanic.metadata as version_info

DESCRIPTION = "TEST"


def name():
    return str(version_info.__name)


def version():
    if is_git_vcs():
        git_version_info = get_git_version_info()
        return git_version_info['short']
    else:
        return str(version_info.__version__)


def full_version():
    if is_git_vcs():
        git_version_info = get_git_version_info()
        return git_version_info['long']
    else:
        return str(version_info.__version__)


def description():
    return str(version_info.__description__)


def author():
    return str(version_info.__author)


def email():
    return str(version_info.__email)


def url():
    """
    Fetch the URL from the project version_info

    :return:
    """
    return str(version_info.__website__)


def branch_version():
    return version()[:3]


def is_pre_release():
    """
    Returns either true if this is a alpha or beta release

    :return:
    """
    full_version_string = full_version()
    return "alpha" in full_version_string.lower() or "beta" in full_version_string.lower()


def dev_status():
    """
    Returns the python module Development Status classifier
    based on if the version string is alpha/beta or stable

    :return:
    """
    full_version_string = full_version()
    if 'alpha' in full_version_string.lower():
        return 'Development Status :: 3 - Alpha'
    elif 'beta' in full_version_string or 'rc' in full_version_string.lower():
        return 'Development Status :: 4 - Beta'
    else:
        return 'Development Status :: 5 - Production/Stable'


def changes():
    """
    Extract part of changelog pertaining to version.

    :return:
    """
    _version = version_info.__version__
    with io.open(os.path.join(get_base_dir(), "CHANGES.txt"), 'r', encoding='utf8') as f:
        lines = []
        for line in f:
            if line.startswith('====='):
                if len(lines) > 1:
                    break
            if lines:
                lines.append(line)
            elif line.startswith(_version):
                lines.append(line)
    return ''.join(lines[:-1])


def get_base_dir():
    return os.path.abspath(os.path.dirname(sys.argv[0]))


def is_git_vcs():
    """
    Checks if the build is executed from a git VCS root

    :return:
    """
    if subprocess.call(["git", "branch"], stderr=subprocess.STDOUT, stdout=open(os.devnull, 'w')) != 0:
        return False
    else:
        return True


def get_git_version_info():
    """
    Parse version information from git.

    Returns a long and short version string:
        eg. short   - 0.0.1                         (full release)
        eg. short   - 0.0.1b2                       (beta release)
        eg. short   - 0.0.1b2.post3                 (beta release with commits since the last tag)
        eg. long    - 0.0.1~68b3db6                 (full release)
        eg. long    - 0.0.1-beta2~68b3db6           (beta release)
        eg. long    - 0.0.1-beta2+68b3db6           (beta release with commits since the last tag)
        eg. long    - 0.0.1-beta2~68b3db6+dirty     (beta release with uncommitted changes)
        eg. long    - 0.0.1-beta2+68b3db6+dirty     (beta release with commits since the last tag & uncommitted changes)

    :return:
    """
    # Fetch the last tag
    last_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).strip().decode("utf-8")
    # Fetch the current commit ID
    current_commit = subprocess.check_output(["git", "rev-parse", "--verify", "--short", "HEAD"]).strip().decode("utf-8")

    # Create a long and short version string to return
    short_version_string = last_tag
    long_version_string = last_tag

    # Fetch the amount of commits since the last tag
    distance_since_last_tag = subprocess.check_output(
        ["git", "rev-list", last_tag + "..HEAD", "--count"]
    ).strip().decode("utf-8")

    # Normalize short version string (saves getting spammed with useless warnings from setuptools about it)
    if '-alpha' in short_version_string.lower():
        short_version_string = short_version_string.replace("-alpha", "a")
    elif '-beta' in short_version_string.lower():
        short_version_string = short_version_string.replace("-beta", "b")
    elif '-rc' in short_version_string.lower():
        short_version_string = short_version_string.replace("-rc", "rc")

    # Append a post tag if this is not a clean tagged build
    if int(distance_since_last_tag) > 0:
        # There are commits since the last tag
        # Modify the version strings
        short_version_string = '{}.post{}'.format(short_version_string, distance_since_last_tag)
        long_version_string = '{}+{}'.format(long_version_string, current_commit)
    else:
        long_version_string = '{}~{}'.format(long_version_string, current_commit)

    # Check if there are uncommitted changes on the directory
    git_diff_status = subprocess.check_output(
        "git diff-index --quiet HEAD -- || echo 'is_dirty'", shell=True
    ).strip().decode("utf-8")
    if git_diff_status == 'is_dirty':
        # There are commits since the last tag
        long_version_string = '{}+dirty'.format(long_version_string)

    return_dic = {
        'short': short_version_string,
        'long':  long_version_string
    }

    return return_dic
