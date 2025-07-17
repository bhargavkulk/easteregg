import argparse
import json
from pathlib import Path


def verify_blend_mode(blend_mode: str):
    assert blend_mode in {'Src'}, f'Unknown blend mode: {blend_mode}'


def verify_paint(paint: dict):
    for key, value in paint.items():
        match key:
            case 'color':
                pass
            case 'blendMode':
                verify_blend_mode(value)
            case _:
                raise ValueError(f'Unknown paint attribute: {key}')


def verify_command(command):
    match command['command']:
        # draw commands must have paints
        case 'DrawPaint':
            assert 'paint' in command
            verify_paint(command['paint'])

        case 'Save':
            # Save has no attributes
            pass
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
