#!/bin/bash
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jul 03 2021, (18:39:00 PM)
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

project_root="$(readlink -e $(dirname $(readlink -e ${BASH_SOURCE[0]}))/../)"

# Build backage
pushd "${project_root}/unmanic/webserver/frontend" &> /dev/null
npm install
npm run build 
popd &> /dev/null

# Copy dist package backage
pushd "${project_root}/unmanic/webserver" &> /dev/null
if [ ! -d "${project_root}/unmanic/webserver/frontend/dist/spa" ]; then
    echo "Cannot find built dist package for the frontend. Something must have gone wrong. Exit"
    exit 1
fi
rm -rf "${project_root}/unmanic/webserver/public"
mv -v "${project_root}/unmanic/webserver/frontend/dist/spa" "${project_root}/unmanic/webserver/public"
popd &> /dev/null
