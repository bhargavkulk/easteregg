#!/bin/bash
set -e -x
set -o pipefail

export PATH=~/.cargo/bin:$PATH

RUSTUP_TERM_COLOR=never rustup update

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

rm -rf report
uv sync
uv run make_report.py bench/json rsrc report
