#!/bin/bash
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jan 07 2019, (17:52:42 PM)
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

# This script is to setup a series of tests for the application


SCRIPT_PATH=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd );
PROJECT_BASE=$(realpath ${SCRIPT_PATH}/../../);


source "${SCRIPT_PATH}/download_test_files.sh"


### FUNCTIONS
# Install script dependencies:
setup_script_dependencies() {
    TO_INSTALL="";
    [[ ! -x $(command -v curl) ]] && TO_INSTALL="${TO_INSTALL} curl";
    if [[ "${TO_INSTALL}" != "" ]]; then
        echo "Missing dependencies - ${TO_INSTALL}";
        exit 0;
    fi
    python3 -m pip install --user --upgrade -r ${PROJECT_BASE}/requirements.txt
}


### RUN
setup_script_dependencies
fetch_test_videos
