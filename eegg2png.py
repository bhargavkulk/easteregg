import argparse
import json
import traceback
from pathlib import Path

import sexpdata as sx

import skia


def normalize(sexp):
    if isinstance(sexp, sx.Symbol):
        return sexp.value()
    elif isinstance(sexp, list):
        return [normalize(item) for item in sexp]
    else:
        return sexp


class Painter:
    def __init__(self, width: int = 512, height: int = 512):
        self.width = width
        self.height = height
        self.surface = skia.Surface(width, height)

    def to_png(self, output: Path):
        image = self.surface.makeImageSnapshot()
        if not image:
            raise RuntimeError('Failed to create image snapshot')
        # image.save takes a string not Path objext, so convert to string
        image.save(str(output), skia.kPNG)

    def paint_layer(self, layer):
        if layer[0] == 'Empty':
            pass
        else:
            for thing in layer:
                print(thing)
            _, _, layer, cmd = layer
            self.paint_layer(layer)
            self.paint_cmd(cmd)

    def paint_cmd(self, cmd):
        if cmd[0] == 'Clip':
            if cmd[1][0] == 'ClipFull':
                ...
            elif cmd[1][0] == 'ClipRect':
                # do ClipRect
                ...
            elif cmd[1][0] == 'ClipRRect':
                # do ClipRRect
                ...
            else:
                raise ValueError(f'Unknown Clip: {cmd[1][0]}')
        transform = cmd[-1]
        _, *matrix, shape = transform

        # do concat Matrix here
        self.paint_shape(shape)

    def make_paint(self, paint):
        if paint[0] == 'Color':
            paint = skia.Paint(Color=skia.ColorSetARGB(paint[1], paint[2], paint[3], paint[4]))

            if paint[5] == 'SrcOver':
                paint.setBlendMode(skia.BlendMode.kSrcOver)
            elif paint[5] == 'Src':
                paint.setBlendMode(skia.BlendMode.kSrc)
            elif paint[5] == 'DstIn':
                paint.setBlendMode(skia.BlendMode.kDstIn)
            elif paint[5] == 'Multiply':
                paint.setBlendMode(skia.BlendMode.kMultiply)
            else:
                raise NotImplementedError(f'blendmode {paint[5]}')
        else:
            raise NotImplementedError(f'Unknown paint type: {paint[0]}')

    def paint_shape(self, shape):
        if shape[0] == 'Rect':
            _, ltrb, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
        elif shape[0] == 'RRect':
            _, ltrb, radii, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
            # draw RRect
        elif shape[0] == 'Path':
            _, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
            # draw Path (How?)
        elif shape[0] == 'ImageRect':
            _, src, dst, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
        elif shape[0] == 'Oval':
            _, ltrb, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
        elif shape[0] == 'TextBlob':
            _, x, y, ltrb, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
        elif shape[0] == 'SaveLayer':
            _, paint, layer = shape
            paint = self.make_paint(paint)
            with self.surface as canvas:
                canvas.saveLayer(None, paint)
                self.paint_layer(layer)
                canvas.restore()
            # Restore
            raise NotImplementedError(shape[0])
        elif shape[0] == 'Fill':
            _, paint = shape
            self.make_paint(paint)
            raise NotImplementedError(shape[0])
        else:
            raise ValueError(f'Unknown shape: {shape[0]}')


def egg_to_png(json, egg, output_file):
    """Writes egg file to png at 'output_file'"""
    try:
        w, h = json.get('dim', (512, 512))
        painter = Painter(w, h)
        data = sx.loads(egg)
        commands = normalize(data)
        painter.paint_layer(commands)
        painter.to_png(output_file)
        return None
    except Exception:
        tb = traceback.format_exc()
        return str(tb)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert easter egg files to PNG images.')
    parser.add_argument('input', help='Input easter egg file in sexp format')
    parser.add_argument('output', help='Output PNG file')

    args = parser.parse_args()
    input_file = Path(args.input)
    output_file = Path(args.output)

    # Read input file using sx
    with input_file.open('r') as f:
        data = sx.load(f)

    commands = normalize(data)
    painter = Painter()
    painter.paint_layer(commands)
    painter.to_png(output_file)
