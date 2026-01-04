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
CONFIG_PREFIX=""
CACHE_PATH="$PROJECT_BASE/dev_environment/cache"
EXT_PORT=8888
IMAGE_TAG="staging"
DOCKER_PARAMS=()
CONTAINER_NAME="unmanic-dev"
CONFIG_LABEL="com.unmanic.run_config"
CPUS=""
MEMORY=""
FORCE_RECREATE="false"
COMMAND="run"
COMMAND_ARGS=()
EXEC_ROOT="false"
RUN_COMMAND=""
ENABLE_PROFILING="false"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] [COMMAND] [COMMAND_ARGS...]

Options:
    --help, -h                  Show this help message and exit
    --debug                     Enable debug mode inside container
    --use-test-support-api      Set USE_TEST_SUPPORT_API=true inside container
    --hw=<nvidia|vaapi>         Enable hardware acceleration
    --cpus=<value>              Limit container CPUs (e.g. "2.5")
    --memory=<value>            Limit container memory (e.g. "4g")
    --cache=<path>              Override cache directory (default: $CACHE_PATH)
    --config-prefix=<value>     Use dev_environment/config-<value> for /config mount
    --port=<port>               Map host port to container 8888 (default: $EXT_PORT)
    --tag=<image-tag>           Docker image tag to run (default: $IMAGE_TAG)
    --force-recreate            Recreate container even if settings match
    --root                      Run exec commands as root (uid 0)
    --run-cmd=<value>           Override container run command (supports {cmd} placeholder)

Commands:
    run                         Start the container (default)
    build                       Build the staging image from ./docker/Dockerfile
    pull                        Pull the staging image from Docker Hub
    stop                        Stop the container
    shell                       Run an interactive shell inside the container
    exec                        Run a command inside the container
    logs                        Print container logs (pass extra docker args, e.g. -f)
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
        CPUS="${1#*=}"
        DOCKER_PARAMS+=(--cpus "$CPUS")
        ;;
    --memory=*)
        MEMORY="${1#*=}"
        DOCKER_PARAMS+=(--memory "$MEMORY")
        ;;
    --cache=*)
        CACHE_PATH="${1#*=}"
        ;;
    --config-prefix=*)
        CONFIG_PREFIX="${1#*=}"
        ;;
    --port=*)
        EXT_PORT="${1#*=}"
        ;;
    --tag=*)
        IMAGE_TAG="${1#*=}"
        ;;
    --force-recreate)
        FORCE_RECREATE=true
        ;;
    --root)
        EXEC_ROOT=true
        ;;
    --run-cmd=*)
        RUN_COMMAND="${1#*=}"
        ;;
    --profiling)
        ENABLE_PROFILING=true
        ;;
    run | build | pull | stop | shell | exec | logs)
        COMMAND="$1"
        shift
        COMMAND_ARGS=("$@")
        break
        ;;
    *)
        COMMAND="$1"
        shift
        COMMAND_ARGS=("$@")
        break
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

CONFIG_PATH="$PROJECT_BASE/dev_environment/config"
if [[ -n $CONFIG_PREFIX ]]; then
    CONFIG_PATH="$PROJECT_BASE/dev_environment/config-$CONFIG_PREFIX"
fi
IMAGE_ID="$($DOCKER_CMD image inspect -f '{{.Id}}' "josh5/unmanic:$IMAGE_TAG" 2>/dev/null || true)"
config_string="debug=$DEBUG;use_test_support_api=$USE_TEST_SUPPORT_API;hw=${HW:-};cpus=$CPUS;memory=$MEMORY;cache=$CACHE_PATH;config_path=$CONFIG_PATH;port=$EXT_PORT;tag=$IMAGE_TAG;image_id=$IMAGE_ID;puid=$PUID;pgid=$PGID"
if [[ -n $RUN_COMMAND ]]; then
    config_string="${config_string};run_cmd=$RUN_COMMAND"
fi
if [[ "$ENABLE_PROFILING" == "true" ]]; then
    config_string="${config_string};profiling=true"
fi
config_hash=$(printf '%s' "$config_string" | sha256sum | awk '{print $1}')

start_container() {
    $DOCKER_CMD run --rm -d \
        --name "$CONTAINER_NAME" \
        --label "$CONFIG_LABEL=$config_hash" \
        -e TZ=Pacific/Auckland \
        -e PUID="$PUID" \
        -e PGID="$PGID" \
        -e DEBUGGING="$DEBUG" \
        -e USE_TEST_SUPPORT_API="$USE_TEST_SUPPORT_API" \
        -e UNMANIC_RUN_COMMAND="$RUN_COMMAND" \
        -e PROFILE_UNMANIC="$ENABLE_PROFILING" \
        -p "$EXT_PORT":8888 \
        -v "$PROJECT_BASE":/app:Z \
        -v "$CONFIG_PATH":/config:Z \
        -v "$PROJECT_BASE/dev_environment/library":/library:Z \
        -v "$CACHE_PATH":/tmp/unmanic:Z \
        -v "$CACHE_PATH/remote_library":/tmp/unmanic/remote_library:Z \
        -v /run/user/"$PUID":/run/user:ro,Z \
        "${DOCKER_PARAMS[@]}" \
        josh5/unmanic:"$IMAGE_TAG"
}

container_exists() {
    $DOCKER_CMD inspect "$CONTAINER_NAME" >/dev/null 2>&1
}

container_running() {
    $DOCKER_CMD inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q true
}

existing_hash="$($DOCKER_CMD inspect -f "{{ index .Config.Labels \"$CONFIG_LABEL\" }}" "$CONTAINER_NAME" 2>/dev/null || true)"

warn_container_state() {
    if ! container_exists; then
        echo "Warning: $CONTAINER_NAME container has not been created. Start it first with '$(basename "$0") run'." >&2
        exit 1
    fi
    if ! container_running; then
        echo "Warning: $CONTAINER_NAME container is not running. Start it first with '$(basename "$0") run'." >&2
        exit 1
    fi
}

case "$COMMAND" in
run)
    if container_exists; then
        if [[ "$FORCE_RECREATE" == "true" ]] || [[ "$existing_hash" != "$config_hash" ]] || ! container_running; then
            echo "Recreating $CONTAINER_NAME container with updated settings..."
            $DOCKER_CMD rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
            start_container
        else
            echo "$CONTAINER_NAME container already running with matching settings."
        fi
    else
        start_container
    fi
    ;;
build)
    $DOCKER_CMD build -f "$PROJECT_BASE/docker/Dockerfile" -t josh5/unmanic:staging "$PROJECT_BASE"
    ;;
pull)
    $DOCKER_CMD pull josh5/unmanic:staging
    ;;
stop)
    if container_exists; then
        if container_running; then
            $DOCKER_CMD stop "$CONTAINER_NAME"
        else
            echo "Warning: $CONTAINER_NAME container is already stopped." >&2
        fi
    else
        echo "Warning: $CONTAINER_NAME container has not been created." >&2
    fi
    ;;
shell)
    warn_container_state
    $DOCKER_CMD exec -it "$CONTAINER_NAME" bash
    ;;
exec)
    warn_container_state
    if [[ ${#COMMAND_ARGS[@]} -eq 0 ]]; then
        echo "Error: exec requires a command to run inside the container." >&2
        usage
        exit 1
    fi
    if [[ "$EXEC_ROOT" == "true" ]]; then
        $DOCKER_CMD exec -it --user 0:0 "$CONTAINER_NAME" "${COMMAND_ARGS[@]}"
    else
        $DOCKER_CMD exec -it --user "$PUID:$PGID" "$CONTAINER_NAME" "${COMMAND_ARGS[@]}"
    fi
    ;;
logs)
    warn_container_state
    $DOCKER_CMD logs "${COMMAND_ARGS[@]}" "$CONTAINER_NAME"
    ;;
*)
    echo "Unknown command: $COMMAND" >&2
    usage
    exit 1
    ;;
esac
