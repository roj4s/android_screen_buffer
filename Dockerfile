FROM ubuntu:18.04

RUN apt-get install -y libjpeg-turbo8 wget git
WORKDIR /opt
RUN wget https://dl.google.com/android/repository/android-ndk-r20b-linux-x86_64.zip
RUN unzip android-ndk-r20b-linux-x86_64.zip
ENV PATH=$PATH:/opt/android-ndk-r20b
RUN git clone https://github.com/openstf/minicap.git
RUN cd /opt/minicap && git submodule init && git submodule update

ENTRYPOINT ["init"]

