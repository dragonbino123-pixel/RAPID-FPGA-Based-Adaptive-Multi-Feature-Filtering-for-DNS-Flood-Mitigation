#!/bin/sh
set -eu
cd "$(dirname "$0")"
"${PYTHON:-python3}" download_ddidd.py
mkdir -p vendor/ddidd
tar -xzf vendor/ddidd-0.1.tar.gz -C vendor/ddidd
"${PYTHON:-python3}" prepare_ddidd.py
cd ddidd_adapter
"${CXX:-c++}" -std=c++11 -O2 ddidd.cc fq.cc hcf.cc wild.cc filter.cc utils.cc -o ddidd
"${CXX:-c++}" -std=c++11 -O2 transport.cpp -o transport
