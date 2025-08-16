#!/bin/bash
set -e -x
set -o pipefail

export PATH=~/.cargo/bin:$PATH

rustup update

if [ -d egglog ]; then
    rm -rf egglog
fi

git clone https://github.com/egraphs-good/egglog/ --quiet

cargo build --manifest-path egglog/Cargo.toml --quiet

# cd skia
# python3 tools/git-sync-deps
# python3 bin/fetch-ninja
# ./bin/gn gen out/debug
# ninja -C out/debug dm skp_parser
# cd ..

python3 -m venv venv
$(pwd)/venv/bin/python -m pip install uv
$(pwd)/venv/bin/python -m uv sync

rm -rf report
$(pwd)/venv/bin/python -m uv run make_report.py new-bench/json rsrc report
