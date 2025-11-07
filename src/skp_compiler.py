import argparse
import json
import pathlib
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Optional

from lambda_skia import (
    BlendMode,
    Color,
    Difference,
    Draw,
    Empty,
    Full,
    Geometry,
    ImageRect,
    Intersect,
    Layer,
    LinearGradient,
    Oval,
    Paint,
    Path,
    RadialGradient,
    Rect,
    RRect,
    SaveLayer,
    TextBlob,
    Transform,
    mk_color,
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


I = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def mm(a, b):
    result = [0.0] * 16
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i * 4 + j] += a[i * 4 + k] * b[k * 4 + j]
    return result


def radii_to_ltrb(radii: list[list[float]]) -> list[float]:
    left = radii[0][0]
    top = radii[0][1]
    right = radii[1][0]
    bottom = radii[2][1]
    return [left, top, right, bottom]


type ClipOp = Literal['intersect'] | Literal['difference']


@dataclass
class State:
    clip: Geometry
    transform: list[float]
    layer: Layer
    is_save_layer: bool
    paint: Optional[Paint]  # Only not none, if is_save_layer is True


def compile_skp_to_lskia(commands: list[dict[str, Any]]) -> Layer:
    """Compiles serialized Skia commands into λSkia"""
    stack: list[State] = [State(Full(), I, Empty(), False, None)]

    for i, command_data in enumerate(commands):

        def compile_paint(json_paint: Optional[dict]) -> Paint:
            warn(f'[INFO] paint: {list(json_paint.keys()) if json_paint else None}')
            if json_paint is None:
                color = Color(1.0, 0.0, 0.0, 0.0)
                blend_mode: BlendMode = '(SrcOver)'
                return Paint(color, blend_mode, '(Solid)', '(IdFilter)', i)
            else:
                for key in json_paint.keys():
                    if key not in (
                        'colorfilter',
                        'shader',
                        'color',
                        'blendMode',
                        'antiAlias',
                        'dither',
                        'strokeWidth',
                        'style',
                        'cap',
                        'strokeJoin',
                        'strokeMiter',
                    ):
                        raise NotImplementedError(key, i)

                color = mk_color(json_paint.get('color', [255, 0, 0, 0]))
                if 'shader' in json_paint.keys():
                    # replace flat color with shader
                    # So the shader is inside SkLocalMatrixShader
                    inner_shader = json_paint['shader']['values']

                    if '01_SkLinearGradient' in inner_shader:
                        is_opaque = all(
                            i[0] == 1 for i in inner_shader['01_SkLinearGradient']['01_colorArray']
                        )
                        color = LinearGradient(is_opaque)
                    elif '01_SkRadialGradient' in inner_shader:
                        is_opaque = all(
                            i[0] == 1 for i in inner_shader['01_SkRadialGradient']['01_colorArray']
                        )
                        color = RadialGradient(is_opaque)
                    else:
                        raise NotImplementedError('unknown shader')

                json_style = json_paint.get('style', 'fill')
                if json_style == 'fill':
                    style = '(Solid)'
                elif json_style == 'stroke':
                    style = '(Stroke)'
                else:
                    raise NotImplementedError(f'Unknown style {json_style}')

                if 'colorfilter' in json_paint:
                    json_color_filter = json_paint['colorfilter']
                    if json_color_filter['name'] == 'SkRuntimeColorFilter':
                        # I AM ASSUMING ALL RUNTIME FILTERS ARE LUMINANCE FILTERS
                        assert 'sk_luma' in json_color_filter['values']['01_string']
                        color_filter = '(LumaFilter)'
                    else:
                        raise NotImplementedError(f'{json_color_filter["name"]} is not implemented')
                else:
                    color_filter = '(IdFilter)'

                blend_mode = '(' + json_paint.get('blendMode', 'SrcOver') + ')'

                return Paint(color, blend_mode, style, color_filter, i)

        def push_clip(g: Geometry, op: ClipOp):
            # given g and op
            # [..., s(m, c, l, b, p)]
            # -->
            # [..., s(m, op(c, g), l, b, p)]
            stack[-1].clip = (Intersect if op == 'intersect' else Difference)(stack[-1].clip, g)

        def push_transform(m: list[float]):
            # given m₂
            # [..., s(m₁, c, l, b, p)]
            # -->
            # [..., s(m₁ × m₂, c, l, b, p)]
            stack[-1].transform = mm(stack[-1].transform, m)

        def mk_draw(g: Geometry):
            p = compile_paint(command_data.get('paint', None))
            # given g and p
            # [..., s(m, c, l, b, p')]
            # -->
            # [..., s(m, c, Draw(l, g, p, c, m), b, p')]
            stack[-1].layer = Draw(
                stack[-1].layer, g, p, stack[-1].clip, Transform(stack[-1].transform)
            )

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
            case 'DrawTextBlob':
                x: float = command_data['x']
                y: float = command_data['y']
                bounds: list[float] = command_data['bounds']
                mk_draw(TextBlob(x / 1.0, y / 1.0, *[bound / 1.0 for bound in bounds]))
            case 'DrawImageRect':
                dst: list[float] = command_data['dst']
                mk_draw(ImageRect(*[d / 1.0 for d in dst]))
            case 'DrawRect':
                coords: list[float] = command_data['coords']
                mk_draw(Rect(*[coord / 1.0 for coord in coords]))
            case 'DrawOval':
                coords: list[float] = command_data['coords']
                mk_draw(Oval(*[coord / 1.0 for coord in coords]))
            case 'DrawRRect':
                coords, *radii = command_data['coords']
                ltrb_radii = radii_to_ltrb(radii)
                mk_draw(RRect(*([i / 1.0 for i in coords + ltrb_radii])))
            case 'DrawPath':
                mk_draw(Path(i))
            case 'DrawTextBlob':
                x: float = command_data['x']
                y: float = command_data['y']
                bounds: list[float] = command_data['bounds']
                mk_draw(TextBlob(x / 1.0, y / 1.0, *[bound / 1.0 for bound in bounds]))
            case 'DrawImageRect':
                dst: list[float] = command_data['dst']
                mk_draw(ImageRect(*[d / 1.0 for d in dst]))
            case 'ClipRect':
                coords: list[float] = command_data['coords']
                op: ClipOp = command_data['op']
                push_clip(Rect(*[coord / 1.0 for coord in coords]), op)
            case 'ClipRRect':
                raise NotImplementedError('Pausing this for now')
                # coords, *radii = command_data['coords']
                # ltrb_radii = radii_to_ltrb(radii)
                # op: ClipOp = command_data['op']
                # push_clip(RRect(*([i / 1.0 for i in coords + ltrb_radii])), op)
            case 'ClipPath':
                raise NotImplementedError('Pausing this for now')
                # op: ClipOp = command_data['op']
                # push_clip(Path(i), op)
            case 'Concat44':
                matrix: list[float] = [i for s in command_data['matrix'] for i in s]
                push_transform(matrix)
            case _:
                raise NotImplementedError(command + ' @ ' + str(i))

    assert len(stack) == 1, 'Unbalanced Save/SaveLayer'
    return stack[-1].layer


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=pathlib.Path)
    parser.add_argument('--output', '-o', type=pathlib.Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    layer = compile_skp_to_lskia(skp['commands'])

    if args.output:
        with args.output.open('w') as f:
            f.write(layer)
    else:
        print('(let test ' + layer.sexp() + ')')
