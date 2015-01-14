FROM ufaldsg/cloud-asr-base
MAINTAINER Ondrej Klejch

#
# Install PyKaldi.
#
# Prerequesities.
RUN apt-get update
RUN apt-get install -y build-essential libatlas-base-dev python-dev python-pip git wget
# Add pykaldi source files
WORKDIR /app
RUN git clone --recursive https://github.com/UFAL-DSG/pykaldi.git
WORKDIR /app/pykaldi
RUN make install
RUN ldconfig
# Test setup
RUN python -c 'import fst; import kaldi.decoders'
# Remove Pykaldi source files
WORKDIR /app
RUN rm -rf pykaldi

WORKDIR /opt/app
ADD download_models.sh /opt/app/download_models.sh
RUN bash download_models.sh

ADD . /opt/app
CMD while true; do python run.py; done
