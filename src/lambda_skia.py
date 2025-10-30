from dataclasses import dataclass, fields
from typing import Literal, override


@dataclass
class Node:
    def sexp(self) -> str:
        class_name = self.__class__.__name__

        try:
            field_values = [getattr(self, field.name) for field in fields(self)]

            values: list[str] = []
            for value in field_values:
                match value:
                    case Node():
                        values.append(value.sexp())
                    case str():
                        values.append(value)
                    case bool():
                        values.append('true' if value else 'false')
                    case _:
                        values.append(str(value))

            return f'({class_name} {" ".join(values)})' if values else f'({class_name})'
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


@dataclass
class LinearGradient(Node):
    """Linear gradient shader"""

    is_opaque: bool

    def pprint(self) -> str:
        return 'LinearGradient'


@dataclass
class RadialGradient(Node):
    """Radial gradient shader"""

    is_opaque: bool

    def pprint(self) -> str:
        return 'RadialGradient'


@dataclass
class Transform(Node):
    """4x4 transform matrix"""

    matrix: list[float]

    @override
    def sexp(self) -> str:
        return '(Matrix ' + ' '.join([str(i) for i in self.matrix]) + ')'

    def pprint(self) -> str:
        return 'Mat' + str(self.matrix)


def mk_color(argb: list[int]):
    return Color(*[i / 255 for i in argb])


type Fill = Color | LinearGradient | RadialGradient

type BlendMode = Literal['(SrcOver)']

type Style = Literal['(Solid)', '(Stroke)']

type Filter = Literal['(IdFilter)', '(LumaFilter)']


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
class Rect(Geometry):
    """A rectangular geometry defined by left, top, right, and bottom
    coordinates."""

    l: float
    t: float
    r: float
    b: float

    @override
    def pprint(self) -> str:
        return f'Rect({self.l}, {self.t}, {self.r}, {self.b})'


@dataclass
class TextBlob(Geometry):
    """A textblob geometry defined by text, position, and attributes"""

    x: float
    y: float
    l: float
    t: float
    r: float
    b: float

    @override
    def pprint(self) -> str:
        return f'TextBlob({self.x}, {self.y}, {self.l}, {self.t}, {self.r}, {self.b})'


@dataclass
class ImageRect(Geometry):
    l: float
    t: float
    r: float
    b: float

    @override
    def pprint(self) -> str:
        return f'ImageRect({self.l}, {self.t}, {self.r}, {self.b})'


@dataclass
class RRect(Geometry):
    """A rectangular geometry defined by left, top, right, and bottom
    coordinates, and the radii."""

    l: float
    t: float
    r: float
    b: float

    rl: float
    rt: float
    rr: float
    rb: float

    @override
    def pprint(self) -> str:
        return f'RRect({self.l}, {self.t}, {self.r}, {self.b}, {self.rl}, {self.rt}, {self.rr}, {self.rb})'


@dataclass
class Oval(Geometry):
    """A rectangular geometry defined by left, top, right, and bottom
    coordinates."""

    l: float
    t: float
    r: float
    b: float

    @override
    def pprint(self) -> str:
        return f'Oval({self.l}, {self.t}, {self.r}, {self.b})'


@dataclass
class Path(Geometry):
    """A geometry that defines an arbitrary closed or open path"""

    index: float

    @override
    def pprint(self) -> str:
        return f'Path({self.index})'


@dataclass
class Intersect(Geometry):
    """A geometry that represents the intersection of two or more geometries."""

    g1: Geometry
    g2: Geometry

    @override
    def pprint(self) -> str:
        return self.g1.pprint() + ' ∩ ' + self.g2.pprint()


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
    style: Style
    color_filter: Filter
    index: int  # This points to the skia command that uses this paint in the skp

    def pprint(self) -> str:
        return (
            'Paint('
            + self.fill.pprint()
            + ', '
            + self.blend_mode
            + ', '
            + self.style
            + ', '
            + self.color_filter
            + ')'
        )


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

    @override
    def pretty_print(self, indent_level=0) -> list[tuple[int, str]]:
        return [(indent_level, 'Empty()')]


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
        if isinstance(self.top, Empty):
            res.append((indent_level + 1, 'Empty()'))
        else:
            res.extend(self.top.pretty_print(indent_level + 1))
        return res


@dataclass
class Clip(Layer):
    layer: Layer
    clip: Geometry
    transform: Transform

    @override
    def pretty_print(self, indent_level: int = 0) -> list[tuple[int, str]]:
        # i, Clip with self.clip
        # i + 1, self.layer

        res: list[tuple[int, str]] = []
        res.append((indent_level, 'Clip with ' + self.clip.pprint() + ':'))
        res.append((indent_level + 1, '@ ' + self.transform.pprint()))
        if isinstance(self.layer, Empty):
            res.append((indent_level + 1, 'Empty()'))
        else:
            res.extend(self.layer.pretty_print(indent_level + 1))
        return res


@dataclass
class Draw(Layer):
    """A layer that renders a geometry onto an existing layer with the given
    paint and clipping region."""

    bottom: Layer
    shape: Geometry
    paint: Paint
    clip: Geometry
    transform: Transform

    @override
    def pretty_print(self, indent_level: int = 0) -> list[tuple[int, str]]:
        # i, self.bottom
        # i, Draw()
        res: list[tuple[int, str]] = []
        if not isinstance(self.bottom, Empty):
            res = self.bottom.pretty_print(indent_level)

        res.append((indent_level, 'Draw ' + self.shape.pprint()))
        res.append((indent_level + 1, 'with ' + self.paint.pprint()))
        res.append((indent_level + 1, 'in ' + self.clip.pprint()))
        res.append((indent_level + 1, '@ ' + self.transform.pprint()))
        return res


def pretty_print_layer(layer: Layer) -> str:
    output = layer.pretty_print()
    res = ''
    for i, line in output:
        res += '  ' * i + line + '\n'

    return res
