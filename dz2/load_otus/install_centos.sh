#!/bin/bash
set -x
set -e
yum clean all
yum install -y git
yum install -y make
yum install -y gcc-c++

cd /opt
git clone https://github.com/python/cpython.git
cd cpython
git checkout 2.7
#./configure --with-pydebug --prefix=/tmp/python
#make -j2


