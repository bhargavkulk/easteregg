import argparse
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

I = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def mm(a, b):
    result = [[0.0 for _ in range(4)] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i][j] += a[i][k] * b[k][j]
    return result


def sexp_ltrb(ltrb):
    return '(LTRB ' + ' '.join(str(i) for i in ltrb) + ')'


# returns paint and blend mode
def compile_paint(paint_json):
    color = paint_json.get('color', [0, 0, 0, 255])
    blend_mode = paint_json.get('blendMode', 'SrcOver')

    return (
        '(Paint ' + ' '.join(str(i) for i in color) + ' (BM' + blend_mode + ')' + ')',
        blend_mode,
    )


# Thanks to ChatGPT for reminding me that everything is a reference in python
@dataclass
class State:
    matrix: Any
    clip: str
    layer: str
    is_save_layer: bool
    save_layer: Any

    def __init__(self):
        self.matrix = I
        self.clip = 'ClipFull'
        self.layer = '(Empty)'
        self.is_save_layer = False
        self.save_layer = None

    def wrap_state(self, shape):
        shape = (
            '(Transform '
            + ' '.join(str(element) for row in self.matrix for element in row)
            + ' '
            + shape
            + ')'
        )
        shape = '(' + self.clip + ' ' + shape + ')'

        return shape


def compile(commands: list):
    state_stack = []
    curr_state = State()

    for command_data in commands:
        match command := command_data['command']:
            case 'Save':
                curr_state.is_save_layer = False
                state_stack.append(deepcopy(curr_state))
            case 'SaveLayer':
                curr_state.is_save_layer = True
                curr_state.save_layer = command_data
                state_stack.append(deepcopy(curr_state))
                curr_state.layer = '(Empty)'
            case 'Restore':
                old_state = state_stack.pop()
                if not old_state.is_save_layer:
                    old_state.layer = curr_state.layer
                    curr_state = old_state
                else:
                    paint, blend_mode = compile_paint(old_state.save_layer.get('paint', {}))
                    old_state.layer = (
                        f'({blend_mode} '
                        + old_state.layer
                        + ' '
                        + old_state.wrap_state(
                            '(SaveLayer ' + paint + ' ' + curr_state.layer + ')',
                        )
                        + ')'
                    )
                    curr_state = old_state

                """
                old_state.layer = (BlendMode (old_state.layer) (SaveLayer curr_state.layer))
                """

            case 'DrawRect':
                ltrb = sexp_ltrb(command_data['coords'])
                paint, blend_mode = compile_paint(command_data.get('paint', {}))
                shape = '(Rect ' + ltrb + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'({blend_mode} ' + curr_state.layer + ' ' + shape + ')'
            case 'DrawOval':
                ltrb = sexp_ltrb(command_data['coords'])
                paint, blend_mode = compile_paint(command_data.get('paint', {}))
                shape = '(Oval ' + ltrb + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'({blend_mode} ' + curr_state.layer + ' ' + shape + ')'
            case 'ClipRect':
                ltrb = sexp_ltrb(command_data['coords'])
                op = '(I)' if command_data['op'] == 'intersect' else '(D)'
                curr_state.clip = 'ClipRect ' + ltrb + op
            case 'Concat44':
                matrix = command_data['matrix']
                curr_state.matrix = mm(curr_state.matrix, matrix)
            case 'DrawTextBlob':
                ltrb = sexp_ltrb(command_data['bounds'])
                paint, blend_mode = compile_paint(command_data.get('paint', {}))
                shape = '(TextBlob ' + ltrb + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'({blend_mode} ' + curr_state.layer + ' ' + shape + ')'
            case _:
                raise Exception(f'Unsupported command: {command}')

    assert len(state_stack) == 0
    return curr_state.layer


def compile_json_skp(skp):
    return compile(skp['commands'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    try:
        eegg = compile_json_skp(skp)

        if args.output:
            with args.output.open('w') as f:
                f.write(eegg)
        else:
            print(eegg)
    except Exception as e:
        print(f'[{args.input.name}]', str(e))
