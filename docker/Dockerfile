FROM josh5/base-ubuntu:16.04
LABEL maintainer="Josh.5 <jsunnex@gmail.com>"


################################
### Config:
###
# Build Dependencies (not required in final image)
ARG BUILD_DEPENDENCIES=" \
        python3-dev \
        python3-pip \
        python3-setuptools \
    "


# Add pip requirements
COPY /requirements.txt /tmp/requirements.txt


### Install pyinotify service.
RUN \
    echo "**** Update sources ****" \
        && apt-get update \
    && \
    echo "**** Install python ****" \
        && apt-get install python3 -y --no-install-recommends \
            python3 \
    && \
    echo "**** Install package build tools ****" \
        && apt-get install -y --no-install-recommends \
            ${BUILD_DEPENDENCIES} \
    && \
    echo "**** Install ffmpeg ****" \
        && apt-get install -y \
            ffmpeg \
    && \
    echo "**** Install pip packages ****" \
        && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt  \
    && \
    echo "**** cleanup ****" \
        && apt-get purge -y --auto-remove \
	        ${BUILD_DEPENDENCIES} \
        && apt-get clean \
        && echo rm -rf \
            /tmp/* \
            /var/tmp/* \
            /var/lib/apt/lists/*


### Add local files
COPY /docker/root   /
COPY /              /app/


### Intended ports and volumes
VOLUME \
    /library \
    /cache

