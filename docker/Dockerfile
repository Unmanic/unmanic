FROM josh5/base-alpine:3.10
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


### Install dependencies.
RUN \
    echo "**** Update sources ****" \
        && apk update \
    && \
    echo "**** Install python ****" \
        && apk add --no-cache \
            python3 \
            unzip \
    && \
    echo "**** Install ffmpeg ****" \
        && apk add --no-cache \
            ffmpeg \
    && \
    echo "**** Install pip packages ****" \
        && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && \
    echo "**** Cleanup ****" \
        && rm -rf \
            /tmp/* \
            /var/tmp/*


### Add local files
COPY /docker/root   /


# Build and install application
# Must first run `python3 ./setup.py bdist_egg` to build package
COPY /dist/      /src/
RUN \
    echo "**** Build and install unmanic ****" \
        && mkdir -p /usr/lib/python3.7/site-packages/unmanic.egg \
        && cd /usr/lib/python3.7/site-packages/unmanic.egg \
        && unzip /src/*.egg \
        && echo './unmanic.egg' > /usr/lib/python3.7/site-packages/easy-install.pth \
    echo "**** Make default paths for unmanic library ****" \
        && mkdir -p /library


### Environment variables
ENV \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    LC_CTYPE=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8
