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
            libexpat1=2.2.9-1ubuntu0.4 \
            libgl1-mesa-dri=21.2.6-0ubuntu0.1~20.04.2 \
            libglib2.0-0=2.64.6-1~ubuntu20.04.4 \
            libgomp1=10.3.0-1ubuntu1~20.04 \
            libharfbuzz0b=2.6.4-1ubuntu4 \
            libmediainfo0v5=19.09+dfsg-2build1 \
            libv4l-0=1.18.0-2build1 \
            libx11-6=2:1.6.9-2ubuntu1.2 \
            libxcb1=1.14-2 \
            libxext6=2:1.3.4-0ubuntu1 \
            libxml2=2.9.10+dfsg-5ubuntu0.20.04.3 \
    && \
    echo "**** Install arch specific packages for $(uname -m) ****" \
        && sleep 2 \
        && \
        if uname -m | grep -q x86; then \
            echo "**** Add Intel Graphics repository  ****" \
                && apt-get install -y \
                    gnupg \
                && echo "deb [arch=amd64] https://repositories.intel.com/graphics/ubuntu focal main" > /etc/apt/sources.list.d/intel-graphics.list \
                && apt-key adv --fetch-keys https://repositories.intel.com/graphics/intel-graphics.key \
            && \
            echo "**** Install Intel Media Drivers  ****" \
                && apt-get update \
                && apt-get install -y \
                    i965-va-driver=2.4.0-0ubuntu1 \
                    intel-igc-cm=1.0.128+i699.3~u20.04 \
                    intel-level-zero-gpu=1.3.22597+i699.3~u20.04 \
                    intel-media-va-driver-non-free=22.2.2+i699.3~u20.04 \
                    intel-opencl-icd=22.10.22597+i699.3~u20.04 \
                    level-zero=1.7.9+i699.3~u20.04 \
                    libigc1=1.0.10409+i699.3~u20.04 \
                    libigdfcl1=1.0.10409+i699.3~u20.04 \
                    libigdgmm11=21.3.3+i643~u20.04 \
                    libmfx1=22.2.2+i699.3~u20.04 \
                    libva-drm2=2.14.0.2-23 \
                    libva-wayland2=2.14.0.2-23 \
                    libva-x11-2=2.14.0.2-23 \
                    libva2=2.14.0.2-23 \
                    vainfo=2.14.0.2-1 \
            && \
            echo "**** Install MESA Media Drivers for AMD VAAPI ****" \
                && apt-get install -y \
                    mesa-va-drivers=21.2.6-0ubuntu0.1~20.04.2 \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y \
                    gnupg \
            && \
            echo ; \
        fi \
    && \
    echo "**** Section cleanup ****" \
        && apt-get clean autoclean -y \
        && apt-get autoremove -y \
        && rm -rf \
            /var/lib/apt/lists/* \
            /var/tmp/* \
            /tmp/*


# Install commonly used command line tools
ARG JELLYFIN_FFMPEG_VERSION="4.4.1-4"
ARG NODEJS_VERSION="16.x"
RUN \
    echo "**** Install FFmpeg for $(uname -m) ****" \
        && sleep 2 \
        && apt-get update \
        && \
        if uname -m | grep -q x86; then \
            echo "**** Add Jellyfin repository ****" \
                && apt-get install --no-install-recommends --no-install-suggests -y ca-certificates gnupg \
                && curl -ks https://repo.jellyfin.org/jellyfin_team.gpg.key | apt-key add - \
                && echo "deb [arch=$( dpkg --print-architecture )] https://repo.jellyfin.org/ubuntu focal main" | tee /etc/apt/sources.list.d/jellyfin.list \
            && \
            echo "**** Install jellyfin-ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    openssl \
                    locales \
                &&  curl -ksL \
                    -o /tmp/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-focal_amd64.deb \
                    "https://repo.jellyfin.org/releases/server/ubuntu/versions/jellyfin-ffmpeg/${JELLYFIN_FFMPEG_VERSION}/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-focal_amd64.deb" \
                && apt-get install -y \
                    /tmp/jellyfin-ffmpeg_${JELLYFIN_FFMPEG_VERSION}-focal_amd64.deb \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y gnupg \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q aarch64; then \
            echo "**** Install ffmpeg and linked 3rd party libs ****" \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    ffmpeg \
                    libssl-dev \
                    ca-certificates \
                    libfontconfig1 \
                    libfreetype6 \
                    libomxil-bellagio0 \
                    libomxil-bellagio-bin \
                    locales \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q armv7l; then \
            echo "**** Add Jellyfin repository ****" \
                && apt-get install --no-install-recommends --no-install-suggests -y ca-certificates gnupg \
                && curl -ks https://repo.jellyfin.org/jellyfin_team.gpg.key | apt-key add - \
                && curl -ks https://keyserver.ubuntu.com/pks/lookup?op=get\&search=0x6587ffd6536b8826e88a62547876ae518cbcf2f2 | apt-key add - \
                && echo 'deb [arch=armhf] https://repo.jellyfin.org/ubuntu focal main' > /etc/apt/sources.list.d/jellyfin.list \
                && echo "deb http://ppa.launchpad.net/ubuntu-raspi2/ppa/ubuntu bionic main">> /etc/apt/sources.list.d/raspbins.list \
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
            curl \
            nano \
            sqlite3 \
            wget \
    && \
    echo "**** Install NodeJS for $(uname -m) ****" \
        && curl -fsSL https://deb.nodesource.com/setup_${NODEJS_VERSION} | bash - \
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
                python3 \
                python3-pip \
                python3-setuptools \
                unzip \
        && \
        if uname -m | grep -q armv7l; then \
            echo "**** Install python package build dependencies ****" \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    gcc \
                    python3-dev \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q aarch64; then \
            echo "**** Install python package build dependencies ****" \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    gcc \
                    python3-dev \
            && \
            echo ; \
        fi \
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
