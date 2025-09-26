import traceback
from pathlib import Path
from typing import Any

import skia  # pyrefly: ignore

# https://github.com/bhargavkulk/easteregg/blob/9646d8c2fcc2e90c01b5a74745f574a5bf9de58a/eegg2png.py
import lambda_skia as ast

BLEND_MODES = {
    '(SrcOver)': skia.BlendMode.kSrcOver,
    '(DstIn)': skia.BlendMode.kDstIn,
    '(SoftLight)': skia.BlendMode.kSoftLight,
    '(Src)': skia.BlendMode.kSrc,
}


def extract_tile_mode(flags: int) -> int:
    return (flags >> 8) & 0xF


class Renderer:
    def __init__(
        self, skp_json: dict[str, Any], width: int = 512, height: int = 512, png: bool = True
    ):
        """Initialize renderer with SKP data and canvas dimensions."""
        self.width = width
        self.height = height
        self.png = png
        if png:
            self.surface = skia.Surface(width, height)
            self.canvas = self.surface.getCanvas()
            self.skp_json = skp_json
        else:
            self.recorder = skia.PictureRecorder()
            self.canvas = self.recorder.beginRecording(width, height)

    def to_png(self, output: Path):
        assert self.png
        image = self.surface.makeImageSnapshot()
        if not image:
            raise RuntimeError('Failed to create image snapshot')
        # image.save takes a string not Path objext, so convert to string
        image.save(str(output), skia.kPNG)

    def to_skp(self, output: Path):
        assert not self.png
        picture = self.recorder.finishRecordingAsPicture()
        with output.open('wb') as f:
            f.write(picture.serialize().bytes())

    def mk_paint(self, paint: ast.Paint):
        skpaint = skia.Paint()

        # Add Fill
        match paint.fill:
            case ast.Color(a, r, g, b):
                skpaint.setColor4f(skia.Color4f(r, g, b, a))
            case ast.LinearGradient():
                # fetch the gradient from the paint from the skp directly
                json_shader: dict = self.skp_json['commands'][paint.index]['paint']['shader']

                # get the matrix
                flat_matrix = [float(x) for row in json_shader['values']['00_matrix'] for x in row]
                assert len(flat_matrix) == 9
                matrix = skia.Matrix()
                matrix.set9(flat_matrix)

                # get the parts of the shader
                json_lgshader: dict = json_shader['values']['01_SkLinearGradient']
                flags: int = json_lgshader['00_uint']
                tile_mode = skia.TileMode(extract_tile_mode(flags))

                # COLORS ALWAYS ARGB, but skia.Color4f needs RGBA order
                colors: list[int] = []
                for json_color in json_lgshader['01_colorArray']:
                    colors.append(
                        int(
                            skia.Color4f(json_color[1], json_color[2], json_color[3], json_color[0])
                        )
                    )

                if '02_byteArray' in json_lgshader:  # color space data
                    # we dont use this
                    if '03_scalarArray' in json_lgshader:  # points
                        points: list[float] = json_lgshader['03_scalarArray']
                        start = skia.Point(*json_lgshader['04_point'])
                        end = skia.Point(*json_lgshader['05_point'])

                        skpaint.setShader(
                            skia.GradientShader.MakeLinear(
                                [start, end],
                                colors,
                                [float(point) for point in points],
                                tile_mode,
                                flags,
                                matrix,
                            )
                        )

                    else:
                        start = skia.Point(*json_lgshader['03_point'])
                        end = skia.Point(*json_lgshader['04_point'])

                        skpaint.setShader(
                            skia.GradientShader.MakeLinear(
                                [start, end],
                                colors,
                                None,
                                tile_mode,
                                flags,
                                matrix,
                            )
                        )
                else:
                    if '02_scalarArray' in json_lgshader:  # points
                        points: list[float] = json_lgshader['02_scalarArray']
                        start = skia.Point(*json_lgshader['03_point'])
                        end = skia.Point(*json_lgshader['04_point'])
                        skpaint.setShader(
                            skia.GradientShader.MakeLinear(
                                [start, end],
                                colors,
                                [float(point) for point in points],
                                tile_mode,
                                flags,
                                matrix,
                            )
                        )
                    else:
                        start = skia.Point(*json_lgshader['02_point'])
                        end = skia.Point(*json_lgshader['03_point'])
                        skpaint.setShader(
                            skia.GradientShader.MakeLinear(
                                [start, end],
                                colors,
                                None,
                                tile_mode,
                                flags,
                                matrix,
                            )
                        )
                pass
            case _:
                raise NotImplementedError(f'{type(paint.fill)} fill is not supported')

        # Add Blend Mode
        if paint.blend_mode in BLEND_MODES.keys():
            skpaint.setBlendMode(BLEND_MODES[paint.blend_mode])
        else:
            raise NotImplementedError(f'{paint.blend_mode[1:-1]} blend mode is not supported')

        return skpaint

    def render_layer(self, layer: ast.Layer) -> None:
        """Recursively render a layer tree to the canvas."""
        match layer:
            case ast.SaveLayer(bottom, top, paint):
                self.render_layer(bottom)
                skpaint = self.mk_paint(paint)
                self.canvas.saveLayer(paint=skpaint)
                self.render_layer(top)
                self.canvas.restore()
            case ast.Draw(bottom, shape, paint, clip, transform):
                self.render_layer(bottom)
                self.canvas.save()
                self.transform(transform)
                self.new_clip_geometry(clip)
                skpaint = self.mk_paint(paint)
                self.render_geometry(shape, skpaint)
                self.canvas.restore()
            case _:
                # Empty()
                pass

    def render_geometry(self, geometry: ast.Geometry, skpaint) -> None:
        """Execute drawing commands for the given geometry."""
        match geometry:
            case ast.Full():
                self.canvas.drawPaint(skpaint)
            case ast.Rect(left, top, right, bottom):
                self.canvas.drawRect(skia.Rect.MakeLTRB(left, top, right, bottom), skpaint)
            case ast.RRect(l, t, r, b, rl, rt, rr, rb):
                rect = skia.Rect.MakeLTRB(l, t, r, b)
                rrect = skia.RRect.MakeEmpty()
                rrect.setNinePatch(rect, rl, rt, rr, rb)
                self.canvas.drawRRect(rrect, skpaint)
            case ast.Oval(left, top, right, bottom):
                self.canvas.drawOval(skia.Rect.MakeLTRB(left, top, right, bottom), skpaint)
            case ast.Intersect(_, _) | ast.Difference(_, _):
                raise ValueError(
                    f'Geometry operator {type(geometry)} not allowed as a draw geometry'
                )
            case ast.TextBlob(x, y, l, t, r, b):
                # Ignore for now
                pass
            case ast.ImageRect(l, t, r, b):
                # Ignore for now
                pass
            case _:
                raise NotImplementedError(f'Geometry type {type(geometry)} not implemented')

    def geometry_to_path(self, geometry: ast.Geometry) -> skia.Path:
        canvas_bounds = skia.Rect.MakeWH(self.width, self.height)

        match geometry:
            case ast.Full():
                path = skia.Path()
                path.addRect(canvas_bounds)
                return path
            case ast.Rect(l, t, r, b):
                path = skia.Path()
                path.addRect(l, t, r, b)
                return path
            case ast.RRect(l, t, r, b, rl, rt, rr, rb):
                path = skia.Path()
                rect = skia.Rect.MakeLTRB(l, t, r, b)
                rrect = skia.RRect.MakeEmpty()
                rrect.setNinePatch(rect, rl, rt, rr, rb)
                path.addRRect(rrect)
                return path
            case ast.Intersect(left, right):
                if isinstance(left, ast.Full):
                    return self.geometry_to_path(right)
                if isinstance(right, ast.Full):
                    return self.geometry_to_path(left)

                left_path = self.geometry_to_path(left)
                right_path = self.geometry_to_path(right)

                return skia.Op(left_path, right_path, skia.PathOp.kIntersect_PathOp)
            case ast.Difference(left, right):
                if isinstance(right, ast.Full):
                    return skia.Path()

                left_path = self.geometry_to_path(left)
                right_path = self.geometry_to_path(right)

                return skia.Op(left_path, right_path, skia.PathOp.kDifference_PathOp)

    def new_clip_geometry(self, geometry: ast.Geometry) -> None:
        clip_path = self.geometry_to_path(geometry)
        self.canvas.clipPath(clip_path)

    def clip_geometry(self, geometry: ast.Geometry) -> None:
        """Apply clipping operations to the canvas for the given geometry."""

        def apply_clip_geometry(geometry: ast.Geometry, clip_op) -> None:
            match geometry:
                case ast.Rect(left, top, right, bottom):
                    self.canvas.clipRect(skia.Rect.MakeLTRB(left, top, right, bottom), clip_op)
                case ast.RRect(l, t, r, b, rl, rt, rr, rb):
                    rect = skia.Rect.MakeLTRB(l, t, r, b)
                    rrect = skia.RRect.MakeEmpty()
                    rrect.setNinePatch(rect, rl, rt, rr, rb)
                    self.canvas.clipRRect(rrect, clip_op)
                case _:
                    raise ValueError(
                        f'Invalid geometry type {type(geometry)} for apply_clip_geometry'
                    )

        match geometry:
            case ast.Full():
                pass
            case ast.Intersect(left_geo, right_geo):
                self.clip_geometry(left_geo)
                apply_clip_geometry(right_geo, skia.ClipOp.kIntersect)
            case ast.Difference(left_geo, right_geo):
                self.clip_geometry(left_geo)
                apply_clip_geometry(right_geo, skia.ClipOp.kDifference)
            case _:
                raise ValueError(f'Invalid geometry type {type(geometry)} for clipping')

    def transform(self, transform: ast.Transform):
        m44 = transform.matrix
        rows = [
            skia.V4(*m44[0:4]),
            skia.V4(*m44[4:8]),
            skia.V4(*m44[8:12]),
            skia.V4(*m44[12:16]),
        ]
        skia_m44 = skia.M44.Rows(*rows)
        self.canvas.setMatrix(skia_m44)


def egg_to_png(json, layer, output_file):
    """Writes egg file to png at 'output_file'"""
    try:
        w, h = json.get('dim', (512, 512))
        renderer = Renderer(json, w, h)
        renderer.render_layer(layer)
        renderer.to_png(output_file)
        return
    except Exception:
        tb = traceback.format_exc()
        return str(tb)


def egg_to_skp(json, layer, output_file):
    """Writes egg file to skp at 'output_file'"""
    try:
        w, h = json.get('dim', (512, 512))
        renderer = Renderer(json, w, h, png=False)
        renderer.render_layer(layer)
        renderer.to_skp(output_file)
        return
    except Exception:
        tb = traceback.format_exc()
        return str(tb)
