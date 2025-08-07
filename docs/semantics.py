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

MaskFilter = Callable[[Coord], """something???? dunno what"""]

Paint = tuple[Fill, Stroke, BlendMode, MaskFilter]


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
    clip: Geometry

    def __call__(self, coord: Coord) -> Color:
        (fill, stroke, blend_mode) = self.paint

        # unsure what thre result of a mask filter is
        # or how it gets composited onto the color buffer

        def color_buffer(coord: Coord) -> Color:
            extent = stroke(self.geometry)
            if coord in extent:
                color = fill(coord)
                return color
            else:
                return Color(0, 0, 0, 0)

        # mask filtering should go here

        def clipped_buffer(coord: Coord) -> Color:
            if coord in clip:
                return color_buffer(coord)
            else:
                return Color(0, 0, 0, 0)

        # image filters should go here

        return blend_mode(self.below(coord), clipped_buffer(coord))
