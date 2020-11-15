FROM lsiobase/ffmpeg:bin as binstage
FROM lsiobase/ubuntu:bionic
LABEL maintainer="Josh.5 <jsunnex@gmail.com>"


# Add files from binstage
COPY --from=binstage / /


# Env variables
ENV \
    LIBVA_DRIVERS_PATH="/usr/lib/x86_64-linux-gnu/dri" \
    NVIDIA_DRIVER_CAPABILITIES="compute,video,utility" \
    NVIDIA_VISIBLE_DEVICES="all"


# Install the runtime dependencies
RUN \
    echo "**** Install runtime ****" \
        && apt-get update \
        && apt-get install -y \
            i965-va-driver \
            libexpat1 \
            libgl1-mesa-dri \
            libglib2.0-0 \
            libgomp1 \
            libharfbuzz0b \
            libv4l-0 \
            libx11-6 \
            libxcb1 \
            libxext6 \
            libxml2 \
            vainfo \
    && \
    echo "**** Cleanup ****" \
        && rm -rf \
            /var/lib/apt/lists/* \
            /var/tmp/*


# Add pip requirements
COPY /requirements.txt /tmp/requirements.txt


# Install dependencies.
RUN \
    echo "**** Update sources ****" \
        && apt-get update \
    && \
    echo "**** Install python ****" \
        && apt-get install -y --no-install-recommends \
            python3 \
            python3-pip \
            python3-setuptools \
            unzip \
    && \
    echo "**** Install pip packages ****" \
        && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && \
    echo "**** Cleanup ****" \
        && rm -rf \
            /tmp/* \
            /var/tmp/*

COPY / /tmp/
RUN apt-get install git --yes
RUN \ 
    echo "**** Building wheel packages ****" \ 
    && \
     cd /tmp/ && python3 ./setup.py bdist_wheel \
                && cp -R dist/ /src/

RUN cd /src/ && mv unmanic-UNKNOWN-py3-none-any.whl unmanic-1.0.0-py3-none-any.whl

RUN \
    echo "**** Cleanup ****" \ 
    && rm -rf /tmp/*

# Build and install application
# Must first run `python3 ./setup.py bdist_wheel` to build package
RUN \
    echo "**** Build and install unmanic ****" \
        && ls -l /src/ \
        && python3 -m pip install --no-cache-dir /src/*.whl \
    && \
    echo "**** Make default paths for unmanic library ****" \
        && mkdir -p /library


# Add local files
COPY /docker/root   /
