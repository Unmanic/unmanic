#!/usr/bin/env bash
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

set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_BASE=$(cd "$SCRIPT_DIR/.." && pwd)

# Defaults
PUID=$(id -u)
PGID=$(id -g)
DEBUG="false"
USE_TEST_SUPPORT_API="false"
CACHE_PATH="$PROJECT_BASE/dev_environment/cache"
EXT_PORT=8888
IMAGE_TAG="staging"
DOCKER_PARAMS=()

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
    --help, -h                  Show this help message and exit
    --debug                     Enable debug mode inside container
    --use-test-support-api      Set USE_TEST_SUPPORT_API=true inside container
    --hw=<nvidia|vaapi>         Enable hardware acceleration
    --cpus=<value>              Limit container CPUs (e.g. "2.5")
    --memory=<value>            Limit container memory (e.g. "4g")
    --cache=<path>              Override cache directory (default: $CACHE_PATH)
    --port=<port>               Map host port to container 8888 (default: $EXT_PORT)
    --tag=<image-tag>           Docker image tag to run (default: $IMAGE_TAG)
EOF
}

# parse flags
while [[ $# -gt 0 ]]; do
    case $1 in
    --help | -h)
        usage
        exit 0
        ;;
    --debug)
        DEBUG=true
        ;;
    --use-test-support-api)
        USE_TEST_SUPPORT_API=true
        ;;
    --hw=*)
        HW="${1#*=}"
        ;;
    --cpus=*)
        DOCKER_PARAMS+=(--cpus "${1#*=}")
        ;;
    --memory=*)
        DOCKER_PARAMS+=(--memory "${1#*=}")
        ;;
    --cache=*)
        CACHE_PATH="${1#*=}"
        ;;
    --port=*)
        EXT_PORT="${1#*=}"
        ;;
    --tag=*)
        IMAGE_TAG="${1#*=}"
        ;;
    *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
    shift
done

if [[ -n $HW ]]; then
    case $HW in
    nvidia)
        DOCKER_PARAMS+=(--gpus all -e NVIDIA_VISIBLE_DEVICES=all)
        ;;
    vaapi)
        DOCKER_PARAMS+=(--device /dev/dri:/dev/dri)
        ;;
    *)
        echo "Unsupported --hw=$HW" >&2
        exit 1
        ;;
    esac
fi

# detect if we need sudo
if docker ps >/dev/null 2>&1; then
    DOCKER_CMD="docker"
else
    DOCKER_CMD="sudo docker"
fi

# run!
$DOCKER_CMD run --rm -it \
    --name unmanic \
    -e TZ=Pacific/Auckland \
    -e PUID="$PUID" \
    -e PGID="$PGID" \
    -e DEBUGGING="$DEBUG" \
    -e USE_TEST_SUPPORT_API="$USE_TEST_SUPPORT_API" \
    -p "$EXT_PORT":8888 \
    -v "$PROJECT_BASE":/app:Z \
    -v "$PROJECT_BASE/dev_environment/config":/config:Z \
    -v "$PROJECT_BASE/dev_environment/library":/library:Z \
    -v "$CACHE_PATH":/tmp/unmanic:Z \
    -v "$CACHE_PATH/remote_library":/tmp/unmanic/remote_library:Z \
    -v /run/user/"$PUID":/run/user:ro,Z \
    "${DOCKER_PARAMS[@]}" \
    ghcr.io/unmanic/unmanic:"$IMAGE_TAG" \
    bash
