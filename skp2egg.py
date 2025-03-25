import json
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, NamedTuple, get_args


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
class Clip:
    op: str


@dataclass
class ClipRect(Clip):
    rect: Rect


@dataclass
class ClipRRect(Clip):
    rect: Rect
    radii: Radii


@dataclass
class ClipPath(Clip):
    path_index: int


@dataclass
class ClipFull(Clip):
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
    clip: Clip
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


class Parser:
    ptr: int
    sk_commands: list[dict[str, Any]]
    clip_stack: list[Clip]
    m44_stack: list[M44]
    paint_map: list[dict]
    image_map: list[str]
    path_map: list[dict]

    def __init__(self, sk_commands):
        self.sk_commands = sk_commands
        self.clip_stack = [ClipFull('intersect')]
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
                    bounds = ClipRect(sk_command['op'], rect)
                    self.clip_stack[-1] = bounds

                case 'ClipRRect':
                    self.advance()
                    rect, *radii = sk_command['coords']
                    left = radii[0][0]
                    top = radii[0][1]
                    right = radii[1][0]
                    bottom = radii[2][1]
                    self.clip_stack[-1] = ClipRRect(
                        sk_command['op'],
                        Rect(*rect),
                        Radii(left, top, right, bottom),
                    )

                case 'ClipPath':
                    self.advance()
                    op = sk_command['op']
                    i = len(self.path_map)
                    self.path_map.append(sk_command['path'])
                    self.clip_stack[-1] = ClipPath(op, i)

                case 'Concat44':
                    self.advance()
                    m44: M44 = tuple(tuple(i) for i in sk_command['matrix'])  # pyright: ignore
                    self.m44_stack[-1] = matrix_multiply(self.m44_stack[-1], m44)

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
class Rectangle(Thing):
    ltrb: LTRB
    paint: Paint


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
class Other(Layer):
    bottom: Layer
    thing: Thing


def get_blend_constructor(paint: SkPaint):
    match paint:
        case NoPaint():
            return SrcOver
        case OldPaint(_, 'SrcOver', _):
            return SrcOver
        case OldPaint(_, 'Src', _):
            return Src
        case _:
            return Other


def skp_to_eegg(commands: list[Command]):
    def recurse(cmds: list[Command], accum: Layer) -> Layer:
        if len(cmds) == 0:
            return accum
        else:
            cmd, *rest = cmds

            if isinstance(cmd, Draw):
                blend_mode = get_blend_constructor(cmd.paint)

                if isinstance(cmd, DrawRect):
                    new_layer = blend_mode(
                        accum,
                        Rectangle(LTRB.from_Rect(cmd.rect), Paint.from_Paint(cmd.paint)),
                    )
                    return recurse(rest, new_layer)
                else:
                    raise NotImplementedError('Draw Command not Implemented')
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

            else:
                raise NotImplementedError('Skia Command Not Implemented')

    return recurse(commands, Empty())


if __name__ == '__main__':
    filepath = sys.argv[-1]
    with open(filepath, 'rb') as f:
        skp = json.load(f)

    commands = Parser(skp['commands']).parse_commands()

    print(commands)

    print()

    print(skp_to_eegg(commands).to_sexp())
