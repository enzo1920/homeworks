#!/bin/bash
set -x
set -e

apt-get install -y git
apt-get install -y make
apt-get install -y gcc
#apt-get install -y mc
cd /opt
git clone https://github.com/python/cpython.git
cd cpython
git checkout 2.7
./configure --with-pydebug --prefix=/tmp/python
make -j2

