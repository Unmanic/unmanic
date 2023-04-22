FROM lsiobase/ubuntu:focal
LABEL maintainer="Josh.5 <jsunnex@gmail.com>"


# Env variables
ENV \
    NVIDIA_DRIVER_CAPABILITIES="compute,video,utility" \
    NVIDIA_VISIBLE_DEVICES="all"


# Install the runtime dependencies
# jellyfin-ffmpeg5 comes with all VA-API drivers required by Intel and AMD, except the OpenCL runtime.
RUN \
    echo "**** Install runtime packages ****" \
        && apt-get update \
        && apt-get install -y \
            libmediainfo0v5=19.09+dfsg-2build1 \
    && \
    echo "**** Install arch specific packages for $(uname -m) ****" \
        && sleep 2 \
        && \
        if uname -m | grep -q x86_64; then \
            echo "**** Add Intel Graphics repository ****" \
                && apt-get install -y \
                    gnupg \
                && echo "deb [arch=amd64] https://repositories.intel.com/graphics/ubuntu focal main" > /etc/apt/sources.list.d/intel-graphics.list \
                && apt-key adv --fetch-keys https://repositories.intel.com/graphics/intel-graphics.key \
            && \
            echo "**** Install Intel Compute Runtime ****" \
                && apt-get update \
                && apt-get install -y \
                    libigdgmm12=22.1.7+i419~u20.04 \
                    libigdfcl1=1.0.11485+i419~u20.04 \
                    libigc1=1.0.11485+i419~u20.04 \
                    intel-igc-cm=1.0.160+i755~u20.04 \
                    intel-opencl-icd=22.28.23726.1+i419~u20.04 \
                    intel-level-zero-gpu=1.3.23726.1+i419~u20.04 \
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
ARG NODEJS_VERSION="16.x"
RUN \
    echo "**** Install FFmpeg for $(uname -m) ****" \
        && sleep 2 \
        && apt-get update \
        && \
        if uname -m | grep -q 'x86_64\|aarch64\|armv7l' ; then \
            echo "**** Add Jellyfin repository ****" \
                && apt-get install --no-install-recommends --no-install-suggests -y ca-certificates gnupg \
                && curl -ks https://repo.jellyfin.org/jellyfin_team.gpg.key | apt-key add - \
                && echo "deb [arch=$( dpkg --print-architecture )] https://repo.jellyfin.org/ubuntu focal main" | tee /etc/apt/sources.list.d/jellyfin.list \
            && \
            echo "**** Install and link jellyfin-ffmpeg5 to ffmpeg ****" \
                && apt-get update \
                && apt-get install --no-install-recommends --no-install-suggests -y \
                    jellyfin-ffmpeg5 \
                    locales \
                    openssl \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
                && ln -s /usr/lib/jellyfin-ffmpeg/ffprobe /usr/local/bin/ffprobe \
            && \
            echo "**** Remove build packages ****" \
                && apt-get remove -y gnupg \
            && \
            echo ; \
        fi \
        && \
        if uname -m | grep -q x86_64 ; then \
            echo "**** Link vainfo for x86_64 ****" \
                && ln -s /usr/lib/jellyfin-ffmpeg/vainfo /usr/local/bin/vainfo \
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
                gcc \
                grc \
                python3 \
                python3-dev \
                python3-pip \
                python3-setuptools \
                unzip \
        && \
        echo "**** Install pip packages ****" \
            && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
        && \
        echo "**** Remove build packages ****" \
            && apt-get remove -y \
                gcc \
                python3-dev \
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
