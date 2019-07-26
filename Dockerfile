FROM alpine:3.10
LABEL maintainer="Josh.5 <jsunnex@gmail.com>"

### Environment variables
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Add pip requirements
COPY /requirements.txt /tmp/requirements.txt

### Install pyinotify service.
RUN apk update \
 && apk add --no-cache \
        python3 \
        ffmpeg \
 && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt  \
 && rm -rf /tmp/* /var/tmp/*

### Add local files
COPY / /app/

RUN addgroup -S unmanic && adduser -S -g unmanic unmanic \
    # For Cache, Code, Configs, and Library Files
    && mkdir -p /tmp/unmanic /app /config/.unmanic /library \
    && chown -R unmanic /tmp/unmanic /app /config/ /library && chgrp -R unmanic /tmp/unmanic /app /config/ /library

EXPOSE 8888

# Needed to be set since paths in python code aren't handled properly
WORKDIR /app

# Set User to Unmanic
USER unmanic

CMD ["/usr/bin/python3", "-u" , "/app/service.py"]