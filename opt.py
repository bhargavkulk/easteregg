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

    for test_case in args.eggs.glob('*.egg'):
        command = f'cargo run --manifest-path egglog/Cargo.toml -- {facts} {test_case} {run}'
        print(command)
        result = subprocess.run(
            command.split(),
        )
