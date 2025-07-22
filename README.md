# EasterEgg

Add urls to `urls.toml`, and then run the script as:

    python3 main.py urls.toml skps

All the skps along with the converted JSON files will be in `skps`.

`skp.py` is the skp -> easteregg compiler. Currently just takes in s json file and spits out the equivalent eastergg form to stdout.

# TODO

- [X] define eastergg in egglog
- [X] compile python eastergg objects to egglog
- [X] redo all skiaopt work
- [X] add the skiaopt test skps to the skps folder
- [X] write a json->skp compiler
- [ ] measure memory and performance numbers
- [X] increase number of urls to look at
- [ ] more rewrite rules
- [ ] define the core set of skia that webpages use
- [ ] connect that core set of skia directyl to the functions used in the skia api
- [  ] denotational semantics of skia

# Skia Important Links

- How does skia serialize stuff? [DebugCanvas.h](https://github.com/google/skia/blob/main/tools/debugger/DrawCommand.cpp)
- [Shader Serialization](https://github.com/google/skia/blob/main/src/shaders/gradients/SkGradientBaseShader.cpp#L76)

# Worries

- Other browsers and applications may use different subsets of skia language.

  Possible answer: So what? Chrome is the biggest user (Maybe Android?????)
  Google makes it somewhat easy to dump skps from android

- do filters affect performance

# Compiling Paints
Very complicated shit.

Paint is 2 things, how the shape is filled, and how the boundaries are drawn.

The shape can be filled in 2 ways.

1. Just a straight up color
2. Or a shader. This generates per pixel colors to fill. It replaces a solid color with complex patterns/gradients etc.

# WTF are ImageFilters

[`skia-python` reference](https://kyamagu.github.io/skia-python/reference/skia.ImageFilters.html)

| Skp Filter Name              | skia-python                       |
|------------------------------|-----------------------------------|
| SkMergeImageFilter           | skia.ImageFilters.Merge           |
| SkMatrixTransformImageFilter | skia.ImageFilters.MatrixTransform |
| SkColorFilterImageFilter     | skia.ImageFilters.ColorFilter     |
| SkBlurImageFilter            | skia.ImageFilters.Blur            |
 xb
# SaveLayers to look at

Seeing lot of non opaque srcovers savelayers
- bilibili layer 56
- duckduckgo 3
- duckduckgo 6
- ebay 0, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18
- fandom layer 2
- instagram layer 0



## Amazon Layer 5
```
ᐊ SrcOver ClipRect [40.0 1281.0 1240.0 1501.0], Mat [...]
  SaveLayer Color(128 0 0 0)
  Empty
  ᐊ SrcOver ClipRRect [41.0 1337.0 84.0 1435.0] [0.0 0.0 2.0 2.0], Mat [...]
    RRect [40.0 1336.0 85.0 1436.0] [0.0 0.0 3.0 3.0] ColorFilter
  ᐊ SrcOver ClipRect [40.0 1326.0 95.0 1446.0], Mat [...]
    RRect [40.0 1336.0 85.0 1436.0] [0.0 0.0 3.0 3.0] Color(255 255 255 255)
  ᐊ SrcOver ClipRect [40.0 1326.0 95.0 1446.0], Mat [...]
    Rect [14.0 0.0 27.0 22.0] [54.0 1375.0 67.0 1397.0] Color(255 0 0 0)
```

## Non SrcOver inside Opaque SaveLayer
Baidu Layer 0
```
ᐊ SrcOver ClipRect [483.0 272.0 745.0 296.0], Mat [...]
  SaveLayer Color(255 0 0 0)
  Empty
  ᐊ SrcOver ClipRect [483.0 272.0 745.0 296.0], Mat [...]
    Rect [483.0 272.0 745.0 296.0] Color(255 0 0 0)
  ᐊ DstIn ClipRect [483.0 272.0 745.0 296.0], Mat [...]
    SaveLayer Color(255 0 0 0)
    Empty
    ᐊ SrcOver ClipRect [483.0 272.0 745.0 296.0], Mat [...]
      TextBlob 482.547 290.0 [-10.6328 -16.0938 262.934 5.19531] Color(255 0 0 0)
```

## Shader inside DstIn inside OSaveLayer
Bilibili Layer 5
```
ᐊ SrcOver ClipFull, Mat [...]
  SaveLayer Color(255 0 0 0)
  Empty
  ᐊ SrcOver ClipRect [60.0 -133.0 630.0 658.0], Mat [...]
    Rect [60.0 -133.0 630.0 657.0] Color(255 147 143 124)
  ᐊ DstIn ClipFull, Mat [...]
    SaveLayer Color(255 0 0 0)
    Empty
    ᐊ SrcOver ClipFull, Mat [...]
      Rect [60.0 -133.0 630.0 657.0] Shader
```

How does dstin work with shader?

Seeing lot of opaque save layer -> dsting savelayer

## Another dstin in savelayer
bilibili 57

```
ᐊ SrcOver ClipRect [0.0 0.0 20.0 21.0], Mat [...]
  SaveLayer Color(255 0 0 0)
  Empty
  ᐊ SrcOver ClipRect [2.0 1.0 18.0 21.0], Mat [...]
    Path Color(255 255 255 255)
  ᐊ SrcOver ClipRect [2.0 1.0 18.0 21.0], Mat [...]
    Path Color(255 255 255 255)
  ᐊ DstIn ClipRect [0.0 0.0 20.0 21.0], Mat [...]
    SaveLayer Color(255 0 0 0)
    Empty
    ᐊ SrcOver ClipRect [2.0 1.0 18.0 21.0], Mat [...]
      Path Color(255 255 255 255)
```

All of these are opaque dstin savelayers. Cant get this to work in skia fiddle

## Ditto
canvaas 0

```
ᐊ SrcOver ClipRect [0.0 0.0 108.0 41.0], Mat [...]
  SaveLayer Color(255 0 0 0)
  Empty
  ᐊ SrcOver ClipRect [-10.0 -10.0 110.0 110.0], Mat [...]
    Rect [0.0 0.0 100.0 100.0] Shader
  ᐊ DstIn ClipRect [0.0 0.0 108.0 41.0], Mat [...]
    SaveLayer Color(255 0 0 0)
    Empty
    ᐊ SrcOver ClipRect [-10.0 -10.0 110.0 110.0], Mat [...]
      SaveLayer ColorFilter
      Empty
      ᐊ SrcOver ClipRect [-10.0 -10.0 110.0 110.0], Mat [...]
        Path Color(255 255 255 255)
```

## Shaders inside opaque savelayer

```
ᐊ SrcOver ClipRect [0.0 3239.0 1280.0 3599.0], Mat [...]
  SaveLayer Color(179 0 0 0)
  Empty
  ᐊ SrcOver ClipRect [0.0 3239.0 1280.0 3599.0], Mat [...]
    SaveLayer Color(255 0 0 0)
    Empty
    ᐊ Other ClipRect [0.0 3239.0 1280.0 3599.0], Mat [...]
      Rect [0.0 0.0 1833.0 1833.0] Shader
```

## dont still understand image filters

need to recreate in skia fiddle

ebay 2, this file has multiple examples of the above savelayre, (shader inside osavelayer)
and lot of image filter ones too.

```
ᐊ SrcOver ClipRect [0.0 0.0 1280.0 360.0], Mat [...]
  SaveLayer Color(179 0 0 0)
  Empty
  ᐊ SrcOver ClipRect [0.0 0.0 1280.0 360.0], Mat [...]
    SaveLayer Color(255 0 0 0)
    Empty
    ᐊ Other ClipRect [0.0 0.0 1280.0 360.0], Mat [...]
      Rect [0.0 0.0 1833.0 1833.0] Shader

Look below!
ᐊ SrcOver ClipRect [113.0 99.0 187.0 117.0], Mat [...]
  SaveLayer ImageFilter
  Empty
  ᐊ SrcOver ClipRect [113.0 99.0 187.0 117.0], Mat [...]
    TextBlob 113.0 113.0 [-2.086 -13.5659 82.5579 3.96207] Color(255 0 0 0)
```

## Tons of ImageFIlters
- github 10, 15, 16, 2, 7, 9
- globo 0, 30, 33
- google 1

# Ask Pavel

Not sure what is happening here:

```json
{
            "command": "DrawRRect",
            "visible": true,
            "coords": [
                [
                    40,
                    1336,
                    85,
                    1436
                ],
                [
                    0,
                    0
                ],
                [
                    3,
                    3
                ],
                [
                    3,
                    3
                ],
                [
                    0,
                    0
                ]
            ],
            "paint": {
                "antiAlias": true,
                "blur": {
                    "sigma": 1.5,
                    "style": "normal"
                },
                "colorfilter": {
                    "name": "SkBlendModeColorFilter",
                    "data": "data/41",
                    "values": {
                        "00_color": [
                            1,
                            0.533333,
                            0.533333,
                            0.533333
                        ],
                        "01_uint": 5
                    }
                }
            }
        },
```

# Weird Things
- https://nightly.cs.washington.edu/reports/easteregg/1752880257:verify:0530860e/json/Pinterest__layer_106.json


# Reading List
- Reincarnate / CAD IR semantics
