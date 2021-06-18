FROM lsiobase/ubuntu:focal
LABEL maintainer="Josh.5 <jsunnex@gmail.com>"


# Env variables
ENV \
    LIBVA_DRIVERS_PATH="/usr/lib/x86_64-linux-gnu/dri" \
    NVIDIA_DRIVER_CAPABILITIES="compute,video,utility" \
    NVIDIA_VISIBLE_DEVICES="all"


# Install the runtime dependencies
# X86 Specific:
#   Intel VAAPI Tone mapping dependencies:
#       Prefer NEO to Beignet since the latter one doesn't support Comet Lake or newer for now.
#       Do not use the intel-opencl-icd package from repo since they will not build with RELEASE_WITH_REGKEYS enabled.
#   REF:
#       https://jellyfin.org/docs/general/administration/hardware-acceleration.html
#       https://github.com/jellyfin/jellyfin/blob/master/Dockerfile
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
            locales \
    && \
    echo "**** Install arch specific packages for $(uname -m) ****" \
        && sleep 2 \
        && \
        if uname -m | grep -q x86; then \
            echo "**** Add build dependencies ****" \
                && apt-get install -y \
                    wget \
            && \
            echo "**** Install MESA Media Drivers for AMD VAAPI ****" \
                && apt-get install -y \
                    mesa-va-drivers \
            && \
            echo "**** Install Intel Media Drivers  ****" \
                && export GMMLIB_VERSION="20.3.2" \
                && export IGC_VERSION="1.0.5435" \
                && export NEO_VERSION="20.46.18421" \
                && export LEVEL_ZERO_VERSION="1.0.18421" \
                && mkdir /tmp/intel-compute-runtime \
                && cd /tmp/intel-compute-runtime \
                && wget https://github.com/intel/compute-runtime/releases/download/${NEO_VERSION}/intel-gmmlib_${GMMLIB_VERSION}_amd64.deb \
                && wget https://github.com/intel/intel-graphics-compiler/releases/download/igc-${IGC_VERSION}/intel-igc-core_${IGC_VERSION}_amd64.deb \
                && wget https://github.com/intel/intel-graphics-compiler/releases/download/igc-${IGC_VERSION}/intel-igc-opencl_${IGC_VERSION}_amd64.deb \
                && wget https://github.com/intel/compute-runtime/releases/download/${NEO_VERSION}/intel-opencl_${NEO_VERSION}_amd64.deb \
                && wget https://github.com/intel/compute-runtime/releases/download/${NEO_VERSION}/intel-ocloc_${NEO_VERSION}_amd64.deb \
                && wget https://github.com/intel/compute-runtime/releases/download/${NEO_VERSION}/intel-level-zero-gpu_${LEVEL_ZERO_VERSION}_amd64.deb \
                && dpkg -i *.deb \
                && cd / \
                && rm -rf /tmp/intel-compute-runtime \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y \
                    wget \
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


# Install ffmpeg
RUN \
    echo "**** Install FFmpeg for $(uname -m) ****" \
        && sleep 2 \
        && \
        if uname -m | grep -q x86; then \
            echo "**** Add Jellyfin repository ****" \
                && apt-get update \
                && apt-get install -y \
                    gnupg \
                    curl \
                && curl -ks https://repo.jellyfin.org/jellyfin_team.gpg.key | apt-key add - \
                && echo "deb [arch=$( dpkg --print-architecture )] https://repo.jellyfin.org/ubuntu focal main" | tee /etc/apt/sources.list.d/jellyfin.list \
            && \
            echo "**** Install jellyfin-ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    jellyfin-ffmpeg \
                    openssl \
                    vainfo \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y \
                    curl \
                    gnupg \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q aarch64; then \
            echo "**** Install ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    ffmpeg \
                    ca-certificates \
                    libfontconfig1 \
                    libfreetype6 \
                    libomxil-bellagio-bin \
                    libomxil-bellagio0 \
                    libssl-dev \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q armv7l; then \
            echo "**** Add Jellyfin repository ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    ca-certificates \
                    curl \
                    gnupg \
                && curl -ks https://repo.jellyfin.org/jellyfin_team.gpg.key | apt-key add - \
                && curl -ks https://keyserver.ubuntu.com/pks/lookup?op=get\&search=0x6587ffd6536b8826e88a62547876ae518cbcf2f2 | apt-key add - \
                && echo 'deb [arch=armhf] https://repo.jellyfin.org/ubuntu focal main' > /etc/apt/sources.list.d/jellyfin.list \
                && echo "deb http://ppa.launchpad.net/ubuntu-raspi2/ppa/ubuntu bionic main">> /etc/apt/sources.list.d/raspbins.list \
            && \
            echo "**** Install jellyfin-ffmpeg and linked 3rd party libs ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    jellyfin-ffmpeg \
                    libfontconfig1 \
                    libfreetype6 \
                    libomxil-bellagio-bin \
                    libomxil-bellagio0 \
                    libraspberrypi0 \
                    libssl-dev \
                    libva2 \
                    vainfo \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y \
                    curl \
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
