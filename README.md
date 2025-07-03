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

# Compiling Paints
Very complicated shit.

Paint is 2 things, how the shape is filled, and how the boundaries are drawn.

The shape can be filled in 2 ways.

1. Just a straight up color
2. Or a shader. This generates per pixel colors to fill. It replaces a solid color with complex patterns/gradients etc.

can y

# WTF are ImageFilters

[`skia-python` reference](https://kyamagu.github.io/skia-python/reference/skia.ImageFilters.html)

| Skp Filter Name              | skia-python                       |
|------------------------------|-----------------------------------|
| SkMergeImageFilter           | skia.ImageFilters.Merge           |
| SkMatrixTransformImageFilter | skia.ImageFilters.MatrixTransform |
| SkColorFilterImageFilter     | skia.ImageFilters.ColorFilter     |
| SkBlurImageFilter            | skia.ImageFilters.Blur            |
