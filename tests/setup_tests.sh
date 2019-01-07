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


### CONFIGURE:
TEST_VIDEOS=" \
        https://sample-videos.com/video123/mkv/720/big_buck_bunny_720p_1mb.mkv \
        https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 \
        https://sample-videos.com/video123/flv/720/big_buck_bunny_720p_1mb.flv \
    "




### CHECK IF WE CAN RUN...
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RELEASE=$(lsb_release -sr);
RELEASE_MAJOR=$(lsb_release -sr | awk -F '.' '{print $1}');
CODENAME=$(lsb_release -sc);
if [[ ${OS_ID} =~ "linuxmint" ]]; then
    # Running Linux Mint...
    # Get Ubuntu codename for this release
    CODENAME=$(cat /etc/os-release | grep UBUNTU_CODENAME | awk -F'=' '{print $2}');
    if [[ ! "${RELEASE_MAJOR}" -ge "18" ]]; then
        echo "You need to run Linux Mint 18 or higher";
        exit 1;
    fi
else
    if [[ ! "${RELEASE_MAJOR}" -ge "16" ]]; then
        echo "You need to run Ubuntu 16 or higher"
        exit 1;
    fi
fi
DATE_STAMP=$(date +"%Y-%m-%d_%H-%M-%S");

# Setup apt install command
APT_ARGS="-y";
if [[ "${RELEASE_MAJOR}" -ge "18" ]]; then
    APT_ARGS+=" -n";
fi
APT_PACKAGES="";
APT_INSTALL_CMD="sudo apt-get install -y ";




### Create missing folders
mkdir -p \
    ${SCRIPT_DIR}/videos




### FUNCTIONS
# Install script dependencies:
setup_script_dependencies() {
    APT_TO_INSTALL="";
    [[ ! -x $(which curl) ]] && APT_TO_INSTALL="${APT_TO_INSTALL} curl";
    if [[ "${APT_TO_INSTALL}" != "" ]]; then
        stage_header "Installing script dependencies collection...";
        sudo apt-get update;
        ${APT_INSTALL_CMD} ${APT_TO_INSTALL};
    fi
}
# Fetch test media:
fetch_test_videos() {
    for url in ${TEST_VIDEOS}; do
        FILE="${url##*/}";
        if [[ ! -e ${SCRIPT_DIR}/videos/${FILE} ]]; then
            echo "Downloading ${url} -> ${SCRIPT_DIR}/videos/${FILE}"
            curl -L ${url} --output ${SCRIPT_DIR}/videos/${FILE};
        fi
    done
}



### RUN
setup_script_dependencies
fetch_test_videos

