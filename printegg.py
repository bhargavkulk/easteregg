import argparse
from io import StringIO
from pathlib import Path

import sexpdata as sx


class Formatter:
    def __init__(self):
        self.buffer = StringIO()
        self.indent = 0

    def write_line(self, string):
        self.buffer.write(('  ' * self.indent) + string + '\n')

    def right(self):
        self.indent += 1

    def left(self):
        self.indent -= 1

    def write(self, string):
        self.buffer.write(string)

    def indent_line(self):
        self.buffer.write('  ' * self.indent)

    def newline(self):
        self.buffer.write('\n')

    def close(self):
        self.buffer.close()

    def fmt_layer(self, layer):
        if layer[0] == 'Empty':
            self.write_line('Empty')
        else:
            _, blend_mode, layer, cmd = layer
            self.fmt_layer(layer)
            self.indent_line()
            self.write(f'ᐊ {blend_mode[0]}')
            self.fmt_cmd(cmd)

    def fmt_cmd(self, cmd):
        if cmd[0] == 'Clip':
            if cmd[1][0] == 'ClipFull':
                self.write(' ClipFull')
            elif cmd[1][0] == 'ClipRect':
                self.write(' ClipRect ')
                self.fmt_ltrb(cmd[1][1])
            elif cmd[1][0] == 'ClipRRect':
                self.write(' ClipRRect ')
                self.fmt_ltrb(cmd[1][1])
                self.write(' ')
                self.fmt_ltrb(cmd[1][2])
            else:
                raise ValueError(f'Unknown Clip: {cmd[1][0]}')
        transform = cmd[-1]
        _, *matrix, shape = transform

        self.write(', Mat [...]')
        self.newline()

        self.right()
        self.fmt_shape(shape)
        self.left()

    def fmt_shape(self, shape):
        self.indent_line()
        if shape[0] == 'Rect':
            _, ltrb, paint, _ = shape
            self.write('Rect ')
            self.fmt_ltrb(ltrb)
            self.write(' ')
            self.fmt_paint(paint)
            self.newline()
        elif shape[0] == 'RRect':
            _, ltrb, radii, paint, _ = shape
            self.write('RRect ')
            self.fmt_ltrb(ltrb)
            self.write(' ')
            self.fmt_ltrb(radii)
            self.write(' ')
            self.fmt_paint(paint)
            self.newline()
        elif shape[0] == 'Path':
            _, paint, _ = shape
            self.write('Path ')
            self.fmt_paint(paint)
            self.newline()
        elif shape[0] == 'ImageRect':
            _, src, dst, paint, _ = shape
            self.write('Rect ')
            self.fmt_ltrb(src)
            self.write(' ')
            self.fmt_ltrb(dst)
            self.write(' ')
            self.fmt_paint(paint)
            self.newline()
        elif shape[0] == 'Oval':
            _, ltrb, paint, _ = shape
            self.write('Oval ')
            self.fmt_ltrb(ltrb)
            self.write(' ')
            self.fmt_paint(paint)
            self.newline()
        elif shape[0] == 'TextBlob':
            _, x, y, ltrb, paint, _ = shape
            self.write('TextBlob ')
            self.write(f'{x} {y} ')
            self.fmt_ltrb(ltrb)
            self.write(' ')
            self.fmt_paint(paint)
            self.newline()
        elif shape[0] == 'SaveLayer':
            _, paint, layer, _ = shape
            self.write('SaveLayer ')
            self.fmt_paint(paint)
            self.newline()
            self.fmt_layer(layer)
        elif shape[0] == 'Fill':
            _, paint, _ = shape
            self.write('Fill ')
            self.fmt_paint(paint)
            self.newline()
        else:
            raise ValueError(f'Unknown shape: {shape[0]}')

    def fmt_ltrb(self, ltrb):
        self.write(f'[{ltrb[1]} {ltrb[2]} {ltrb[3]} {ltrb[4]}]')

    def fmt_paint(self, paint):
        if paint[0] == 'Color':
            self.write(f'Color({paint[1]} {paint[2]} {paint[3]} {paint[4]})')
        else:
            self.write(paint[0])

    def clear(self):
        self.buffer = StringIO()
        self.indent = 0


def normalize(sexp):
    if isinstance(sexp, sx.Symbol):
        return sexp.value()
    elif isinstance(sexp, list):
        return [normalize(item) for item in sexp]
    else:
        return sexp


def parse_sexp(string):
    return normalize(sx.loads(string))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('r') as f:
        eegg = normalize(sx.load(f))

    formatter = Formatter()
    formatter.fmt_layer(eegg)

    if args.output:
        with args.output.open('w') as f:
            f.write(formatter.buffer.getvalue())
    else:
        print(formatter.buffer.getvalue())
