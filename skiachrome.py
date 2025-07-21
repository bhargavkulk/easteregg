import argparse
import json
from pathlib import Path


def verify_shader(shader: dict):
    # this function is going to have a very annoying structure
    # I don't want to write this
    raise NotImplementedError('Shader')


def verify_path(path: dict):
    assert path['fillType'] in {'evenOdd', 'winding', 'inverseWinding'}, (
        f'Unknown fill type: {path["fillType"]}'
    )
    assert 'verbs' in path
    for verb in path['verbs']:
        if isinstance(verb, dict):
            # this loop should only run once
            for key in verb.keys():
                assert key in {'move', 'cubic', 'line', 'conic', 'quad'}, f'Unknown verb: {key}'
        elif isinstance(verb, str):
            assert verb == 'close', f'Unknown verb {verb}'
        else:
            ValueError('I dont think I should be here')


def verify_blend_mode(blend_mode: str):
    assert blend_mode in {'Src', 'DstIn', 'Multiply', 'Overlay'}, (
        f'Unknown blend mode: {blend_mode}'
    )


def verify_paint(paint: dict):
    for key, value in paint.items():
        match key:
            case 'color':
                pass
            case 'blendMode':
                verify_blend_mode(value)
            case 'blur':
                # use this to make shadows, do a difference clip, to just draw the borders

                # SkPaint blurPaint;
                # paint.setMaskFilter(SkMaskFilter::MakeBlur(
                #     kNormal_SkBlurStyle,
                #     5.0f,  // sigma
                #     false  // respect CTM
                # ));

                # Types of blur filters:
                # kNormal_SkBlurStyle -> 'normal'
                # kSolid_SkBlurStyle
                # kOuter_SkBlurStyle
                # kInner_SkBlurStyle

                assert 'sigma' in value
                assert 'style' in value
                assert value['style'] in {'normal'}, f'Unknown blur style: {value["style"]}'
            case 'style':
                # fill -> draw inside, DEFAULT
                # stroke -> draw border
                # stroke and fill -> draw border and inside
                assert value in {'stroke'}, f'Unknown draw style: {value}'
            case 'strokeWidth':
                # just a number
                # does nothing if style is fill
                pass
            case 'cap':
                # setStrokeCap https://api.skia.org/classSkPaint.html#a68e82b3dfce8a3c35413795461794ba6
                assert value in {'round'}, f'Unknown stroke cap: {value}'
            case 'strokeJoin':
                assert value in {'round'}, f'Unknown stroke join: {value}'
            case 'dither':
                # distribute colors, if the current display does not support
                # current pixel to be drawn
                # Chrome seems to enable this for gradients
                pass
            case 'shader':
                # "01_SkLinearGradient": {
                #     "00_uint" -> flags
                #     "01_colorArray" -> colors
                #     "02_byteArray" -> colorspace
                #     "03_scalarArray" -> paints
                #     "04_point" -> start
                #     "05_point" -> end
                # }
                verify_shader(value)
            case 'colorfilter':
                match value['name']:
                    case 'SkBlendModeColorFilter':
                        # SkColor grey = SkColorSetARGB(255, 136, 136, 136);
                        # paint.setColorFilter(SkColorFilters::Blend(grey, SkBlendMode::kSrcIn));
                        # TODO ask pavel about this weird color filter
                        # TODO dont really understand diff between this and color/blendmode
                        assert 'values' in value
                        assert '00_color' in value['values']  # color
                        assert '01_uint' in value['values']  # blend mode
                    case _:
                        raise ValueError(f'Unknown color filter: {value["name"]}')
            case 'antiAlias':
                pass
            case _:
                raise ValueError(f'Unknown paint attribute: {key}')


def verify_command(command):
    match command['command']:
        # draw commands must have paints
        case 'DrawPaint':
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawRect' | 'DrawRRect':
            assert 'coords' in command  # location
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawPath':
            assert 'path' in command
            verify_path(command['path'])
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawTextBlob':
            assert 'x' in command  # location
            assert 'y' in command
            assert 'runs' in command  # text data
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawImageRect':
            assert 'image' in command  # src image
            assert 'src' in command  # crop size of the image
            assert 'dst' in command  # dst coords to be mapped to
            assert 'sampling' in command  # TODO: figure this out
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawDRRect':
            assert 'outer' in command  # outer shape
            assert 'inner' in command  # inner shape
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawOval':
            assert 'coords' in command
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'Save' | 'Restore':
            # save and restore has no attributes
            pass
        case 'SaveLayer':
            # canvas->saveLayer(Optional[bounds], Optional[paint])
            # bounds may not be in savelayer
            # bounds are a suggestion, so they mean nothing.
            # clip is more meaningful

            # paint may not be in savelayer
            # defaults to black opaque srcover
            if 'paint' in command:
                verify_paint(command['paint'])
        case 'Concat44':
            # concat44 has only 1 possible attribute
            assert 'matrix' in command
        case 'ClipRect':
            assert 'coords' in command
            assert 'op' in command
            assert command['op'] in {'intersect', 'difference'}, command['op']
        case 'ClipRRect':
            assert 'coords' in command  # ltrb and radii
            assert 'op' in command
            assert command['op'] in {'intersect', 'difference'}, command['op']
        case 'ClipPath':
            assert 'path' in command
            verify_path(command['path'])
            assert command['op'] in {'intersect', 'difference'}, command['op']
        case _:
            raise ValueError(f'Unknown command: {command["command"]}')


def verify_skp(commands):
    for i, command in enumerate(commands['commands']):
        try:
            verify_command(command)
        except Exception as e:
            raise ValueError(f'Error at {i}: {command["command"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    verify_skp(skp)
