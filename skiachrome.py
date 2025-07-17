import argparse
import json
from pathlib import Path


def verify_paint(paint: dict):
    pass


def verify_command(command):
    match command['command']:
        # draw commands must have paints
        case 'DrawPaint':
            assert 'paint' in command
            verify_paint(command['paint'])
        case _:
            raise ValueError(f'Unknown command: {command["command"]}')


def verify_skp(commands):
    for i, command in enumerate(commands['commands']):
        try:
            verify_command(command)
        except Exception as e:
            raise ValueError(f'Error at {i}: {str(e)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    verify_skp(skp)
