import argparse
import json
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, reveal_type

from lambda_skia import (
    BlendMode,
    Color,
    Difference,
    Draw,
    Empty,
    Full,
    Geometry,
    Intersect,
    Layer,
    Paint,
    Rectangle,
    SaveLayer,
    mk_color,
    pretty_print_layer,
)

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


@dataclass
class State:
    # matrix: list[float]?
    clip: Geometry
    layer: Layer
    is_save_layer: bool
    paint: Optional[Paint]  # Only not none, if is_save_layer is True


def compile_paint(json_paint: Optional[dict]) -> Paint:
    warn(f'[INFO] paint: {list(json_paint.keys()) if json_paint else None}')
    if json_paint is None:
        color = Color(1.0, 0.0, 0.0, 0.0)
        blend_mode: BlendMode = '(SrcOver)'
        return Paint(color, blend_mode)
    else:
        color = mk_color(json_paint.get('color', [255, 0, 0, 0]))
        blend_mode = '(' + json_paint.get('blendMode', 'SrcOver') + ')'
        return Paint(color, blend_mode)


def compile_to_lambda_skia(commands: list[dict[str, Any]]) -> Layer:
    """Compiles serialized Skia commands into λSkia"""
    stack: list[State] = [State(Full(), Empty(), False, None)]
    # print(stack)
    # input()
    for i, command_data in enumerate(commands):

        def mk_clip(g: Geometry, op: Literal['intersect'] | Literal['difference']):
            # given g and op
            # [..., s(m, c, l, b, p)]
            # -->
            # [..., s(m, op(c, g), l, b, p)]
            stack[-1].clip = (Intersect if op == 'intersect' else Difference)(stack[-1].clip, g)

        def mk_draw(g: Geometry):
            p = compile_paint(command_data.get('paint', None))
            # given g and p
            # [..., s(m, c, l, b, p')]
            # -->
            # [..., s(m, c, Draw(l, g, p, c), b, p')]
            stack[-1].layer = Draw(stack[-1].layer, g, p, stack[-1].clip)

        match command := command_data['command']:
            case 'Save':
                # [..., s₁(m, c, l, b, p)]
                # -->
                # [..., s₁(m, c, l, b, p), s₂(m, c, l, b, p)]
                new_state = deepcopy(stack[-1])
                new_state.is_save_layer = False
                stack.append(new_state)
            case 'SaveLayer':
                # given p₁
                # [..., s₁(m, c, l, b, p₁)]
                # [..., s₁(m, c, l, b, p₁), s₂(m, c, Empty(), b, p₂)]
                new_state = deepcopy(stack[-1])
                new_state.layer = Empty()
                new_state.is_save_layer = True
                new_state.paint = compile_paint(command_data.get('paint', None))
                stack.append(new_state)
            case 'Restore':
                saved_state: State = stack.pop()
                if saved_state.is_save_layer:
                    assert saved_state.paint is not None
                    # [..., s₁(m₁, c₁, l₁, b₁, p₁), s₂(m₂, c₂, l₂, True, p₂)]
                    # -->
                    # [..., s₁(m₁, c₁, SaveLayer(l₁, l₂, p₂), b₁, p₁)]
                    stack[-1].layer = SaveLayer(
                        stack[-1].layer, saved_state.layer, saved_state.paint
                    )
                else:
                    # [..., s₁(m₁, c₁, l₁, b₁, p₁), s₂(m₂, c₂, l₂, True, None)]
                    # -->
                    # [..., s₁(m₁, c₁, l₂, b₁, p₁)]
                    stack[-1].layer = saved_state.layer
            case 'DrawPaint':
                mk_draw(Full())
            case 'DrawRect':
                coords: list[float] = command_data['coords']
                mk_draw(Rectangle(*coords))
            case 'ClipRect':
                coords: list[float] = command_data['coords']
                op: Literal['intersect'] | Literal['difference'] = command_data['op']
                mk_clip(Rectangle(*coords), op)
            case _:
                raise NotImplementedError(command)
        # print(stack)
        # input()
    assert len(stack) == 1, 'Unbalanced Save/SaveLayer'

    return stack[-1].layer


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    layer = compile_to_lambda_skia(skp['commands'])

    if args.output:
        with args.output.open('w') as f:
            f.write(layer)
    else:
        print(pretty_print_layer(layer))
