#!/bin/bash
set -e -x
# if [ ! -d skia ]; then
#     git clone https://skia.googlesource.com/skia.git
# fi
if [ ! -d egglog ]; then
    git clone https://github.com/egraphs-good/egglog/
fi

rm -rf report

# cd skia
# python3 tools/git-sync-deps
# python3 bin/fetch-ninja
# ./bin/gn gen out/debug
# ninja -C out/debug dm skp_parser
# cd ..

#cd egglog
#cargo install --locked cargo-nextest --version 0.9.85
#cargo build
#cd ..

python3 -m venv venv
$(pwd)/venv/bin/python -m pip install uv
$(pwd)/venv/bin/python -m uv sync
$(pwd)/venv/bin/python -m uv run make_report.py new-bench/json rsrc report

#$(pwd)/venv/bin/python -m pip install playwright sexpdata yattag skia_python-138.0rc1-cp312-cp312-manylinux_2_28_x86_64.whl
#$(pwd)/venv/bin/python -m playwright install
#$(pwd)/venv/bin/python make_report.py new-bench/json rsrc report
