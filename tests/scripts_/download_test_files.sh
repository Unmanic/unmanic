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
TEST_VIDEOS_DIRECTORY="${PROJECT_BASE}/tests/support_/videos";

### CONFIGURE:
## Sources:
#   - https://standaloneinstaller.com/blog/big-list-of-sample-videos-for-testers-124.html
declare -A SMALL_TEST_VIDEOS=(
    ['big_buck_bunny_720p_1mb.mp4']='https://drive.google.com/uc?id=1p0axETh8CKlL-oKPNaHAh786sr06hOAi&authuser=0&export=download'
    ['big_buck_bunny_720p_1mb.mkv']='https://drive.google.com/uc?id=11Zx1h1yiTnKkZJSXj0VVvLssIBgYiHv7&authuser=0&export=download'
    ['big_buck_bunny_720p_1mb.flv']='https://drive.google.com/uc?id=1k8um0-Hn9fOYpoR4gkYY2rRWfZZq1CGj&authuser=0&export=download'
    ['big_buck_bunny_144p_1mb.3gp']='https://drive.google.com/uc?id=1DjGbUsuhawb3Y-a3HkD2puodu232ZA1Q&authuser=0&export=download'
)
declare -A MED_TEST_VIDEOS=(
    ['big_buck_bunny_720p_10mb.mp4']='https://drive.google.com/uc?id=1qAYTFtEwfCcgFjLuPCoJJGWwzYki8SbG&authuser=0&export=download'
    ['big_buck_bunny_720p_10mb.mkv']='https://drive.google.com/uc?id=1FdXRRB0TX6QMx2HmZScPW2gZqMx17Lbq&authuser=0&export=download'
    ['big_buck_bunny_720p_10mb.flv']='https://drive.google.com/uc?id=1keev_0qoJMMNv7bzLxv_E0v1ugTjmMbB&authuser=0&export=download'
    ['big_buck_bunny_240p_10mb.3gp']='https://drive.google.com/uc?id=1OQBGz8P-scmrefxoEWcuIm4eNhlOI6eZ&authuser=0&export=download'
)
# http://www.engr.colostate.edu/me/facil/dynamics/files/flame.avi <- single stream (not supported yet)
# https://github.com/Matroska-Org/matroska-test-files
#   - test5.mkv = Multiple audio/subtitles
#   - test8.mkv = Audio gap
declare -A FAULTY_TEST_VIDEOS=(
    ['matroska-test-files-test5.mkv']='https://drive.google.com/uc?id=16vdt6FEOIeUdCG9r-3FZDq5tDD4nMtMp&authuser=0&export=download'
    ['matroska-test-files-test8.mkv']='https://drive.google.com/uc?id=16vdt6FEOIeUdCG9r-3FZDq5tDD4nMtMp&authuser=0&export=download'
)


### FUNCTIONS
# Fetch test media:
fetch_test_videos() {
    mkdir -p \
        ${TEST_VIDEOS_DIRECTORY}/small \
        ${TEST_VIDEOS_DIRECTORY}/med \
        ${TEST_VIDEOS_DIRECTORY}/faulty

    for DEST_FILE in "${!SMALL_TEST_VIDEOS[@]}"; do
        URL=${SMALL_TEST_VIDEOS[$DEST_FILE]}
        DEST_PATH=${TEST_VIDEOS_DIRECTORY}/small/${DEST_FILE}
        if [[ ! -e ${DEST_PATH} ]]; then
            echo "Downloading ${URL} -> ${DEST_PATH}"
            curl -sSL ${URL} --output ${DEST_PATH};
        fi
    done
    for DEST_FILE in "${!MED_TEST_VIDEOS[@]}"; do
        URL=${MED_TEST_VIDEOS[$DEST_FILE]}
        DEST_PATH=${TEST_VIDEOS_DIRECTORY}/med/${DEST_FILE}
        if [[ ! -e ${DEST_PATH} ]]; then
            echo "Downloading ${URL} -> ${DEST_PATH}"
            curl -sSL ${URL} --output ${DEST_PATH};
        fi
    done
    for DEST_FILE in "${!FAULTY_TEST_VIDEOS[@]}"; do
        URL=${FAULTY_TEST_VIDEOS[$DEST_FILE]}
        DEST_PATH=${TEST_VIDEOS_DIRECTORY}/faulty/${DEST_FILE}
        if [[ ! -e ${DEST_PATH} ]]; then
            echo "Downloading ${URL} -> ${DEST_PATH}"
            curl -sSL ${URL} --output ${DEST_PATH};
        fi
    done
}


### RUN
fetch_test_videos
