#!/bin/bash
set -e -x
# if [ ! -d skia ]; then
#     git clone https://skia.googlesource.com/skia.git
# fi
if [ ! -d egglog ]; then
    git clone https://github.com/egraphs-good/egglog/
fi

rm -rf eegg err opt report

# cd skia
# python3 tools/git-sync-deps
# python3 bin/fetch-ninja
# ./bin/gn gen out/debug
# ninja -C out/debug dm skp_parser
# cd ..

cd egglog
cargo install --locked cargo-nextest --version 0.9.85
cargo build
cd ..

mkdir -p report
touch report/index.html

python3 -m venv venv

$(pwd)/venv/bin/python -m pip install playwright
$(pwd)/venv/bin/python -m playwright install
## SHOULD PROBABLY CACHE THE SKPS TALK TO PAVEL ABOUT THIS
$(pwd)/venv/bin/python skp2egg.py json eegg err
$(pwd)/venv/bin/python opt.py egg eegg opt
$(pwd)/venv/bin/python gen_report.py json eegg err opt report

ls eegg
ls err
