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
            libexpat1 \
            libglib2.0-0 \
            libgomp1 \
            libharfbuzz0b \
            libmediainfo0v5 \
            libv4l-0 \
            libx11-6 \
            libxcb1 \
            libxext6 \
            libxml2 \
    && \
    echo "**** Install all available media acceleration packages ****" \
        # va-driver-all: 
        #   A meta-package for installing all available Video Acceleration API (VAAPI) drivers. Includes packages like:
        #       - i965-va-driver
        #       - intel-media-va-driver
        #       - mesa-va-drivers
        #       - libdrm2
        #       - etc
        && apt-get install -y \
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
                # libmfx1:
                #   This is a library for Intel Media SDK runtime. It is necessary for applications that use Intel Quick Sync Video technology.
                # libmfxgen1:
                #   Similar to libmfx1, it's a part of the Intel Media SDK.
                # libva-drm2 and libva2:
                #   These are additional libraries needed for VAAPI to interface with the Direct Rendering Manager (DRM) and to provide the main API for VAAPI.
                # libvpl2:
                #   This is the successor to the Media SDK and provides a library for video processing.
                && apt-get install -y \
                    intel-media-va-driver-non-free \
                    libigdgmm12 \
                    libmfx1 \
                    libmfxgen1 \
                    libva-drm2 \
                    libva2 \
                    libvpl2 \
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
ARG JELLYFIN_FFMPEG_VERSION="6"
ARG NODE_MAJOR="20"
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
                && apt-get install -y \
                    jellyfin-ffmpeg${JELLYFIN_FFMPEG_VERSION} \
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
                && apt-get install -y \
                    jellyfin-ffmpeg${JELLYFIN_FFMPEG_VERSION} \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
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
