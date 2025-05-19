import argparse
import json
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

warnings_var: ContextVar[list[str]] = ContextVar('warnings', default=[])


def get_reset_warnings():
    warnings = warnings_var.get()
    warnings_var.set([])
    return warnings


def warn(msg):
    warnings = warnings_var.get()
    warnings.append(msg)
    warnings_var.set(warnings)


I = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def mm(a, b):
    result = [[0.0 for _ in range(4)] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i][j] += a[i][k] * b[k][j]
    return result


def sexp_ltrb(ltrb):
    return '(LTRB ' + ' '.join(str(float(i)) for i in ltrb) + ')'


def radii_to_ltrb(radii):
    left = radii[0][0]
    top = radii[0][1]
    right = radii[1][0]
    bottom = radii[2][1]
    return [left, top, right, bottom]


# returns paint and blend mode
def compile_paint(paint_json: dict | None):
    color = [255, 0, 0, 0]
    blend_mode = 'SrcOver'

    if paint_json is None:
        color = [255, 0, 0, 0]
        blend_mode = 'SrcOver'
    else:
        if blend_mode in paint_json.keys():
            blend_mode = paint_json['blend_mode']
            if blend_mode not in ('Src', 'SrcOver', 'DstIn'):
                blend_mode = 'Other'
                warn(f'[WARN] UNKNOWN BLEND MODE {blend_mode}')
            color = paint_json.get('color', [255, 0, 0, 0])
        elif color in paint_json.keys():
            blend_mode = 'SrcOver'
            color = paint_json.get('color', [255, 0, 0, 0])
        else:
            color = [0, 0, 0, 0]
            warn(f'[WARN] not a blend mode')
            if 'image_filter' in paint_json.keys():
                blend_mode = 'ImageFilter'
            else:
                blend_mode = 'OtherFilter'

    return (
        '(Paint ' + ' '.join(str(i) for i in color) + ' (' + blend_mode + ')' + ')',
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
        self.clip = 'Clip (ClipFull)'
        self.layer = '(Empty)'
        self.is_save_layer = False
        self.save_layer = None

    def wrap_state(self, shape):
        shape = (
            '(Transform (M4x4 '
            + ' '.join(str(element) for row in self.matrix for element in row)
            + ') '
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
                    paint, blend_mode = compile_paint(old_state.save_layer.get('paint', None))
                    old_state.layer = (
                        f'(Blend ({blend_mode}) '
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
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(Rect ' + ltrb + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
            case 'DrawRRect':
                coords, *radii = command_data['coords']
                ltrb = sexp_ltrb(coords)
                radii = sexp_ltrb(radii_to_ltrb(radii))
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(RRect ' + ltrb + ' ' + radii + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
            case 'DrawPath':
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(Path ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
            case 'DrawOval':
                ltrb = sexp_ltrb(command_data['coords'])
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(Oval ' + ltrb + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
            case 'ClipRect':
                ltrb = sexp_ltrb(command_data['coords'])
                op = '(I)' if command_data['op'] == 'intersect' else '(D)'
                curr_state.clip = 'Clip (ClipRect ' + ltrb + ' ' + op + ')'
            case 'ClipRRect':
                coords, *radii = command_data['coords']
                ltrb = sexp_ltrb(coords)
                radii = sexp_ltrb(radii_to_ltrb(radii))
                op = '(I)' if command_data['op'] == 'intersect' else '(D)'
                curr_state.clip = 'Clip (ClipRRect ' + ltrb + ' ' + radii + ' ' + op + ')'
            case 'Concat44':
                matrix = command_data['matrix']
                curr_state.matrix = mm(curr_state.matrix, matrix)
            case 'DrawTextBlob':
                ltrb = sexp_ltrb(command_data['bounds'])
                x = str(float(command_data['x']))
                y = str(float(command_data['y']))
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(TextBlob ' + x + ' ' + y + ' ' + ltrb + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
            case 'DrawPaint':
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(Fill ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
            case 'DrawImageRect':
                src = sexp_ltrb(command_data['src'])
                dst = sexp_ltrb(command_data['dst'])
                paint, blend_mode = compile_paint(command_data.get('paint', None))
                shape = '(ImageRect ' + src + ' ' + dst + ' ' + paint + ')'
                shape = curr_state.wrap_state(shape)
                curr_state.layer = f'(Blend ({blend_mode}) ' + curr_state.layer + ' ' + shape + ')'
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
