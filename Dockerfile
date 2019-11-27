FROM ubuntu:18.04

RUN echo "deb http://us.archive.ubuntu.com/ubuntu/ bionic main restricted" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y wget git
WORKDIR /opt
RUN wget https://dl.google.com/android/repository/android-ndk-r20b-linux-x86_64.zip
RUN apt-get install -y unzip
RUN unzip android-ndk-r20b-linux-x86_64.zip
ENV PATH=$PATH:/opt/android-ndk-r20b
RUN git clone https://github.com/openstf/minicap.git
RUN cd /opt/minicap && git submodule init && git submodule update
COPY init /opt/init
RUN chmod +x /opt/init
RUN apt-get install -y make
WORKDIR /opt
RUN wget https://dl.google.com/android/repository/platform-tools_r29.0.5-linux.zip
RUN unzip platform-tools_r29.0.5-linux.zip
ENV PATH $PATH:/opt/platform-tools

ENTRYPOINT ["/opt/init"]

