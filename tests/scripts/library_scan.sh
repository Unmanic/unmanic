#!/bin/bash
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jan 07 2019, (17:59:00 PM)
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
PROJECT_BASE=$(realpath ${SCRIPT_PATH}/../../);
PUID=$(id -u);
PGID=$(id -g);


# Setup folders:
rm -rf ${PROJECT_BASE}/tests/tmp/library/path*
mkdir -p \
    ${PROJECT_BASE}/tests/tmp/library/path1 \
    ${PROJECT_BASE}/tests/tmp/library/path2 \
    ${PROJECT_BASE}/tests/tmp/library/path3 \
    ${PROJECT_BASE}/tests/tmp/library/path4


# Copy test files to test folders
cp -r ${PROJECT_BASE}/tests/videos/med/* ${PROJECT_BASE}/tests/tmp/library/path1/
cp -r ${PROJECT_BASE}/tests/videos/med/* ${PROJECT_BASE}/tests/tmp/library/path2/
cp -r ${PROJECT_BASE}/tests/videos/med/* ${PROJECT_BASE}/tests/tmp/library/path3/
cp -r ${PROJECT_BASE}/tests/videos/med/* ${PROJECT_BASE}/tests/tmp/library/path4/


# Set the config for the application so that it scans for files right away
DEBUGGING=${DEBUGGING:-true}
NUMBER_OF_WORKERS=${NUMBER_OF_WORKERS:-1}
SCHEDULE_FULL_SCAN_MINS=${SCHEDULE_FULL_SCAN_MINS:-10}
RUN_FULL_SCAN_ON_START=${RUN_FULL_SCAN_ON_START:-true}

for arg in ${@}; do
    if [[ ${arg} =~ '--clean' ]]; then
        rm -rf ${PROJECT_BASE}/tests/tmp/config;
    fi
done


# Run container
docker run -ti --rm \
    -p 8888:8888 \
    -v ${PROJECT_BASE}:/app \
    -v ${PROJECT_BASE}/cache:/tmp/unmanic \
    -v ${PROJECT_BASE}/tests/tmp/library:/library \
    -v ${PROJECT_BASE}/tests/tmp/config:/config \
    -e PUID=${PUID} \
    -e PGID=${PGID} \
    -e DEBUGGING=${DEBUGGING} \
    -e NUMBER_OF_WORKERS=${NUMBER_OF_WORKERS} \
    -e SCHEDULE_FULL_SCAN_MINS=${SCHEDULE_FULL_SCAN_MINS} \
    -e RUN_FULL_SCAN_ON_START=${RUN_FULL_SCAN_ON_START} \
    josh5/unmanic bash

