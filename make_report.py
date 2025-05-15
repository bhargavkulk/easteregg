import argparse
import json
import shutil
import subprocess
from pathlib import Path

from printegg import Formatter, parse_sexp
from skp2eegg import compile_json_skp

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # benchmarks
    parser.add_argument('bench', type=Path)
    # output folder
    parser.add_argument('output', type=Path)

    args = parser.parse_args()

    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir()

    benchmarks = []
    formatter = Formatter()

    for benchmark in args.bench.glob('*.json'):
        bench_name = benchmark.stem
        data = dict()
        data['name'] = bench_name

        with benchmark.open('rb') as f:
            skp = json.load(f)

        # 1. Compile to Egg
        egg = None
        try:
            egg = compile_json_skp(skp)
        except Exception as e:
            error_msg = str(e)
            err_file = args.output / (bench_name + '__NOOPT_ERR.html')
            with err_file.open('w') as f:
                f.write(f)
            data['compile_error'] = str(err_file)
            continue

        assert egg is not None

        egg_file = args.output / (bench_name + '__NOOPT.html')
        with egg_file.open('w') as f:
            print(egg)
            f.write(egg)

        fmt_egg_file = args.output / (bench_name + '__NOOPT_FMT.html')
        with fmt_egg_file.open('w') as f:
            formatter.fmt_layer(parse_sexp(egg))
            fmt_egg = formatter.buffer.getvalue()
            formatter.clear()
            f.write(fmt_egg)

        data['egg_file'] = str(egg_file)
        data['fmt_egg_file'] = str(fmt_egg_file)

        # 2. Optimize
        #    FILL IN LATER

        # 3. Collect Stats, file names
        #    Count SaveLayers before and after

        benchmarks.append(data)

    # 6. Make Report
    for benchmark in benchmarks:
        print(benchmark)
