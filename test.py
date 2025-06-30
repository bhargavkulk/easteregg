import skia

surface = skia.Surface(128, 128)

with surface as canvas:
    rect = skia.Rect(0, 0, 32, 32)
    paint = skia.Paint(Color=skia.ColorBLUE, Style=skia.Paint.kFill_Style)
    canvas.drawRect(rect, paint)

with surface as canvas:
    rect = skia.Rect(32, 32, 64, 64)
    paint = skia.Paint(Color=skia.ColorRED, Style=skia.Paint.kFill_Style)
    canvas.drawRect(rect, paint)

image = surface.makeImageSnapshot()
image.save('output.png', skia.kPNG)
