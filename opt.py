import argparse
import subprocess
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('facts', type=Path)
    parser.add_argument('eggs', type=Path)
    parser.add_argument('opt', type=Path)

    args = parser.parse_args()

    args.opt.mkdir(parents=True, exist_ok=True)

    facts = args.facts / 'command.egg'
    run = args.facts / 'extract.egg'

    for test_case in args.eggs.glob('*.txt'):
        print('[*] Optimizing', test_case.stem)
        command = (
            f'cargo run --quiet --manifest-path egglog/Cargo.toml -- {facts} {test_case} {run}'
        )
        result = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with (args.opt / (test_case.stem + '.txt')).open('wb') as f:
            f.write(result.stdout)
