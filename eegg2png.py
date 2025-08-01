import argparse
import json
import traceback
from pathlib import Path

import numpy as np
import sexpdata as sx

import skia


def normalize(sexp):
    if isinstance(sexp, sx.Symbol):
        return sexp.value()
    elif isinstance(sexp, list):
        return [normalize(item) for item in sexp]
    else:
        return sexp


FILTER_MODES = {
    0: skia.FilterMode.kNearest,
    1: skia.FilterMode.kLinear,
}

MIPMAP_MODES = {
    0: skia.MipmapMode.kNone,
    1: skia.MipmapMode.kNearest,
    2: skia.MipmapMode.kLinear,
}


def mk_image_filter(imagefilter):
    name = imagefilter['name']
    values = imagefilter['values']

    if name == 'SkMergeImageFilter':
        input_name = next((k for k in values if k[:2] == '02'), None)
        assert input_name
        input = values[input_name]
        input = mk_image_filter_rec(input_name, input)
        return skia.ImageFilters.Merge([input])


import skia


def mk_path(drawpath_json):
    path_data = drawpath_json['path']
    fill_type = path_data.get('fillType', 'winding')

    path = skia.Path()
    if fill_type == 'winding':
        path.setFillType(skia.PathFillType.kWinding)
    elif fill_type == 'evenOdd':
        path.setFillType(skia.PathFillType.kEvenOdd)
    elif fill_type == 'inverseWinding':
        path.setFillType(skia.PathFillType.kInverseWinding)
    else:
        raise ValueError(f'Unknown fillType: {fill_type}')

    for verb in path_data['verbs']:
        if isinstance(verb, dict):
            if 'move' in verb:
                x, y = verb['move']
                path.moveTo(x, y)
            elif 'cubic' in verb:
                pts = verb['cubic']
                (x1, y1), (x2, y2), (x3, y3) = pts
                path.cubicTo(x1, y1, x2, y2, x3, y3)
            elif 'line' in verb:
                x, y = verb['line']
                path.lineTo(x, y)
            elif 'quad' in verb:
                pts = verb['quad']
                (x1, y1), (x2, y2) = pts
                path.quadTo(x1, y1, x2, y2)
            elif 'conic' in verb:
                pts = verb['conic']
                (x1, y1), (x2, y2), w = pts
                path.conicTo(x1, y1, x2, y2, w)
            else:
                raise ValueError(f'Unknown verb key: {verb}')
        elif isinstance(verb, str):
            if verb == 'close':
                path.close()
            else:
                raise ValueError(f'Unknown verb string: {verb}')
        else:
            raise TypeError(f'Unexpected verb type: {verb}')

    return path


def mk_image_filter_rec(filter_name, filter):
    """If `01_bool` is set then the filter is composing another filter"""

    is_composing = filter['01_bool']
    input_name = next((k for k in filter if k[:2] == '02'), None)
    filter = mk_image_filter_rec(input_name, filter[input_name]) if input_name else None

    if filter_name == '02_SkMatrixTransformImageFilter':
        matrix = filter['03_matrix']
        matrix = skia.Matrix(np.array(matrix), dtype=float32)

        sampling = filter['04_sampling']
        filter_mode = skia.FilterMode(sampling['filter'])  # FILTER_MODES[sampling['filter']]
        mipmap_mode = skia.MipmapMode(sampling['mipmap'])  # MIPMAP_MODES[sampling['mipmap']]
        sampling_option = skia.SamplingOptions(filter_mode, mipmap_mode)

        return skia.ImageFilters.MatrixTransform(matrix, sampling_options, input=filter)
    elif filter_name == '02_SkColorFilterImageFilter':
        # construct the blend_mode color filter
        blend = filter['03_SkBlendModeColorFilter']
        color = skia.ColorSetARGB(*blend['00_color'])
        blend_mode = skia.BlendMode(blend['01_uint'])


def mk_clip_op(clip_op: str):
    if clip_op == 'D':
        return skia.ClipOp.kDifference
    elif clip_op == 'I':
        return skia.ClipOp.kIntersect
    else:
        raise ValueError(f'unknown clipop {clip_op}')


def mk_m44(flat):
    if len(flat) != 16:
        raise ValueError(f'Expected 16 elements, got {len(flat)}')

    rows = [
        skia.V4(*flat[0:4]),
        skia.V4(*flat[4:8]),
        skia.V4(*flat[8:12]),
        skia.V4(*flat[12:16]),
    ]
    return skia.M44.Rows(*rows)


class Painter:
    def __init__(self, commands, width: int = 512, height: int = 512):
        self.width = width
        self.height = height
        self.commands = commands
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
            _, _, layer, cmd = layer
            self.paint_layer(layer)
            self.paint_cmd(cmd)

    def paint_cmd(self, cmd):
        if cmd[0] == 'Clip':
            if cmd[1][0] == 'ClipFull':
                pass
            elif cmd[1][0] == 'ClipRect':
                rect = skia.Rect.MakeLTRB(*(cmd[1][1][1:]))
                op = mk_clip_op(cmd[1][2][0])
                with self.surface as canvas:
                    canvas.clipRect(rect, op)
            elif cmd[1][0] == 'ClipRRect':
                _, ltrb, radii, op = cmd[1]
                op = mk_clip_op(op[0])
                with self.surface as canvas:
                    rect = skia.Rect.MakeLTRB(*ltrb[1:])
                    rrect = skia.RRect.MakeEmpty()
                    rrect.setNinePatch(rect, *radii[1:])
                    canvas.clipRRect(rrect, op)
            else:
                raise valueerror(f'unknown clip: {cmd[1][0]}')
        transform = cmd[-1]
        _, matrix, shape = transform
        matrix = mk_m44(matrix[1:])
        with self.surface as canvas:
            canvas.setMatrix(matrix)
        self.paint_shape(shape)

    def make_paint(self, eegg_paint):
        print(eegg_paint)
        if eegg_paint[0] == 'Color':
            paint = skia.Paint(
                Color=skia.ColorSetARGB(eegg_paint[1], eegg_paint[2], eegg_paint[3], eegg_paint[4])
            )

            if eegg_paint[5][0] == 'SrcOver':
                paint.setBlendMode(skia.BlendMode.kSrcOver)
            elif eegg_paint[5][0] == 'Src':
                paint.setBlendMode(skia.BlendMode.kSrc)
            elif eegg_paint[5][0] == 'DstIn':
                paint.setBlendMode(skia.BlendMode.kDstIn)
            elif eegg_paint[5][0] == 'Multiply':
                paint.setBlendMode(skia.BlendMode.kMultiply)
            else:
                raise NotImplementedError(f'blendmode {eegg_paint[5][0]}')

            return paint
        else:
            raise NotImplementedError(f'Unknown paint type: {eegg_paint[0]}')

    def paint_shape(self, shape):
        if shape[0] == 'Rect':
            _, ltrb, paint, index = shape
            paint = self.make_paint(paint)
            with self.surface as canvas:
                rect = skia.Rect.MakeLTRB(*(ltrb[1:]))
                canvas.drawRect(rect, paint)
        elif shape[0] == 'RRect':
            _, ltrb, radii, paint, index = shape
            paint = self.make_paint(paint)
            with self.surface as canvas:
                rect = skia.Rect.MakeLTRB(*ltrb[1:])
                rrect = skia.RRect.MakeEmpty()
                rrect.setNinePatch(rect, *(radii[1:]))
                canvas.drawRRect(rrect, paint)
        elif shape[0] == 'Path':
            _, paint, index = shape
            paint = self.make_paint(paint)
            path_data = self.commands[index]
            path = mk_path(path_data)
            with self.surface as canvas:
                canvas.drawPath(path, paint)
        elif shape[0] == 'ImageRect':
            _, src, dst, paint, index = shape
            # cant draw images yet
            pass
        elif shape[0] == 'Oval':
            _, ltrb, paint, index = shape
            paint = self.make_paint(paint)
            with self.surface as canvas:
                rect = skia.Rect.MakeLTRB(*(ltrb[1:]))
                canvas.drawOval(rect, paint)
        elif shape[0] == 'TextBlob':
            _, x, y, ltrb, paint, index = shape
            # cant draw text yet
        elif shape[0] == 'SaveLayer':
            _, paint, layer, index = shape
            paint = self.make_paint(paint)
            with self.surface as canvas:
                canvas.saveLayer(bounds=None, paint=paint)
                self.paint_layer(layer)
                canvas.restore()
        elif shape[0] == 'Fill':
            _, paint, index = shape
            paint = self.make_paint(paint)
            with self.surface as canvas:
                canvas.drawPaint(paint)
        else:
            raise ValueError(f'Unknown shape: {shape[0]}')


def egg_to_png(json, egg, output_file):
    """Writes egg file to png at 'output_file'"""
    try:
        w, h = json.get('dim', (512, 512))
        painter = Painter(json['commands'], w, h)
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
