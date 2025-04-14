import argparse
import json
import pathlib as pl
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, NamedTuple


class SExp:
    def to_sexp(self: object) -> str:
        class_name = self.__class__.__name__
        attrs = vars(self)

        attr_strs = []
        for value in attrs.values():
            if isinstance(value, SExp):
                attr_strs.append(value.to_sexp())
            elif isinstance(value, Enum):
                attr_strs.append(f'({value.name})')  # Use the name of the Enum member
            else:
                attr_strs.append(f'{value!r}')

        return f'({class_name})' if not attr_strs else f'({class_name} {" ".join(attr_strs)})'


RGBA = tuple[int, int, int, int]


def format_float(x):
    if x.is_integer():
        return f'{x:.1f}'
    else:
        return f'{x}'


M44 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]


def to_m44(l: list[list[float]]):
    r0 = tuple(float(x) for x in l[0])
    r1 = tuple(float(x) for x in l[1])
    r2 = tuple(float(x) for x in l[2])
    r3 = tuple(float(x) for x in l[3])

    return (r0, r1, r2, r3)


def matrix_multiply(m1: M44, m2: M44) -> M44:
    return (
        (
            m1[0][0] * m2[0][0] + m1[0][1] * m2[1][0] + m1[0][2] * m2[2][0] + m1[0][3] * m2[3][0],
            m1[0][0] * m2[0][1] + m1[0][1] * m2[1][1] + m1[0][2] * m2[2][1] + m1[0][3] * m2[3][1],
            m1[0][0] * m2[0][2] + m1[0][1] * m2[1][2] + m1[0][2] * m2[2][2] + m1[0][3] * m2[3][2],
            m1[0][0] * m2[0][3] + m1[0][1] * m2[1][3] + m1[0][2] * m2[2][3] + m1[0][3] * m2[3][3],
        ),
        (
            m1[1][0] * m2[0][0] + m1[1][1] * m2[1][0] + m1[1][2] * m2[2][0] + m1[1][3] * m2[3][0],
            m1[1][0] * m2[0][1] + m1[1][1] * m2[1][1] + m1[1][2] * m2[2][1] + m1[1][3] * m2[3][1],
            m1[1][0] * m2[0][2] + m1[1][1] * m2[1][2] + m1[1][2] * m2[2][2] + m1[1][3] * m2[3][2],
            m1[1][0] * m2[0][3] + m1[1][1] * m2[1][3] + m1[1][2] * m2[2][3] + m1[1][3] * m2[3][3],
        ),
        (
            m1[2][0] * m2[0][0] + m1[2][1] * m2[1][0] + m1[2][2] * m2[2][0] + m1[2][3] * m2[3][0],
            m1[2][0] * m2[0][1] + m1[2][1] * m2[1][1] + m1[2][2] * m2[2][1] + m1[2][3] * m2[3][1],
            m1[2][0] * m2[0][2] + m1[2][1] * m2[1][2] + m1[2][2] * m2[2][2] + m1[2][3] * m2[3][2],
            m1[2][0] * m2[0][3] + m1[2][1] * m2[1][3] + m1[2][2] * m2[2][3] + m1[2][3] * m2[3][3],
        ),
        (
            m1[3][0] * m2[0][0] + m1[3][1] * m2[1][0] + m1[3][2] * m2[2][0] + m1[3][3] * m2[3][0],
            m1[3][0] * m2[0][1] + m1[3][1] * m2[1][1] + m1[3][2] * m2[2][1] + m1[3][3] * m2[3][1],
            m1[3][0] * m2[0][2] + m1[3][1] * m2[1][2] + m1[3][2] * m2[2][2] + m1[3][3] * m2[3][2],
            m1[3][0] * m2[0][3] + m1[3][1] * m2[1][3] + m1[3][2] * m2[2][3] + m1[3][3] * m2[3][3],
        ),
    )


class Radii(NamedTuple):
    left: float
    top: float
    right: float
    bottom: float


class Rect(NamedTuple):
    left: float
    top: float
    right: float
    bottom: float


@dataclass
class SkClip:
    op: str


@dataclass
class SkClipRect(SkClip):
    rect: Rect


@dataclass
class SkClipRRect(SkClip):
    rect: Rect
    radii: Radii


@dataclass
class SkClipPath(SkClip):
    path_index: int


@dataclass
class SkClipFull(SkClip):
    pass


class SkPaint:
    pass


@dataclass
class OldPaint(SkPaint):
    color: RGBA
    blend_mode: str
    original: int


class NoPaint(SkPaint):
    pass


@dataclass
class Node:
    pass


@dataclass
class Sequence(Node):
    left: Node
    right: Node | None


@dataclass
class Command(Node):
    clip: SkClip
    m44: M44


@dataclass
class SkSave(Command):
    commands: list[Command]


@dataclass
class SkSaveLayer(Command):
    commands: list[Command]
    bounds: Rect | None
    paint: SkPaint


@dataclass
class Draw(Command):
    paint: SkPaint


@dataclass
class DrawPaint(Draw):
    pass


@dataclass
class DrawRRect(Draw):
    rect: Rect
    radii: Radii


@dataclass
class DrawRect(Draw):
    rect: Rect


@dataclass
class DrawImageRect(Draw):
    image: int
    src: Rect
    dst: Rect


@dataclass
class DrawOval(Draw):
    rect: Rect


@dataclass
class DrawTextBlob(Draw):
    x: float
    y: float
    bounds: Rect


@dataclass
class DrawPath(Draw):
    pass


def intersect_rect(a: Rect, b: Rect):
    # Calculate intersection bounds
    left = max(a.left, b.left)
    top = max(a.top, b.top)
    right = min(a.right, b.right)
    bottom = min(a.bottom, b.bottom)

    # Check if intersection is valid (non-empty)
    if left < right and top < bottom:
        return Rect(left, top, right, bottom)
    else:
        return Rect(0, 0, 0, 0)


class Parser:
    ptr: int
    sk_commands: list[dict[str, Any]]
    clip_stack: list[SkClip]
    m44_stack: list[M44]
    paint_map: list[dict]
    image_map: list[str]
    path_map: list[dict]

    def __init__(self, sk_commands):
        self.sk_commands = sk_commands
        self.clip_stack = [SkClipFull('intersect')]
        self.m44_stack = [
            ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        ]
        self.paint_map = []
        self.image_map = []
        self.path_map = []
        self.ptr = 0

    def advance(self):
        self.ptr += 1
        return self.sk_commands[self.ptr - 1]

    def peek(self):
        return self.sk_commands[self.ptr]

    def dont_stop(self):
        if len(self.clip_stack) > 1:
            # save or saveLayer was called
            return self.peek()['command'] != 'Restore'
        else:
            return self.ptr < len(self.sk_commands)

    def merge_clip(self, clip: SkClip):
        top = self.clip_stack[-1]
        if isinstance(top, SkClipFull):
            self.clip_stack[-1] = clip
        elif isinstance(clip, SkClipRect) and clip.op == 'intersect':
            if isinstance(top, SkClipRect) and top.op == 'intersect':
                rect = intersect_rect(top.rect, clip.rect)
                self.clip_stack[-1] = SkClipRect('intersect', rect)

    def parse_paint(self, paint_json: dict | None) -> SkPaint:
        if paint_json is None:
            return NoPaint()
        color = RGBA(paint_json.get('color', [0, 0, 0, 0]))
        i = len(self.paint_map)
        self.paint_map.append(paint_json)
        return OldPaint(color, paint_json.get('blendMode', 'SrcOver'), i)

    def parse_commands(self) -> list[Command]:
        res = list[Command]()

        while self.dont_stop():
            match (sk_command := self.peek())['command']:
                case 'DrawPaint':
                    self.advance()
                    res.append(
                        DrawPaint(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            self.parse_paint(sk_command['paint']),
                        )
                    )

                case 'DrawRRect':
                    self.advance()
                    rect, *radii = sk_command['coords']
                    left = radii[0][0]
                    top = radii[0][1]
                    right = radii[1][0]
                    bottom = radii[2][1]
                    res.append(
                        DrawRRect(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            self.parse_paint(sk_command['paint']),
                            Rect(*rect),
                            Radii(left, top, right, bottom),
                        )
                    )

                case 'DrawRect':
                    self.advance()
                    rect = sk_command['coords']
                    res.append(
                        DrawRect(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            self.parse_paint(sk_command['paint']),
                            Rect(*rect),
                        )
                    )

                case 'DrawOval':
                    self.advance()
                    rect = sk_command['coords']
                    res.append(
                        DrawOval(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            self.parse_paint(sk_command['paint']),
                            Rect(*rect),
                        )
                    )

                case 'DrawImageRect':
                    self.advance()
                    i = len(self.image_map)
                    self.image_map.append(sk_command['image']['data'])
                    src = sk_command['src']
                    dst = sk_command['dst']
                    paint = sk_command['paint']

                    res.append(
                        DrawImageRect(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            self.parse_paint(paint),
                            i,
                            Rect(*src),
                            Rect(*dst),
                        )
                    )

                case 'DrawTextBlob':
                    self.advance()
                    x = sk_command['x']
                    y = sk_command['y']
                    bounds = Rect(*sk_command['bounds'])
                    paint = self.parse_paint(sk_command['paint'])

                    res.append(
                        DrawTextBlob(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            paint,
                            float(x),
                            float(y),
                            bounds,
                        )
                    )

                case 'Save':
                    self.advance()
                    self.clip_stack.append(self.clip_stack[-1])
                    self.m44_stack.append(self.m44_stack[-1])
                    things = self.parse_commands()
                    self.advance()
                    self.clip_stack.pop()
                    self.m44_stack.pop()
                    res.append(SkSave(self.clip_stack[-1], self.m44_stack[-1], things))

                case 'SaveLayer':
                    self.advance()
                    self.clip_stack.append(self.clip_stack[-1])
                    self.m44_stack.append(self.m44_stack[-1])
                    things = self.parse_commands()
                    self.advance()
                    self.clip_stack.pop()
                    self.m44_stack.pop()

                    bounds = sk_command.get('bounds')
                    paint = sk_command.get(
                        'paint',
                        None,
                    )

                    res.append(
                        SkSaveLayer(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            things,
                            Rect(*bounds) if bounds else bounds,
                            self.parse_paint(paint),
                        )
                    )

                case 'ClipRect':
                    self.advance()
                    coords = sk_command['coords']
                    rect = Rect(*coords)
                    bounds = SkClipRect(sk_command['op'], rect)
                    # print(bounds)
                    self.merge_clip(bounds)
                    # print(self.clip_stack)

                case 'ClipRRect':
                    self.advance()
                    # do nothing for now
                    # union using skia python

                case 'Concat44':
                    self.advance()
                    matrix = sk_command['matrix']
                    m44 = to_m44(matrix)
                    self.m44_stack[-1] = matrix_multiply(self.m44_stack[-1], m44)
                    # print(self.m44_stack)

                case 'DrawPath':
                    self.advance()
                    paint = self.parse_paint(sk_command['paint'])

                    res.append(
                        DrawPath(
                            self.clip_stack[-1],
                            self.m44_stack[-1],
                            paint,
                        )
                    )

                case _:
                    raise NotImplementedError(f'Unknown operator {sk_command["command"]}')

        return res


# The Functional Language
# EEgg = Src(<EEgg>, <EEgg>)
#      | SrcOver(<EEgg>, <EEgg>)
#      | Rectangle(Clip, M44, LTRB, Paint)
#      | Save(<EEgg>)
#      | SaveLayer(<EE>)
#      | Empty(Clip, M44)


@dataclass
class EEgg(SExp):
    pass


class BlendMode(Enum):
    BMSrc = 0
    BMSrcOver = 1
    BMOther = 2


@dataclass
class LTRB(SExp):
    left: float
    top: float
    right: float
    bottom: float

    @staticmethod
    def from_Rect(rect: Rect):
        return LTRB(*[float(i) for i in rect])

    @staticmethod
    def from_Radii(radii: Radii):
        return LTRB(*[float(i) for i in radii])


@dataclass
class Paint(SExp):
    red: int
    blue: int
    green: int
    alpha: int
    blend_mode: BlendMode

    @staticmethod
    def from_Paint(skpaint: SkPaint):
        if isinstance(skpaint, OldPaint):
            a, r, b, g = skpaint.color
            if skpaint.blend_mode == 'Src':
                return Paint(r, g, b, a, BlendMode.BMSrc)
            elif skpaint.blend_mode == 'SrcOver':
                return Paint(r, g, b, a, BlendMode.BMSrcOver)
            else:
                return Paint(r, g, b, a, BlendMode.BMOther)
        elif isinstance(skpaint, NoPaint):
            return Paint(0, 0, 0, 255, BlendMode.BMSrcOver)
        else:
            raise NotImplementedError('NewPaint.from_Paint ???')


# datatype Thing:
# | Rect R
# | RRect R r
# | ...
# | SaveLayer Layer
# | Clip DrawCommand
# | ...
# datatype Layer:
# | Empty
# | SrcOver(Layer, DrawCommand)
# | ...
# | Blur Layer


@dataclass
class Thing(SExp):
    pass


@dataclass
class Full(Thing):
    paint: Paint


@dataclass
class Rectangle(Thing):
    ltrb: LTRB
    paint: Paint


@dataclass
class Oval(Thing):
    ltrb: LTRB
    paint: Paint


@dataclass
class TextBlob(Thing):
    x: float
    y: float
    bounds: LTRB
    paint: Paint


@dataclass
class RRect(Thing):
    rect: LTRB
    radii: LTRB
    paint: Paint


@dataclass
class ImageRect(Thing):
    src: LTRB
    dst: LTRB
    paint: Paint


@dataclass
class Path(Thing):
    paint: Paint


@dataclass
class ClipRect(Thing):
    bounds: LTRB
    thing: Thing


@dataclass
class ClipFull(Thing):
    thing: Thing


@dataclass
class SaveLayer(Thing):
    paint: Paint
    layer: 'Layer'


@dataclass
class Layer(SExp):
    pass


@dataclass
class Empty(Layer):
    pass


@dataclass
class SrcOver(Layer):
    bottom: Layer
    thing: Thing


@dataclass
class Src(Layer):
    bottom: Layer
    thing: Thing


@dataclass
class DstIn(Layer):
    bottom: Layer
    thing: Thing


@dataclass
class Other(Layer):
    bottom: Layer
    thing: Thing
    pass


def get_clip_constructor(clip: SkClip):
    match clip:
        case SkClipFull():
            return lambda x: ClipFull(x)
        case SkClipRect(_, rect):
            bounds = LTRB.from_Rect(rect)
            return lambda x: ClipRect(bounds, x)
        case _:
            raise NotImplementedError('get clip constructor unknown clip')


def get_blend_constructor(paint: SkPaint):
    match paint:
        case NoPaint():
            return SrcOver
        case OldPaint(_, 'SrcOver', _):
            return SrcOver
        case OldPaint(_, 'Src', _):
            return Src
        case OldPaint(_, 'DstIn', _):
            return DstIn
        case _:
            return Other


def skp_to_eegg(commands: list[Command]):
    def recurse(cmds: list[Command], accum: Layer) -> Layer:
        if len(cmds) == 0:
            return accum
        else:
            cmd, *rest = cmds

            clip_constructor = get_clip_constructor(cmd.clip)

            if isinstance(cmd, Draw):
                blend_mode = get_blend_constructor(cmd.paint)

                if isinstance(cmd, DrawRect):
                    thing = Rectangle(LTRB.from_Rect(cmd.rect), Paint.from_Paint(cmd.paint))
                    new_layer = blend_mode(
                        accum,
                        clip_constructor(thing),
                    )
                    return recurse(rest, new_layer)
                elif isinstance(cmd, DrawPaint):
                    thing = Full(Paint.from_Paint(cmd.paint))
                    new_layer = blend_mode(
                        accum,
                        clip_constructor(thing),
                    )
                    return recurse(rest, new_layer)
                elif isinstance(cmd, DrawTextBlob):
                    new_layer = blend_mode(
                        accum,
                        TextBlob(
                            cmd.x,
                            cmd.y,
                            LTRB.from_Rect(cmd.bounds),
                            Paint.from_Paint(cmd.paint),
                        ),
                    )
                    return recurse(rest, new_layer)
                elif isinstance(cmd, DrawOval):
                    new_layer = blend_mode(
                        accum,
                        Oval(LTRB.from_Rect(cmd.rect), Paint.from_Paint(cmd.paint)),
                    )
                    return recurse(rest, new_layer)
                elif isinstance(cmd, DrawPath):
                    new_layer = blend_mode(accum, Path(Paint.from_Paint(cmd.paint)))
                    return recurse(rest, new_layer)
                elif isinstance(cmd, DrawRRect):
                    new_layer = blend_mode(
                        accum,
                        RRect(
                            LTRB.from_Rect(cmd.rect),
                            LTRB.from_Radii(cmd.radii),
                            Paint.from_Paint(cmd.paint),
                        ),
                    )
                    return recurse(rest, new_layer)
                elif isinstance(cmd, DrawImageRect):
                    new_layer = blend_mode(
                        accum,
                        ImageRect(
                            LTRB.from_Rect(cmd.src),
                            LTRB.from_Rect(cmd.dst),
                            Paint.from_Paint(cmd.paint),
                        ),
                    )
                    return recurse(rest, new_layer)
                else:
                    raise NotImplementedError('Draw Command not Implemented' + str(cmd))
            if isinstance(cmd, SkSaveLayer):
                blend_mode = get_blend_constructor(cmd.paint)

                new_layer = blend_mode(
                    accum,
                    SaveLayer(
                        Paint.from_Paint(cmd.paint),
                        skp_to_eegg(cmd.commands),
                    ),
                )

                return recurse(rest, new_layer)
            if isinstance(cmd, SkSave):
                return recurse(cmd.commands + rest, accum)

            else:
                raise NotImplementedError('Skia Command Not Implemented ' + str(cmd))

    return recurse(commands, Empty())


def compile_json(json_thing):
    commands = Parser(skp['commands']).parse_commands()
    return skp_to_eegg(commands).to_sexp()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=pl.Path)
    parser.add_argument('egg', type=pl.Path)
    parser.add_argument('err', type=pl.Path)

    args = parser.parse_args()

    args.egg.mkdir(parents=True, exist_ok=True)
    args.err.mkdir(parents=True, exist_ok=True)

    for json_file in args.input.glob('*.json'):
        with json_file.open('rb') as f:
            skp = json.load(f)

        try:
            output = compile_json(skp)
            path = args.egg / (json_file.stem + '.egg')
            with path.open('w') as f:
                f.write('(let test' + output + ')')
        except Exception as e:
            output = f'{e}'
            path = args.err / (json_file.stem + '.txt')
            with path.open('w') as f:
                f.write(output)

    # folder = sys.argv[-1]
    # with open(filepath, 'rb') as f:
    #     skp = json.load(f)

    # commands = Parser(skp['commands']).parse_commands()

    # print(commands)

    # print()

    # print(skp_to_eegg(commands).to_sexp())
