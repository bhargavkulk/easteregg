# EasterEgg

Add urls to `urls.toml`, and then run the script as:

    python3 main.py urls.toml skps

All the skps along with the converted JSON files will be in `skps`.

`skp.py` is the skp -> easteregg compiler. Currently just takes in s json file and spits out the equivalent eastergg form to stdout.

# TODO

- [ ] define eastergg in egglog
- [ ] compile python eastergg objects to egglog
- [ ] redo all skiaopt work
- [ ] add the skiaopt test skps to the skps folder
- [ ] write a json->skp compiler
- [ ] measure memory and performance numbers
- [ ] increase number of urls to look at
- [ ] more rewrite rules

# WTF are ImageFilters

[`skia-python` reference](https://kyamagu.github.io/skia-python/reference/skia.ImageFilters.html)

| Skp Filter Name              | skia-python                       |
|------------------------------|-----------------------------------|
| SkMergeImageFilter           | skia.ImageFilters.Merge           |
| SkMatrixTransformImageFilter | skia.ImageFilters.MatrixTransform |
| SkColorFilterImageFilter     | skia.ImageFilters.ColorFilter     |
| SkBlurImageFilter            | skia.ImageFilters.Blur            |
