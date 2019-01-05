#!/bin/bash

PUID=$(id -u)
PGID=$(id -g)

docker run -ti --rm \
    -e PUID:${PUID} \
    -e PGID:${PGID} \
    -p 8888:8888 \
    -v `pwd`/config:/config \
    -v `pwd`/library:/library \
    -v `pwd`/cache:/tmp/unmanic \
    -e LIBRARY_PATH=/library \
    -e DEBUGGING=false \
    -e SUPPORTED_CONTAINERS='avi,mkv' \
    josh5/unmanic:dev

