import argparse
import json
from pathlib import Path


def verify_color_filter(colorfilter: dict):
    # large composed color filter:
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_10.json
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_9.json
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Zoom__layer_11.json

    # matrixcolorfilter
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Microsoft_Bing__layer_3.json

    # Not all color filters compose other color filters
    print('gndu', colorfilter)
    assert 'name' in colorfilter
    assert 'data' in colorfilter
    assert 'values' in colorfilter

    match colorfilter['name']:
        case 'SkBlendModeColorFilter':
            # SkColor grey = SkColorSetARGB(255, 136, 136, 136);
            # paint.setColorFilter(SkColorFilters::Blend(grey, SkBlendMode::kSrcIn));

            # TODO ask pavel about this weird color filter
            # TODO dont really understand diff between this and color/blendmode
            assert 'values' in colorfilter
            assert '00_color' in colorfilter['values']  # color
            assert '01_uint' in colorfilter['values']  # blend mode
            # case 'SkComposeColorFilter': Will go into inner_color_filter
            #     00_<colorfilter> -> outer colorfilter
            #     01_<colorfilter> -> inner colorfilter
            # case 'SkMatrixColorFilter': ICF
            #     00_scalarArray -> matrix
            #     01_bool -> is RGBA domain
            #     02_bool -> is clamped
            #
        case 'SkRuntimeColorFilter':
            # 00_int -> stable key (figure this out)
            # 01_string -> the runtime function (exists only if 00_int is 0)
            # 02_bytearray -> funiforms
            # 03_int -> something i dont get

            # I dont understand how this is constructed
            assert '00_int' in colorfilter['values']
            assert '01_string' in colorfilter['values']
            assert '02_byteArray' in colorfilter['values']
            assert '03_int' in colorfilter['values']
        case _:
            raise ValueError(f'Unknown color filter: {colorfilter["name"]}')


# IMPORTANT: If 01_bool is false then all the subsequent indices gets pushed up
#            by 1
# "sampling": {
#     "maxAniso": 0,
#     "useCubic": false,
#     "filter": 1,
#     "mipmap": 2,
#     "cubic.B": 0,
#     "cubic.C": 0
# }

# Complicated image filters:
# https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Google_Search__layer_1.json
# https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Microsoft_Bing__layer_13.json


def verify_image_filter(image_filter: dict):
    # SkMatrixTransformImageFilter:
    # | 00_int -> # of input filters
    # | 01_bool -> # is input null or not
    # | 02_* -> input filter
    # | 03_matrix
    # | 04_sampling
    raise NotImplementedError('image filters')


def verify_inner_image_filter(name, image_filter):
    # SkColorFilterImageFilter
    # | 00_int -> # of input filters
    # | 01_bool -> # is input null or not
    # | 02_<image_filter> -> input image filter
    # | 03_<color_filter> -> color filter (make a new inner color filter verifier)

    # SkBlurImageFilter
    # | 00_int -> # of input filters
    # | 01_bool -> # is input null or not
    # | 02_<image_filter> -> input image filter
    # | 03_scalar -> sigma x
    # | 04_scalar -> sigma y
    # | 05_int -> fLegacyTileMode
    pass


def verify_shader(shader: dict):
    # this function is going to have a very annoying structure
    # I don't want to write this
    assert 'name' in shader
    assert 'data' in shader
    assert 'values' in shader

    match shader['name']:
        case 'SkLocalMatrixShader':
            # applies a matrix to transform the coordinate space of the matrix
            # keys are not static, so we need to wack shit
            print(shader['values'])
            for key, value in shader['values'].items():
                match key:
                    case '00_matrix':
                        # this is the transform matrix
                        pass
                    case _ if key.startswith('01'):
                        inner_shader_name = key.split('_')[1]
                        verify_inner_shader(inner_shader_name, value)
                    case _:
                        raise ValueError(f'Unknown SkLocalMatrixShader key: {key}')
        case _:
            raise ValueError(f'Unknown outer shader: {shader["name"]}')


def verify_inner_shader(name, shader):
    match name:
        case 'SkLinearGradient':
            # "01_SkLinearGradient": {
            #     "00_uint" -> flags
            #     "01_colorArray" -> colors
            #     "02_byteArray" -> colorspace
            #     "03_scalarArray" -> paints
            #     "04_point" -> start
            #     "05_point" -> end
            # }

            # I think we may have to reconstruct the flags from diff, see README.md

            assert '00_uint' in shader
            assert '01_colorArray' in shader
            assert '02_byteArray' in shader
            assert '03_scalarArray' in shader
            assert '04_point' in shader
            assert '05_point' in shader
        case _:
            raise ValueError(f'Unknown shader {name}')


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
            raise ValueError('I dont think I should be here')


def verify_blend_mode(blend_mode: str):
    # SoftLight: https://nightly.cs.washington.edu/reports/easteregg/1753066297:verify:0530860e/Yandex__layer_26__VERIFY.html
    #            https://nightly.cs.washington.edu/reports/easteregg/1753066297:verify:0530860e/Zen_News__layer_30__VERIFY.html
    # Overlay: https://nightly.cs.washington.edu/reports/easteregg/1753066297:verify:0530860e/Mail_ru__layer_18__VERIFY.html
    #          https://nightly.cs.washington.edu/reports/easteregg/1753066297:verify:0530860e/Mail_ru__layer_15__VERIFY.html
    # Plus: https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/GitHub__layer_2__VERIFY.html
    assert blend_mode in {'Src', 'DstIn', 'Multiply', 'Overlay', 'SoftLight', 'Plus'}, (
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
            case 'strokeMiter':
                # https://api.skia.org/classSkPaint.html#a2e767abfeb7795ed251a08b5ed85033f
                pass
            case 'dither':
                # distribute colors, if the current display does not support
                # current pixel to be drawn
                # Chrome seems to enable this for gradients
                pass
            case 'shader':
                verify_shader(value)
            case 'colorfilter':
                # large composed color filter:
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_10.json
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_9.json
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Zoom__layer_11.json

                # matrixcolorfilter
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Microsoft_Bing__layer_3.json
                verify_color_filter(value['name'])
                # match value['name']:
                #     case 'SkBlendModeColorFilter':
                #         # SkColor grey = SkColorSetARGB(255, 136, 136, 136);
                #         # paint.setColorFilter(SkColorFilters::Blend(grey, SkBlendMode::kSrcIn));
                #         # TODO ask pavel about this weird color filter
                #         # TODO dont really understand diff between this and color/blendmode
                #         assert 'values' in value
                #         assert '00_color' in value['values']  # color
                #         assert '01_uint' in value['values']  # blend mode
                #     # case 'SkComposeColorFilter': Will go into inner_color_filter
                #     #     00_<colorfilter> -> outer colorfilter
                #     #     01_<colorfilter> -> inner colorfilter
                #     # case 'SkMatrixColorFilter': ICF
                #     #     00_scalarArray -> matrix
                #     #     01_bool -> is RGBA domain
                #     #     02_bool -> is clamped
                #     #

                #     case _:
                #         raise ValueError(f'Unknown color filter: {value["name"]}')
            case 'antiAlias':
                pass
            case 'dashing':
                # dashing only corresponds to SkDashPathEffect
                # other path effects seem to be serialized under pathEffect
                assert 'intervals' in value
                assert 'phase' in value
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
