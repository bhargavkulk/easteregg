#!/bin/bash
set -e -x
git clone https://skia.googlesource.com/skia.git
cd skia
python3 tools/git-sync-deps
python3 bin/fetch-ninja
./bin/gn gen out/debug
ninja -C out/debug dm skp_parser

# REPORT LOLW

mkdir -p report
touch report/index.html
