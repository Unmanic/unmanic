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
PROJECT_BASE=$(realpath ${SCRIPT_PATH}/..);
PUID=$(id -u);
PGID=$(id -g);

for arg in ${@}; do
    if [[ ${arg} == '--debug' ]]; then
        DEBUGGING=true;
    fi
done

docker run -ti --rm \
    -p 8888:8888 \
    -v ${PROJECT_BASE}/:/app \
    -v ${PROJECT_BASE}/config:/config \
    -v ${PROJECT_BASE}/library:/library \
    -v ${PROJECT_BASE}/cache:/tmp/unmanic \
    -e PUID=${PUID} \
    -e PGID=${PGID} \
    -e DEBUGGING=${DEBUGGING} \
    josh5/unmanic bash

