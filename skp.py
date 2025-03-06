import json
import sys
from dataclasses import dataclass
from typing import Any, NamedTuple

RGBA = tuple[int, int, int, int]

type M44 = tuple[
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
class ClipBounds:
    op: str
    pass


@dataclass
class RectBounds(ClipBounds):
    rect: Rect


@dataclass
class RRectBounds(ClipBounds):
    rect: Rect
    radii: Radii


@dataclass
class PathBounds(ClipBounds):
    fill_type: str
    verbs: Any


@dataclass
class Paint:
    """original is an index into a map of indexes to the original paint struct"""

    color: RGBA
    blend_mode: str
    original: int


@dataclass
class Node:
    pass


@dataclass
class Sequence(Node):
    """Sequence is virtual operation to aid compilation to EasterEgg"""

    left: Node
    right: Node


@dataclass
class Command(Node):
    clip: ClipBounds | None
    m44: M44


@dataclass
class Save(Command):
    """Save saves current clip and m44 on a stack. Matching call to restore,
    discards all changes to clip and m44, restoring the state back to when save
    was called"""

    commands: list[Command] | Node


@dataclass
class SaveLayer(Command):
    commands: list[Command] | Node
    bounds: Rect
    paint: Paint


@dataclass
class Draw(Command):
    paint: Paint | None


@dataclass
class DrawPaint(Draw):
    """Draws paint in clip bounds"""

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
    image: str
    src: Rect
    dst: Rect


class Parser:
    ptr: int
    sk_commands: list[dict[str, Any]]
    clip_stack: list[ClipBounds | None]
    m44_stack: list[M44]

    def __init__(self, sk_commands):
        self.sk_commands = sk_commands
        self.clip_stack = [None]
        self.m44_stack = [
            ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        ]
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

    def parse_commands(self) -> list[Command]:
        res = list[Command]()

        while self.dont_stop():
            print(self.peek())
            match (sk_command := self.peek())['command']:
                case 'DrawPaint':
                    self.advance()
                    res.append(DrawPaint(self.clip_stack[-1], self.m44_stack[-1], None))

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
                            None,
                            Rect(*rect),
                            Radii(left, top, right, bottom),
                        )
                    )

                case 'DrawRect':
                    self.advance()
                    rect = sk_command['co']
                    res.append(DrawRect(self.clip_stack[-1], self.m44_stack[-1], None, Rect(*rect)))

                case 'DrawImageRect':
                    self.advance()
                    image = sk_command['image']['data']
                    src = sk_command['src']
                    dst = sk_command['dst']
                    paint = sk_command['paint']

                    res.append(
                        DrawImageRect(
                            self.clip_stack[-1], self.m44_stack[-1], None, image, src, dst
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
                    res.append(Save(self.clip_stack[-1], self.m44_stack[-1], things))
                case 'SaveLayer':
                    self.advance()
                    self.clip_stack.append(self.clip_stack[-1])
                    self.m44_stack.append(self.m44_stack[-1])
                    things = self.parse_commands()
                    self.advance()
                    self.clip_stack.pop()
                    self.m44_stack.pop()

                    bounds = sk_command['bounds']
                    paint = sk_command['paint']

                    res.append(
                        SaveLayer(self.clip_stack[-1], self.m44_stack[-1], things, bounds, paint)
                    )

                case 'ClipRect':
                    self.advance()
                    coords = sk_command['coords']
                    rect = Rect(*coords)
                    bounds = RectBounds(sk_command['op'], rect)
                    self.clip_stack[-1] = bounds

                case 'ClipRRect':
                    self.advance()
                    rect, *radii = sk_command['coords']
                    left = radii[0][0]
                    top = radii[0][1]
                    right = radii[1][0]
                    bottom = radii[2][1]
                    self.clip_stack[-1] = RRectBounds(
                        sk_command['op'],
                        Rect(*rect),
                        Radii(left, top, right, bottom),
                    )

                case 'ClipPath':
                    self.advance()
                    op = sk_command['op']
                    fill_type = sk_command['path']['fill_type']
                    verbs = sk_command['path']['verbs']
                    self.clip_stack[-1] = PathBounds(op, fill_type, verbs)

                case 'Concat44':
                    self.advance()
                    m44: M44 = tuple(tuple(i) for i in sk_command['matrix'])  # pyright: ignore
                    self.m44_stack[-1] = matrix_multiply(self.m44_stack[-1], m44)

                case _:
                    raise NotImplementedError(f'Unknown operator {sk_command["command"]}')

        return res


if __name__ == '__main__':
    # commands = [
    #     {'command': 'DrawPaint'},
    #     {'command': 'Save'},
    #     {'command': 'ClipRect', 'op': 'intersect', 'coords': [1250.5, 866, 1263, 1570.1]},
    #     {'command': 'DrawPaint'},
    #     {'command': 'Restore'},
    #     {'command': 'DrawPaint'},
    #     {
    #         'command': 'Concat44',
    #         'matrix': [[1, 0, 0, 0], [0, 1, 0, -760], [0, 0, 1, 0], [0, 0, 0, 1]],
    #     },
    #     {'command': 'DrawPaint'},
    # ]

    filepath = sys.argv[-1]
    with open(filepath, 'rb') as f:
        skp = json.load(f)

    print(Parser(skp['commands']).parse_commands())
