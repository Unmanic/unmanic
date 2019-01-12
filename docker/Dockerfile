FROM josh5/base-alpine:3.8
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
        && apk update \
    && \
    echo "**** Install python ****" \
        && apk add --no-cache \
            python3 \
    && \
    echo "**** Install ffmpeg ****" \
        && apk add --no-cache \
            ffmpeg \
    && \
    echo "**** Install pip packages ****" \
        && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt  \
    && \
    echo "**** Cleanup ****" \
        && rm -rf \
            /tmp/* \
            /var/tmp/*


### Add local files
COPY /docker/root   /
COPY /              /app/


### Environment variables
ENV \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    LC_CTYPE=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

