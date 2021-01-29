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
TEST_VIDEOS_DIRECTORY=$(realpath ${SCRIPT_PATH}/../support_/videos);
TEMP_ENV=$(realpath ${SCRIPT_PATH}/../tmp/test_env);
PUID=$(id -u);
PGID=$(id -g);

source "${SCRIPT_PATH}/download_test_files.sh"

# Setup folders:
rm -rf ${TEMP_ENV}/library/path*
mkdir -p \
    ${TEMP_ENV}/library/path1 \
    ${TEMP_ENV}/library/path2 \
    ${TEMP_ENV}/library/path3 \
    ${TEMP_ENV}/library/path4


# Copy test files to test folders
cp -r ${TEST_VIDEOS_DIRECTORY}/small/* ${TEMP_ENV}/library/path1/
cp -r ${TEST_VIDEOS_DIRECTORY}/small/* ${TEMP_ENV}/library/path2/
cp -r ${TEST_VIDEOS_DIRECTORY}/small/* ${TEMP_ENV}/library/path3/
cp -r ${TEST_VIDEOS_DIRECTORY}/small/* ${TEMP_ENV}/library/path4/


# Set the config for the application so that it scans for files right away
DEBUGGING=${DEBUGGING:-true}
NUMBER_OF_WORKERS=${NUMBER_OF_WORKERS:-1}
SCHEDULE_FULL_SCAN_MINUTES=${SCHEDULE_FULL_SCAN_MINUTES:-10}
RUN_FULL_SCAN_ON_START=${RUN_FULL_SCAN_ON_START:-true}


# Parse args
for arg in ${@}; do
    # If clean is passed, clear out the config prior to running
    if [[ ${arg} =~ '--clean' ]]; then
        rm -rf ${TEMP_ENV}/config;
    fi
done


# Run container
docker run -ti --rm \
    -p 8888:8888 \
    -v ${PROJECT_BASE}/:/app \
    -v ${TEMP_ENV}/cache:/tmp/unmanic \
    -v ${TEMP_ENV}/library:/library \
    -v ${TEMP_ENV}/config:/config \
    -e PUID=${PUID} \
    -e PGID=${PGID} \
    -e DEBUGGING=${DEBUGGING} \
    -e NUMBER_OF_WORKERS=${NUMBER_OF_WORKERS} \
    -e SCHEDULE_FULL_SCAN_MINUTES=${SCHEDULE_FULL_SCAN_MINUTES} \
    -e RUN_FULL_SCAN_ON_START=${RUN_FULL_SCAN_ON_START} \
    josh5/unmanic bash

