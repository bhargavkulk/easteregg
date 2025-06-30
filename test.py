import skia

data = skia.Data.MakeFromFileName('./font')

font = skia.Typeface.MakeFromFile('font')

print(font)
