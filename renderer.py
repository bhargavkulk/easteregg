import traceback
from pathlib import Path
from typing import Any

import skia  # pyrefly: ignore

# https://github.com/bhargavkulk/easteregg/blob/9646d8c2fcc2e90c01b5a74745f574a5bf9de58a/eegg2png.py
import lambda_skia as ast

BLEND_MODES = {
    '(SrcOver)': skia.BlendMode.kSrcOver,
}


def mk_paint(paint: ast.Paint):
    skpaint = skia.Paint()

    # Add Fill
    if isinstance(paint.fill, ast.Color):
        skpaint.setColor4f(skia.Color4f(paint.fill.r, paint.fill.g, paint.fill.g, paint.fill.a))
    else:
        raise NotImplementedError(f'{type(paint.fill)} fill is not supported')

    # Add Blend Mode
    if paint.blend_mode in BLEND_MODES.keys():
        skpaint.setBlendMode(BLEND_MODES[paint.blend_mode])
    else:
        raise NotImplementedError(f'{paint.blend_mode[1:-1]} blend mode is not supported')

    return skpaint


class Renderer:
    def __init__(self, skp_json: dict[str, Any], width: int = 512, height: int = 512):
        """Initialize renderer with SKP data and canvas dimensions."""
        self.surface = skia.Surface(width, height)
        self.canvas = self.surface.getCanvas()
        self.skp_json = skp_json

    def to_png(self, output: Path):
        image = self.surface.makeImageSnapshot()
        if not image:
            raise RuntimeError('Failed to create image snapshot')
        # image.save takes a string not Path objext, so convert to string
        image.save(str(output), skia.kPNG)

    def render_layer(self, layer: ast.Layer) -> None:
        """Recursively render a layer tree to the canvas."""
        match layer:
            case ast.SaveLayer(bottom, top, paint):
                self.render_layer(bottom)
                skpaint = mk_paint(paint)
                self.canvas.saveLayer(paint=skpaint)
                self.render_layer(top)
                self.canvas.restore()
            case ast.Draw(bottom, shape, paint, clip, transform):
                self.render_layer(bottom)
                self.canvas.save()
                self.clip_geometry(clip)
                # TODO: convert Transform to matrix and set
                print('still need to do the damn transform')
                skpaint = mk_paint(paint)
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
                pass
            case ast.Rect(left, top, right, bottom):
                self.canvas.drawRect(skia.Rect.MakeLTRB(left, top, right, bottom), skpaint)
                pass
            case ast.Intersect(_, _) | ast.Difference(_, _):
                raise ValueError(
                    f'Geometry operator {type(geometry)} not allowed as a draw geometry'
                )
            case _:
                raise NotImplementedError(f'Geometry type {type(geometry)} not implemented')

    def clip_geometry(self, geometry: ast.Geometry) -> None:
        """Apply clipping operations to the canvas for the given geometry."""

        def apply_clip_geometry(geometry: ast.Geometry, clip_op) -> None:
            match geometry:
                case ast.Full():
                    raise ValueError('Full geometry should not appear in apply_clip_geometry')
                case ast.Rect(left, top, right, bottom):
                    self.canvas.clipRect(skia.Rect.MakeLTRB(left, top, right, bottom), clip_op)
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


def egg_to_png(json, layer, output_file):
    """Writes egg file to png at 'output_file'"""
    try:
        w, h = json.get('dim', (512, 512))
        renderer = Renderer(w, h)
        renderer.render_layer(layer)
        renderer.to_png(output_file)
        return None
    except Exception:
        tb = traceback.format_exc()
        return str(tb)
