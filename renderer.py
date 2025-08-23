from pathlib import Path
from typing import Any

import skia  # pyrefly: ignore

# https://github.com/bhargavkulk/easteregg/blob/9646d8c2fcc2e90c01b5a74745f574a5bf9de58a/eegg2png.py
import lambda_skia as ast

BLEND_MODES = {
    '(SrcOver)': skia.BlendMode.kSrcOver,
}


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

                # TODO: convert Paint to skia.Paint
                # TODO: determine bounds for saveLayer

                self.render_layer(top)
                self.canvas.restore()

            case ast.Draw(bottom, shape, paint, clip, transform):
                self.render_layer(bottom)

                self.canvas.save()

                # TODO: convert Transform to matrix and set
                # TODO: convert Paint to skia.Paint

                self.clip_geometry(clip)
                self.render_geometry(shape, paint)

                self.canvas.restore()

    def render_geometry(self, geometry: ast.Geometry, paint: ast.Paint) -> None:
        """Execute drawing commands for the given geometry."""
        match geometry:
            case ast.Full():
                # TODO: implement full geometry rendering
                pass
            case ast.Rect(left, top, right, bottom):
                # TODO: implement rect rendering
                pass
            case ast.Intersect(_, _) | ast.Difference(_, _):
                pass
            case _:
                raise NotImplementedError(f'Geometry type {type(geometry)} not implemented')

    def clip_geometry(self, geometry: ast.Geometry) -> None:
        """Apply clipping operations to the canvas for the given geometry."""

        def apply_clip_geometry(geometry: ast.Geometry, clip_op) -> None:
            match geometry:
                case ast.Full():
                    raise ValueError('Full geometry should not appear in apply_clip_geometry')
                case ast.Rect(left, top, right, bottom):
                    # TODO: implement rect clipping with clip_op
                    pass
                case _:
                    raise ValueError(
                        f'Invalid geometry type {type(geometry)} for apply_clip_geometry'
                    )

        match geometry:
            case ast.Full():
                # TODO: implement full clipping
                pass
            case ast.Intersect(left_geo, right_geo):
                self.clip_geometry(left_geo)
                apply_clip_geometry(right_geo, skia.ClipOp.kIntersect)
            case ast.Difference(left_geo, right_geo):
                self.clip_geometry(left_geo)
                apply_clip_geometry(right_geo, skia.ClipOp.kDifference)
            case _:
                raise ValueError(f'Invalid geometry type {type(geometry)} for clipping')
