#!/bin/bash
set -e -x
if [ ! -d skia ]; then
    git clone https://skia.googlesource.com/skia.git
fi
cd skia
python3 tools/git-sync-deps
python3 bin/fetch-ninja
./bin/gn gen out/debug
ninja -C out/debug dm skp_parser

# REPORT LOLW

mkdir -p report
touch report/index.html
poetry run python dl_skps.py urls.toml skps json
