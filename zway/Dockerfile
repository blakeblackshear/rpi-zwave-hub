FROM resin/rpi-raspbian

LABEL author="Blake Blackshear <blakeb@blakeshome.com>"

ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/z-way-server/libs
ENV PATH=/opt/z-way-server:$PATH
ENV ZWAY_VERSION=2.3.6

RUN apt-get update -y \
  && apt-get install -y \
    curl \
    libarchive13 \
    libavahi-compat-libdnssd-dev \
    libc-ares2 \
    libcurl3 \
    libssl-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN ln -s /usr/lib/arm-linux-gnueabihf/libarchive.so.13 /usr/lib/arm-linux-gnueabihf/libarchive.so.12

RUN curl -SLO https://razberry.z-wave.me/z-way-server/z-way-server-RaspberryPiXTools-v${ZWAY_VERSION}.tgz \
  && tar -zxvf z-way-server-RaspberryPiXTools-v${ZWAY_VERSION}.tgz -C /opt \
  && rm z-way-server-RaspberryPiXTools-v${ZWAY_VERSION}.tgz

RUN mkdir -p /etc/z-way \
    && echo "v2.3.6" > /etc/z-way/VERSION \
    && echo "razberry" > /etc/z-way/box_type

COPY config.xml /opt/z-way-server/config.xml

# TODO: Add Niffler, MQTT Plugin, Disable auth

EXPOSE 8083

WORKDIR /opt/z-way-server

CMD ["z-way-server"]
