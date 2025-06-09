import argparse
from pathlib import Path

import numpy as np

import skia

# Registry for draw functions
draw_registry = []

WIDTH, HEIGHT = 512, 512


def draw_func(func):
    draw_registry.append(func)
    return func


def make_m44(r1, r2, r3, r4):
    return skia.M44.Rows(skia.V4(*r1), skia.V4(*r2), skia.V4(*r3), skia.V4(*r4))

def draw(json, canvas):



def to_png(draw, json, dir):
    filename = f'unit__{draw.__name__}.png'
    path = dir / filename
    surface = skia.Surface(WIDTH, HEIGHT)
    with surface as canvas:
        draw(json, canvas)

    image = surface.makeImageSnapshot()
    image.save(str(path), skia.kPNG)


def to_skp(draw, json, dir):
    filename = f'unit__{draw.__name__}.skp'
    path = dir / filename

    recorder = skia.PictureRecorder()
    canvas = recorder.beginRecording(skia.Rect.MakeWH(WIDTH, HEIGHT))
    draw(json, canvas)
    picture = recorder.finishRecordingAsPicture()
    skdata = picture.serialize()

    with open(path, 'wb') as f:
        f.write(bytes(skdata))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Render Skia draw functions to PNG and SKP.')
    parser.add_argument('png_dir', type=Path, help='Directory to save PNG files.')
    parser.add_argument('skp_dir', type=Path, help='Directory to save SKP files.')
    args = parser.parse_args()

    args.png_dir.mkdir(parents=True, exist_ok=True)
    args.skp_dir.mkdir(parents=True, exist_ok=True)

    # Render all registered draw functions
    for draw in draw_registry:
        to_png(draw, args.png_dir)
        to_skp(draw, args.skp_dir)
