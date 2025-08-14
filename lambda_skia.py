from dataclasses import dataclass, fields
from typing import Any, Literal, override, reveal_type

# Layer      l ::= Empty()
#                | SaveLayer(bottom: l, top: l, paint: p)
#                | Draw(bottom: l, shape: g, paint: p, clip: g
#
# Paint      p ::= Paint(fill: f, blend_mode: b)
#
# Fill       f ::= ARGB(float, float, float, float)
#
# Blend Mode b ::= SrcOver
#
# Geometry   g ::= Rect(float, float, float, float)


@dataclass
class Node:
    def sexp(self) -> str:
        class_name = self.__class__.__name__

        try:
            field_values = [getattr(self, field.name) for field in fields(self)]

            processed_values: list[str] = []
            for value in field_values:
                match value:
                    case Node():
                        processed_values.append(value.sexp())
                    case str():
                        processed_values.append(value)
                    case _:
                        processed_values.append(str(value))

            return (
                f'({class_name} {" ".join(processed_values)})'
                if processed_values
                else f'({class_name})'
            )
        except TypeError:
            raise NotImplementedError()


@dataclass
class Color(Node):
    """A solid color defined by alpha, red, green, and blue channel values."""

    a: float
    r: float
    g: float
    b: float

    def pprint(self) -> str:
        return f'Color({int(self.a * 255)}, {int(self.r * 255)}, {int(self.b * 255)}, {int(self.g * 255)})'


def mk_color(argb: list[int]):
    return Color(*[i / 255 for i in argb])


type Fill = Color

type BlendMode = Literal['(SrcOver)']


@dataclass
class Geometry(Node):
    def pprint(self) -> str:
        raise NotImplementedError()


@dataclass
class Full(Geometry):
    """A geometry representing the full clip. Used in conjunction with
    DrawPaint"""

    @override
    def pprint(self) -> str:
        return 'Full()'


@dataclass
class Rectangle(Geometry):
    """A rectangular geometry defined by left, top, right, and bottom
    coordinates."""

    l: float
    t: float
    r: float
    b: float

    @override
    def pprint(self) -> str:
        return f'Rectangle({self.l}, {self.t}, {self.r}, {self.b})'


@dataclass
class Intersect(Geometry):
    """A geometry that represents the intersection of two or more geometries."""

    g1: Geometry
    g2: Geometry

    @override
    def pprint(self) -> str:
        return self.g1.pprint() + ' ∪ ' + self.g2.pprint()


@dataclass
class Difference(Geometry):
    """A geometry that represents the difference of two or more geometries."""

    g1: Geometry
    g2: Geometry

    @override
    def pprint(self) -> str:
        return self.g1.pprint() + ' / ' + self.g2.pprint()


@dataclass
class Paint(Node):
    """Configuration that determines how geometries are filled and blended when
    drawn."""

    fill: Fill
    blend_mode: BlendMode

    def pprint(self) -> str:
        return f'Paint(' + self.fill.pprint() + ', ' + self.blend_mode + ')'


class Layer(Node):
    """A drawing surface that can contain pixels and be composited with other
    layers."""

    def pretty_print(self, indent_level: int = 0) -> list[tuple[int, str]]:
        """Pretty-printing a layer, returns a list of tuples of an int and a
        string. Each element is a line, the string tis content and the integer
        tells us how nested it is"""
        raise NotImplementedError()


@dataclass
class Empty(Layer):
    """A layer that contains no pixels and serves as the base for all drawing
    operations."""

    pass


@dataclass
class SaveLayer(Layer):
    """A layer that composites a top layer onto a bottom layer using the
    specified paint settings."""

    bottom: Layer
    top: Layer
    paint: Paint

    @override
    def pretty_print(self, indent_level: int = 0) -> list[tuple[int, str]]:
        # i, self.bottom
        # i, SaveLayer self.paint
        # i + 1 self.top
        res: list[tuple[int, str]] = []
        if not isinstance(self.bottom, Empty):
            res = self.bottom.pretty_print(indent_level)

        res.append((indent_level, 'SaveLayer ' + self.paint.pprint() + ':'))
        res.extend(self.top.pretty_print(indent_level + 1))
        return res


@dataclass
class Draw(Layer):
    """A layer that renders a geometry onto an existing layer with the given
    paint and clipping region."""

    bottom: Layer
    shape: Geometry
    paint: Paint
    clip: Geometry

    @override
    def pretty_print(self, indent_level: int = 0) -> list[tuple[int, str]]:
        # i, self.bottom
        # i, Draw()
        res: list[tuple[int, str]] = []
        if not isinstance(self.bottom, Empty):
            res = self.bottom.pretty_print(indent_level)

        cmd = 'Draw ' + self.shape.pprint() + ' ' + self.paint.pprint() + ' ' + self.clip.pprint()
        res.append((indent_level, cmd))
        return res


def pretty_print_layer(layer: Layer):
    output = layer.pretty_print()
    for i, line in output:
        print('  ' * i + line)
