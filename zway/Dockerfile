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

# extract custom automation source code to /opt/z-way-server/blakeshome
RUN curl -SLO https://github.com/blakeblackshear/home-automation/archive/v2.3.6-custom.tar.gz \
  && tar -zxvf v2.3.6-custom.tar.gz -C /opt/z-way-server \
  && mv /opt/z-way-server/home-automation-2.3.6-custom /opt/z-way-server/blakeshome \
  && rm v2.3.6-custom.tar.gz

# install basemodule
RUN curl -SLO https://github.com/maros/Zway-BaseModule/archive/1.10.tar.gz \
  && tar -zxvf 1.10.tar.gz -C /opt/z-way-server/blakeshome/userModules \
  && mv /opt/z-way-server/blakeshome/userModules/Zway-BaseModule-1.10 /opt/z-way-server/blakeshome/userModules/BaseModule \
  && rm 1.10.tar.gz

# install websocket bridge
RUN curl -SLO https://github.com/blakeblackshear/zway-websocket/archive/v0.0.4.tar.gz \
  && tar -zxvf v0.0.4.tar.gz -C /opt/z-way-server/blakeshome/userModules \
  && mv /opt/z-way-server/blakeshome/userModules/zway-websocket-0.0.4 /opt/z-way-server/blakeshome/userModules/WebSockets \
  && rm v0.0.4.tar.gz

# install cooper scene controllers
RUN curl -SLO https://github.com/blakeblackshear/zway-cooper-scene-controllers/archive/v0.0.1.tar.gz \
  && tar -zxvf v0.0.1.tar.gz -C /opt/z-way-server/blakeshome/userModules \
  && mv /opt/z-way-server/blakeshome/userModules/zway-cooper-scene-controllers-0.0.1 /opt/z-way-server/blakeshome/userModules/CooperSceneControllers \
  && rm v0.0.1.tar.gz

# install niffler
RUN curl -SLO https://github.com/blakeblackshear/Niffler/archive/v0.0.1.tar.gz \
  && tar -zxvf v0.0.1.tar.gz -C /opt/z-way-server/blakeshome/userModules \
  && mv /opt/z-way-server/blakeshome/userModules/Niffler-0.0.1 /opt/z-way-server/blakeshome/userModules/Niffler \
  && rm v0.0.1.tar.gz

# default the UI to expert
COPY htdocs/index.html /opt/z-way-server/htdocs/index.html

RUN mkdir -p /etc/z-way \
    && echo "v2.3.6" > /etc/z-way/VERSION \
    && echo "razberry" > /etc/z-way/box_type

COPY config.xml /opt/z-way-server/config.xml
COPY storage/configjson-06b2d3b23dce96e1619d2b53d6c947ec.json /opt/z-way-server/blakeshome/storage/configjson-06b2d3b23dce96e1619d2b53d6c947ec.json
EXPOSE 8083

WORKDIR /opt/z-way-server

CMD ["z-way-server"]
