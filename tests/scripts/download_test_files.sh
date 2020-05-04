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


### CONFIGURE:
# https://standaloneinstaller.com/blog/big-list-of-sample-videos-for-testers-124.html
SMALL_TEST_VIDEOS=" \
        https://sample-videos.com/video123/mkv/720/big_buck_bunny_720p_1mb.mkv \
        https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 \
        https://sample-videos.com/video123/flv/720/big_buck_bunny_720p_1mb.flv \
        http://mirrors.standaloneinstaller.com/video-sample/grb_2.3gp \
    "
MED_TEST_VIDEOS=" \
        https://sample-videos.com/video123/mkv/720/big_buck_bunny_720p_10mb.mkv \
        https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_10mb.mp4 \
        https://sample-videos.com/video123/flv/720/big_buck_bunny_720p_10mb.flv \
        https://sample-videos.com/video123/3gp/240/big_buck_bunny_240p_10mb.3gp \
        https://github.com/Matroska-Org/matroska-test-files/raw/master/test_files/test5.mkv \
        https://github.com/Matroska-Org/matroska-test-files/raw/master/test_files/test8.mkv \
    "
# http://www.engr.colostate.edu/me/facil/dynamics/files/flame.avi <- single stream (not supported yet)
# https://github.com/Matroska-Org/matroska-test-files
#   - test5.mkv = Multiple audio/subtitles
#   - test8.mkv = Audio gap
FAULTY_TEST_VIDEOS=" \
        https://github.com/Matroska-Org/matroska-test-files/raw/master/test_files/test5.mkv \
        https://github.com/Matroska-Org/matroska-test-files/raw/master/test_files/test8.mkv \
    "


### FUNCTIONS
# Fetch test media:
fetch_test_videos() {
    mkdir -p \
        ${PROJECT_BASE}/tests/videos/small \
        ${PROJECT_BASE}/tests/videos/med \
        ${PROJECT_BASE}/tests/videos/faulty
    for url in ${SMALL_TEST_VIDEOS}; do
        FILE="${url##*/}";
        if [[ ! -e ${PROJECT_BASE}/tests/videos/small/${FILE} ]]; then
            echo "Downloading ${url} -> ${PROJECT_BASE}/tests/videos/small/${FILE}"
            curl -L ${url} --output ${PROJECT_BASE}/tests/videos/small/${FILE};
        fi
    done
    for url in ${MED_TEST_VIDEOS}; do
        FILE="${url##*/}";
        if [[ ! -e ${PROJECT_BASE}/tests/videos/med/${FILE} ]]; then
            echo "Downloading ${url} -> ${PROJECT_BASE}/tests/videos/med/${FILE}"
            curl -L ${url} --output ${PROJECT_BASE}/tests/videos/med/${FILE};
        fi
    done
    for url in ${FAULTY_TEST_VIDEOS}; do
        FILE="${url##*/}";
        if [[ ! -e ${PROJECT_BASE}/tests/videos/faulty/${FILE} ]]; then
            echo "Downloading ${url} -> ${PROJECT_BASE}/tests/videos/faulty/${FILE}"
            curl -L ${url} --output ${PROJECT_BASE}/tests/videos/faulty/${FILE};
        fi
    done
}


### RUN
fetch_test_videos
