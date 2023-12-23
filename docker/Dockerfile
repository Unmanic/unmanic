FROM lsiobase/ubuntu:jammy
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
    echo "**** Install build dependencies requirements ****" \
        && apt-get update \
        && apt-get install -y \
            ca-certificates \
            curl \
            gnupg \
            wget \
    && \
    echo "**** Install runtime packages ****" \
        && apt-get install -y \
            libexpat1=2.4.7-1ubuntu0.2 \
            libglib2.0-0=2.72.4-0ubuntu2.2 \
            libgomp1=12.3.0-1ubuntu1~22.04 \
            libharfbuzz0b=2.7.4-1ubuntu3.1 \
            libmediainfo0v5=21.09+dfsg-4 \
            libv4l-0=1.22.1-2build1 \
            libx11-6=2:1.7.5-1ubuntu0.3 \
            libxcb1=1.14-3ubuntu3 \
            libxext6=2:1.3.4-1build1 \
            libxml2=2.9.13+dfsg-1ubuntu0.3 \
    && \
    echo "**** Install all available media acceleration packages ****" \
        # libmfx1:
        #   This is a library for Intel Media SDK runtime. It is necessary for applications that use Intel Quick Sync Video technology.
        # libvpl2:
        #   This is the successor to the Media SDK and provides a library for video processing.
        # va-driver-all: 
        #   A meta-package for installing all available Video Acceleration API (VAAPI) drivers. Includes packages like:
        #       - i965-va-driver
        #       - intel-media-va-driver
        #       - mesa-va-drivers
        #       - libdrm2
        #       - etc
        && apt-get install -y \
            libmfx1 \
            libvpl2 \
            va-driver-all \
    && \
    echo "**** Install arch specific packages for $(uname -m) ****" \
        && sleep 2 \
        && \
        if uname -m | grep -q x86; then \
            echo "**** Add Intel Graphics repository  ****" \
                && wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | gpg --dearmor --output /usr/share/keyrings/intel-graphics.gpg \
                && echo "deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu jammy client" | tee /etc/apt/sources.list.d/intel-gpu-jammy.list \
            && \
            echo "**** Install Intel Media Drivers  ****" \
                && apt-get update \
                # intel-media-va-driver-non-free:
                #   This is the primary driver for Intel's Video Acceleration API on Linux, which provides support for video encoding and decoding on Intel graphics hardware.
                # libigdgmm12:
                #   A part of the Intel Graphics Memory Management Library, which is used for managing graphics memory in an efficient and optimized way on Intel GPUs.
                # libmfxgen1:
                #   Similar to libmfx1, it's a part of the Intel Media SDK.
                # libva-drm2 and libva2:
                #   These are additional libraries needed for VAAPI to interface with the Direct Rendering Manager (DRM) and to provide the main API for VAAPI.
                && apt-get install -y \
                    intel-media-va-driver-non-free \
                    libigdgmm12 \
                    libmfxgen1 \
                    libva-drm2 \
                    libva2 \
            && \
            echo ; \
        fi \
    && \
    echo "**** Install hardware info tools packages ****" \
        # hwinfo:
        #   A hardware identification system that provides detailed information about all the hardware components of a computer.
        # vainfo:
        #   This utility displays information about the VAAPI capabilities of your hardware.
        && apt-get install -y \
            hwinfo \
            vainfo \
    && \
    echo "**** Section cleanup ****" \
        && apt-get clean autoclean -y \
        && apt-get autoremove -y \
        && rm -rf \
            /var/lib/apt/lists/* \
            /var/tmp/* \
            /tmp/*


# Install commonly used command line tools
ARG JELLYFIN_FFMPEG_VERSION="6.0-8"
ARG NODE_MAJOR="16"
RUN \
    echo "**** Install FFmpeg for $(uname -m) ****" \
        && sleep 2 \
        && apt-get update \
        && \
        if uname -m | grep -q x86; then \
            echo "**** Add Jellyfin repository ****" \
                && wget -qO - https://repo.jellyfin.org/jellyfin_team.gpg.key | gpg --dearmor --output /usr/share/keyrings/jellyfin_team.gpg \
                && echo "deb [arch=$( dpkg --print-architecture ) signed-by=/usr/share/keyrings/jellyfin_team.gpg] https://repo.jellyfin.org/ubuntu jammy main" | tee /etc/apt/sources.list.d/jellyfin.list \
            && \
            echo "**** Install jellyfin-ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    openssl \
                    locales \
                && wget --no-cookies --quiet \
                    -O "/tmp/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-jammy_amd64.deb" \
                    "https://repo.jellyfin.org/releases/server/ubuntu/versions/jellyfin-ffmpeg/${JELLYFIN_FFMPEG_VERSION}/jellyfin-ffmpeg6_${JELLYFIN_FFMPEG_VERSION}-jammy_amd64.deb" \
                && apt-get install -y \
                    /tmp/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-jammy_amd64.deb \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q aarch64; then \
            echo "**** Add Jellyfin repository ****" \
                && wget -qO - https://repo.jellyfin.org/jellyfin_team.gpg.key | gpg --dearmor --output /usr/share/keyrings/jellyfin_team.gpg \
                && echo "deb [arch=$( dpkg --print-architecture ) signed-by=/usr/share/keyrings/jellyfin_team.gpg] https://repo.jellyfin.org/ubuntu jammy main" | tee /etc/apt/sources.list.d/jellyfin.list \
            && \
            echo "**** Install jellyfin-ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    locales \
                    libssl-dev \
                    libfontconfig1 \
                    libfreetype6 \
                    libomxil-bellagio0 \
                    libomxil-bellagio-bin \
                && wget --no-cookies --quiet \
                    -O "/tmp/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-jammy_arm64.deb" \
                    "https://repo.jellyfin.org/releases/server/ubuntu/versions/jellyfin-ffmpeg/${JELLYFIN_FFMPEG_VERSION}/jellyfin-ffmpeg6_${JELLYFIN_FFMPEG_VERSION}-jammy_arm64.deb" \
                && apt-get install -y \
                    /tmp/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-jammy_arm64.deb \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q armv7l; then \
            echo "**** Add Jellyfin repository ****" \
                && wget -qO - https://repo.jellyfin.org/jellyfin_team.gpg.key | gpg --dearmor --output /usr/share/keyrings/jellyfin_team.gpg \
                && echo "deb [arch=armhf signed-by=/usr/share/keyrings/jellyfin_team.gpg] https://repo.jellyfin.org/ubuntu jammy main" | tee /etc/apt/sources.list.d/jellyfin.list \
            && \
            echo "**** Install jellyfin-ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    jellyfin-ffmpeg \
                    libssl-dev \
                    libfontconfig1 \
                    libfreetype6 \
                    libomxil-bellagio0 \
                    libomxil-bellagio-bin \
                    libraspberrypi0 \
                    vainfo \
                    libva2 \
                    locales \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y gnupg \
            && \
            echo ; \
        fi \
    && \
    echo "**** Install startup script requirements ****" \
        && apt-get install -y \
            jq \
            nano \
            sqlite3 \
    && \
    echo "**** Add NodeJS repository ****" \
        && wget -qO - https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --output /usr/share/keyrings/nodesource.gpg \
        && echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && \
    echo "**** Install NodeJS for $(uname -m) ****" \
        && apt-get update \
        && apt-get install -y \
            nodejs \
    && \
    echo "**** Install exiftool for $(uname -m) ****" \
        && apt-get install -y \
            libimage-exiftool-perl \
    && \
    echo "**** Section cleanup ****" \
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
    echo "**** Install Unmanic application dependencies ****" \
        && sleep 2 \
        && \
        echo "**** Update sources ****" \
            && apt-get update \
        && \
        echo "**** Install python ****" \
            && apt-get install -y --no-install-recommends \
                grc \
                gcc \
                python3 \
                python3-dev \
                python3-pip \
                python3-setuptools \
                unzip \
        && \
        echo "**** Install pip packages ****" \
            && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && \
    echo "**** Section cleanup ****" \
        && apt-get clean autoclean -y \
        && apt-get autoremove -y \
        && rm -rf \
            /var/lib/apt/lists/* \
            /var/tmp/* \
            /tmp/*


# Install pre-built Unmanic wheel
# Must first run `python3 ./setup.py bdist_wheel` on host to build package
COPY /dist/ /src/
RUN \
    echo "**** Install Unmanic ****" \
        && sleep 2 \
        && \
        echo "**** Install unmanic from pre-built wheel ****" \
            && ls -l /src/ \
            && python3 -m pip install --no-cache-dir /src/*.whl \
        && \
        echo "**** Move unmanic executable so we can wrap a bash script around it for developers ****" \
            && mv -f /usr/local/bin/unmanic /usr/local/bin/unmanic-service \
        && \
        echo "**** Make default paths for unmanic library ****" \
            && mkdir -p /library


# Add local files
COPY /docker/root /


# Unmanic runs on port 8888
EXPOSE 8888/tcp
