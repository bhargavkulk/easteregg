import argparse
import json
from pathlib import Path

import sexpdata as sx

import skia


def draw_commands(commands, output_file):
    """Draws the commands on a skia canvas and saves it as a PNG file."""
    width, height = 800, 600
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)

    for command in commands:
        if command['type'] == 'line':
            start = command['start']
            end = command['end']
            paint = skia.Paint(Color=skia.ColorBLACK, StrokeWidth=2, Style=skia.Paint.kStroke_Style)
            canvas.drawLine(start[0], start[1], end[0], end[1], paint)

    image = surface.makeImageSnapshot()
    image.save(output_file, skia.kPNG)
    print(f'Image saved to {output_file}')


if __name__ == '__main__':
    """cli tool that converts easter egg files into png images
    Input:
        - easter egg file in sexp format
    Output:
        - png file
    """
    parser = argparse.ArgumentParser(description='Convert easter egg files to PNG images.')
    parser.add_argument('input', help='Input easter egg file in sexp format')
    parser.add_argument('output', help='Output PNG file')

    args = parser.parse_args()
    input_file = Path(args.input)
    output_file = Path(args.output)

    # Read input file using sx
    with input_file.open('r') as f:
        data = sx.load(f)

    commands = eegg_to_commands(data)

    draw_commands(commands, output_file)
