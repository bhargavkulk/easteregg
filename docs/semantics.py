from dataclasses import dataclass
from typing import Callable


class Real:
    pass


class Int:
    pass


@dataclass
class Coord:
    x: Real
    y: Real


@dataclass
class Color:
    a: int
    r: int
    g: int
    b: int


Geometry = set[Coord]

Stroke = Callable[[set[Coord]], set[Coord]]

Fill = Callable[[Coord], Color]

BlendMode = Callable[[Color, Color], Color]

Paint = tuple[Fill, Stroke, BlendMode]


class Layer:
    def __call__(self, coord: Coord) -> Color:
        raise NotImplementedError('ajshdkajhds')


class Empty(Layer):
    def __call__(self, coord: Coord) -> Color:
        return Color(255, 0, 0, 0)


class Draw(Layer):
    below: Layer
    geometry: Geometry
    paint: Paint

    def __call__(self, coord: Coord) -> Color:
        (fill, stroke, blend_mode) = self.paint

        def buffer(coord: Coord) -> Color:
            extent = stroke(self.geometry)
            if coord in extent:
                color = fill(coord)
                return color
            else:
                return Color(0, 0, 0, 0)

        return blend_mode(self.below(coord), buffer(coord))
