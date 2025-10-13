from typing import Any

from lark import Lark, Transformer

from lambda_skia import (
    Color,
    Difference,
    Draw,
    Empty,
    Full,
    ImageRect,
    Intersect,
    Layer,
    LinearGradient,
    Oval,
    Paint,
    Path,
    Rect,
    RRect,
    SaveLayer,
    TextBlob,
    Transform,
)

grammar = """
layer: "(Empty)" -> empty
     | "(SaveLayer" layer layer paint ")" -> save_layer
     | "(Draw" layer geometry paint geometry matrix ")" -> draw
     | "(Clip" layer geometry ")" -> clip

matrix: "(Matrix" FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT ")" -> matrix

geometry: "(Full)" -> full
        | "(Path" INT ")" -> path
        | "(Rect" FLOAT FLOAT FLOAT FLOAT ")" -> rect
        | "(RRect" FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT ")" -> rrect
        | "(Oval" FLOAT FLOAT FLOAT FLOAT ")" -> oval
        | "(ImageRect" FLOAT FLOAT FLOAT FLOAT ")" -> imagerect
        | "(TextBlob" FLOAT FLOAT FLOAT FLOAT FLOAT FLOAT ")" -> textblob
        | "(Intersect" geometry geometry ")" -> intersect
        | "(Difference" geometry geometry ")" -> difference

paint: "(Paint" fill blend_mode style filter INT ")" -> paint

fill: "(Color" FLOAT FLOAT FLOAT FLOAT ")" -> color
    | "(LinearGradient)" -> linear_gradient

blend_mode: "(" /[A-Za-z]+/ ")"

style: "(" /[A-Za-z]+/ ")"

filter: "(" /[A-Za-z]+/ ")"

FLOAT: /-?\d+\.\d+/

%import common.INT
%import common.WS
%ignore WS
"""


class LambdaSkiaTransformer(Transformer[Any, Layer]):
    def FLOAT(self, node):
        return float(node)

    def INT(self, node):
        return int(node)

    def blend_mode(self, node):
        return '(' + str(node[0]) + ')'

    def style(self, node):
        return '(' + str(node[0]) + ')'

    def filter(self, node):
        return '(' + str(node[0]) + ')'

    def color(self, node):
        return Color(*node)

    def linear_gradient(self, node):
        return LinearGradient()

    def paint(self, node):
        return Paint(*node)

    def full(self, node):
        return Full()

    def rect(self, node):
        return Rect(*node)

    def rrect(self, node):
        return RRect(*node)

    def oval(self, node):
        return Oval(*node)

    def path(self, node):
        return Path(*node)

    def imagerect(self, node):
        return ImageRect(*node)

    def textblob(self, node):
        return TextBlob(*node)

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

    def clip(self, node):
        return Clip(*node)

    def matrix(self, node):
        return Transform(node)


def parse_sexp(sexp_str: str) -> Layer:
    parser = Lark(grammar, start='layer', parser='lalr')
    return LambdaSkiaTransformer().transform(parser.parse(sexp_str))
