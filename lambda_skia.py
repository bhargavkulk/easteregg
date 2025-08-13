from dataclasses import dataclass, fields
from typing import Any, Literal

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


def mk_color(argb: list[int]):
    return Color(*[i / 255 for i in argb])


type Fill = Color

type BlendMode = Literal['(SrcOver)']


@dataclass
class Geometry(Node):
    pass


@dataclass
class Full(Geometry):
    pass


@dataclass
class Rectangle(Geometry):
    """A rectangular geometry defined by left, top, right, and bottom
    coordinates."""

    l: float
    t: float
    r: float
    b: float


@dataclass
class Intersect(Geometry):
    """A geometry that represents the intersection of two or more geometries."""

    g1: Geometry
    g2: Geometry


@dataclass
class Difference(Geometry):
    """A geometry that represents the difference of two or more geometries."""

    g1: Geometry
    g2: Geometry


@dataclass
class Paint(Node):
    """Configuration that determines how geometries are filled and blended when
    drawn."""

    fill: Fill
    blend_mode: BlendMode


class Layer(Node):
    """A drawing surface that can contain pixels and be composited with other
    layers."""

    pass


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


@dataclass
class Draw(Layer):
    """A layer that renders a geometry onto an existing layer with the given
    paint and clipping region."""

    bottom: Layer
    shape: Geometry
    paint: Paint
    clip: Geometry
