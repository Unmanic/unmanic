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


if ! command -v grcat &> /dev/null; then
    echo "This script needs 'grcat' for formatting the logs."
    echo "You must first install the 'grc' package..."
    echo
    echo "  Debian/Ubuntu:  apt-get install grc"
    echo "  Arch Linux:     pacman -S grc"
    echo "  Fedora:         dnf install grc"
    exit 1
fi

# Parse args for what logs to tail and what filters to apply
log_dir="${unmanic_dev_logs_dir}"
logfiles="unmanic.log"
for ARG in ${@}; do
    case ${ARG} in
        --local)
            log_dir="${HOME}/.unmanic/logs";
            ;;
        --tornado)
            logfiles="${logfiles} tornado.log";
            ;;
        --filters*)
            # EG: ":DEBUG:"
            filters=$(echo ${ARG} | awk -F'=' '{print $2}');
            ;;
        *)
            echo "Unrecognised param. Exiting!"
            exit 1
            ;;
    esac
done

if [[ -z ${filters} ]]; then
    pushd "${log_dir}" || exit 1
    tail -fn10 ${logfiles} | grcat ${SCRIPT_PATH}/../docker/root/.grc.conf.unmanic.logs
    popd &> /dev/null || exit 1
else
    pushd "${log_dir}" || exit 1
    echo "Filter logs with '${filters}'"
    tail -fn10 ${logfiles} | stdbuf -o0 grep -v "${filters}" | grcat ${SCRIPT_PATH}/../docker/root/.grc.conf.unmanic.logs
    popd &> /dev/null || exit 1
fi
