from typing import Any

from lark import Lark, Transformer

from lambda_skia import (
    Color,
    Difference,
    Draw,
    Empty,
    Full,
    Intersect,
    Layer,
    Oval,
    Paint,
    Rect,
    SaveLayer,
)

grammar = """
layer: "(" "Empty" ")" -> empty
     | "(" "SaveLayer" layer layer paint ")" -> save_layer
     | "(" "Draw" layer geometry paint geometry ")" -> draw

geometry: "(" "Full" ")" -> full
        | "(" "Rect" FLOAT FLOAT FLOAT FLOAT ")" -> rect
        | "(" "Intersect" geometry geometry ")" -> intersect
        | "(" "Difference" geometry geometry ")" -> difference
        | "(" "Oval" FLOAT FLOAT FLOAT FLOAT ")" -> oval

paint: "(" "Paint" fill blend_mode ")" -> paint

fill: "(" "Color" FLOAT FLOAT FLOAT FLOAT ")" -> color

blend_mode: /\([A-Za-z]+\)/

%import common.FLOAT
%import common.WS
%ignore WS
"""


class LambdaSkiaTransformer(Transformer[Any, Layer]):
    def FLOAT(self, node):
        return float(node)

    def blend_mode(self, node):
        return str(node[0])

    def color(self, node):
        return Color(*node)

    def paint(self, node):
        return Paint(*node)

    def full(self, node):
        return Full()

    def rect(self, node):
        return Rect(*node)

    def intersect(self, node):
        return Intersect(*node)

    def difference(self, node):
        return Difference(*node)

    def empty(self, node):
        return Empty()

    def save_layer(self, node):
        return SaveLayer(*node)

    def draw(self, node):
        return Draw(*node)

    def oval(self, node):
        return Oval(*node)


def parse_sexp(sexp_str: str) -> Layer:
    parser = Lark(grammar, start='layer', parser='lalr')
    return LambdaSkiaTransformer().transform(parser.parse(sexp_str))
