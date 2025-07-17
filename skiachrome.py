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
            case 'antiAlias':
                pass
            case _:
                raise ValueError(f'Unknown paint attribute: {key}')


def verify_command(command):
    match command['command']:
        # draw commands must have paints
        case 'DrawPaint':
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawRect':
            assert 'coords' in command  # location
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawTextBlob':
            assert 'x' in command  # location
            assert 'y' in command
            assert 'runs' in command  # text data
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawImageRect':
            assert 'image' in command  # src image
            assert 'src' in command  # crop size of the image
            assert 'dst' in command  # dst coords to be mapped to
            assert 'sampling' in command  # TODO: figure this out
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'Save' | 'Restore':
            # save and restore has no attributes
            pass
        case 'SaveLayer':
            assert 'bounds' in command  # bounds are a suggestion, so they mean nothing.
            # clip is more meaningful

            # paint may not be in savelayer
            # defaults to black opaque srcover
            if 'paint' in command:
                verify_paint(command['paint'])
        case 'Concat44':
            # concat44 has only 1 possible attribute
            assert 'matrix' in command
        case 'ClipRect':
            assert 'coords' in command
            assert 'op' in command
            assert command['op'] in {'intersect', 'difference'}, command['op']
        case 'ClipRRect':
            assert 'coords' in command  # ltrb and radii
            assert 'op' in command
            assert command['op'] in {'intersect', 'difference'}, command['op']
        case _:
            raise ValueError(f'Unknown command: {command["command"]}')


def verify_skp(commands):
    for i, command in enumerate(commands['commands']):
        try:
            verify_command(command)
        except Exception as e:
            raise ValueError(f'Error at {i}: {command["command"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    verify_skp(skp)
