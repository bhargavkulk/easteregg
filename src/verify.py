import argparse
import json
from pathlib import Path


def verify_color_filter(colorfilter: dict):
    # large composed color filter:
    #
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_10.json
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_9.json
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Zoom__layer_11.json

    # matrixcolorfilter
    # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Microsoft_Bing__layer_3.json

    # Not all color filters compose other color filters
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

        case 'SkRuntimeColorFilter':
            # 00_int -> stable key (figure this out)
            # 01_string -> the runtime function (exists only if 00_int is 0)
            # 02_bytearray -> funiforms
            # 03_int -> something i dont get
            # Constructed from SkRuntimeEffect::makeColorFilter
            # the run time language is the SkSL (Skia Shader Language)
            assert '00_int' in colorfilter['values']
            assert '01_string' in colorfilter['values']
            assert '02_byteArray' in colorfilter['values']
            assert '03_int' in colorfilter['values']
        case _:
            raise ValueError(f'Unknown color filter: {colorfilter["name"]}')


# inner_color_filter
# case 'SkComposeColorFilter': Will go into inner_color_filter
#     00_<colorfilter> -> outer colorfilter
#     01_<colorfilter> -> inner colorfilter
# case 'SkMatrixColorFilter': ICF
#     00_scalarArray -> matrix
#     01_bool -> is RGBA domain
#     02_bool -> is clamped


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
    # assert False, 'searching for shader'
    assert 'name' in shader
    assert 'data' in shader
    assert 'values' in shader

    match shader['name']:
        case 'SkLocalMatrixShader':
            # applies a matrix to transform the coordinate space of the matrix
            # keys are not static, so we need to wack shit
            for key, value in shader['values'].items():
                match key:
                    case '00_matrix':
                        # this is the transform matrix
                        pass
                    case _ if key.startswith('01'):
                        inner_shader_name: str = key.split('_')[1]
                        verify_inner_shader(inner_shader_name, value)
                    case _:
                        raise ValueError(f'Unknown SkLocalMatrixShader key: {key}')
        case _:
            raise ValueError(f'Unknown outer shader: {shader["name"]}')


def verify_inner_shader(name, shader):
    match name:
        case 'SkLinearGradient':
            assert '00_uint' in shader  # flags
            assert '01_colorArray' in shader  # colors

            if '02_byteArray' in shader:  # color space data
                if '03_scalarArray' in shader:  # points
                    assert '04_point' in shader  # start
                    assert '05_point' in shader  # end
                else:
                    assert '03_point' in shader  # start
                    assert '04_point' in shader  # end
            else:
                if '02_scalarArray' in shader:  # points
                    assert '03_point' in shader  # start
                    assert '04_point' in shader  # end
                else:
                    assert '02_point' in shader  # start
                    assert '03_point' in shader  # end
        case 'SkRadialGradient':
            assert '00_uint' in shader  # flags
            assert '01_colorArray' in shader  # colors

            if '02_byteArray' in shader:  # color space data
                if '03_scalarArray' in shader:  # points
                    assert '04_point' in shader  # start
                    assert '05_scalar' in shader  # end
                else:
                    assert '03_point' in shader  # start
                    assert '04_scalar' in shader  # end
            else:
                if '02_scalarArray' in shader:  # points
                    assert '03_point' in shader  # start
                    assert '04_scalar' in shader  # end
                else:
                    assert '02_point' in shader  # start
                    assert '03_scalar' in shader  # end
        case 'SkPictureShader':
            # https://api.skia.org/classSkPicture.html#a41f14a3d374444c8b7f3615c175aa107
            assert '00_int' in shader  # tile x direction
            assert '01_int' in shader  # tile y direction
            assert '02_rect' in shader  # cull data
            assert '03_int' in shader  # tile mode
            # rest is picture data, not worth specifying
        case 'SkImageShader':
            assert '00_uint' in shader  # tile mode x
            assert '01_uint' in shader  # tile mode y
            assert '02_sampling' in shader  # image sampling shaders
            assert '03_image' in shader  # actual shader
            assert (
                '04_bool' in shader
            )  # raw images https://api.skia.org/classSkImage.html#a807165d5c63608927cd556252e92d4b2
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
                assert isinstance(value, str)
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
                assert isinstance(value, dict)
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
                assert isinstance(value, dict)
                verify_shader(value)
            case 'colorfilter':
                # large composed color filter:
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_10.json
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/GitHub__layer_9.json
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Zoom__layer_11.json

                # matrixcolorfilter
                # https://nightly.cs.washington.edu/reports/easteregg/1753074320:verify:8ab065ff/json/Microsoft_Bing__layer_3.json
                assert isinstance(value, dict)
                verify_color_filter(value)
                # raise NotImplementedError('fixing color filter')
            case 'imagefilter':
                pass  # raise NotImplementedError('imagefilters not supported')
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
        case 'DrawRect':
            assert 'coords' in command  # location
            assert 'paint' in command
            verify_paint(command['paint'])
        case 'DrawRRect':
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
        case 'DrawPoints':
            assert 'mode' in command
            assert command['mode'] in {'lines'}, f'Unknown points mode: {command["mode"]}'
            assert 'points' in command
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
            assert False, 'Searching for Path'
            assert 'path' in command
            verify_path(command['path'])
            assert command['op'] in {'intersect', 'difference'}, command['op']
        case _:
            raise ValueError(f'Unknown command: {command["command"]}')


def verify_skp(commands):
    for i, command in enumerate(commands['commands']):
        try:
            verify_command(command)
        except Exception:
            raise ValueError(f'Error at {i}: {command["command"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    _ = parser.add_argument('input', type=Path)
    _ = parser.add_argument('--output', '-o', type=Path)

    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    verify_skp(skp)
