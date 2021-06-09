FROM lsiobase/ubuntu:focal
LABEL maintainer="Josh.5 <jsunnex@gmail.com>"


# Env variables
ENV \
    LIBVA_DRIVERS_PATH="/usr/lib/x86_64-linux-gnu/dri" \
    NVIDIA_DRIVER_CAPABILITIES="compute,video,utility" \
    NVIDIA_VISIBLE_DEVICES="all"


# Install the runtime dependencies
# TODO: Remove intel-opencl-icd and replace with suggested build by Jellyfin
#   https://jellyfin.org/docs/general/administration/hardware-acceleration.html
#   https://github.com/jellyfin/jellyfin/blob/master/Dockerfile
RUN \
    echo "**** Install runtime packages ****" \
        && apt-get update \
        && apt-get install -y \
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
    echo "**** Install x86 specific packages ($(uname -m)) ****" \
        &&  if uname -m | grep -q x86; then \
                apt-get install -y \
                    gpg-agent \
                && echo "**** Add Intel Graphics repository  ****" \
                && echo "deb [arch=amd64] https://repositories.intel.com/graphics/ubuntu focal main" > /etc/apt/sources.list.d/intel-graphics.list \
                && apt-key adv --fetch-keys https://repositories.intel.com/graphics/intel-graphics.key \
                && echo "**** Install Intel Media Drivers  ****" \
                && apt-get update \
                && apt-get install -y \
                    i965-va-driver \
                    intel-opencl-icd \
                    intel-level-zero-gpu level-zero \
                    intel-media-va-driver-non-free libmfx1 \
                && echo "**** Install MESA Media Drivers for AMD VAAPI ****" \
                && apt-get install -y \
                    mesa-va-drivers ; \
            else \
                echo "Arch does not support x86 runtime packages. Ignoring"; \
            fi \
    && \
    echo "**** Cleanup ****" \
        && apt-get clean autoclean -y \
        && apt-get autoremove -y \
        && rm -rf \
            /var/lib/apt/lists/* \
            /var/tmp/* \
            /tmp/*


# Install jellyfin-ffmpeg
ARG FFMPEG_VERSION=4.3.2-1
RUN \
    echo "**** Install jellyfin-ffmpeg ($( dpkg --print-architecture )) ****" \
        && curl -Lf \
            https://repo.jellyfin.org/releases/server/ubuntu/versions/jellyfin-ffmpeg/${FFMPEG_VERSION}/jellyfin-ffmpeg_${FFMPEG_VERSION}-focal_$( dpkg --print-architecture ).deb \
            -o /tmp/jellyfin-ffmpeg_${FFMPEG_VERSION}-focal_$( dpkg --print-architecture ).deb \
        && apt-get update \
        && apt-get install --no-install-recommends --no-install-suggests -y \
            openssl \
            locales \
        && apt-get install --no-install-recommends --no-install-suggests -y \
            /tmp/jellyfin-ffmpeg_${FFMPEG_VERSION}-focal_$( dpkg --print-architecture ).deb \
        && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
        && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
    && \
    echo "**** Cleanup ****" \
        && apt-get clean autoclean -y \
        && apt-get autoremove -y \
        && rm -rf \
            /var/lib/apt/lists/* \
            /var/tmp/* \
            /tmp/*


# Add pip requirements
COPY /requirements.txt /tmp/requirements.txt


# Install Unmanic python dependencies.
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


# Build and install application
# Must first run `python3 ./setup.py bdist_wheel` to build package
COPY /dist/      /src/
RUN \
    echo "**** Build and install unmanic ****" \
        && ls -l /src/ \
        && python3 -m pip install --no-cache-dir /src/*.whl \
    && \
    echo "**** Move unmanic executable so we can wrap a bash script around it for developers ****" \
        && mv -f /usr/local/bin/unmanic /usr/local/bin/unmanic-service \
    && \
    echo "**** Make default paths for unmanic library ****" \
        && mkdir -p /library


# Add local files
COPY /docker/root   /
