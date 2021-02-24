#!/bin/bash
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Oct 21 2020, (15:47:00 PM)
#
#   Copyright:
#          Copyright (C) Josh Sunnex - All Rights Reserved
#
#          Permission is hereby granted, free of charge, to any person obtaining a copy
#          of this software and associated documentation files (the "Software"), to deal
#          in the Software without restriction, including without limitation the rights
#          to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#          copies of the Software, and to permit persons to whom the Software is
#          furnished to do so, subject to the following conditions:
#
#          The above copyright notice and this permission notice shall be included in all
#          copies or substantial portions of the Software.
#
#          THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#          EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#          MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#          IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#          DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#          OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#          OR OTHER DEALINGS IN THE SOFTWARE.
#
#
###################################################################################################


SCRIPT_PATH=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd );

config_dir=${SCRIPT_PATH}/../dev_environment/config
unmanic_dev_logs_dir=${config_dir}/.unmanic/logs


if ! command -v grcat; then
    echo "This script needs 'grcat' for formatting the logs."
    echo "You must first install the 'grc' package..."
    echo
    echo "  Debian/Ubuntu:  apt-get install grc"
    echo "  Arch Linux:     pacman -S grc"
    echo "  Fedora:         dnf install grc"
    exit 1
fi

# Tail all current log files:
#filters=":DEBUG:"
filters=""
if [[ -z ${filters} ]]; then
    tail -fn10 ${unmanic_dev_logs_dir}/*.log | grcat ${SCRIPT_PATH}/../.grc.conf.unmanic.logs
else
    tail -fn10 ${unmanic_dev_logs_dir}/*.log | stdbuf -o0 grep -v "${filters}" | grcat ${SCRIPT_PATH}/../.grc.conf.unmanic.logs
fi


