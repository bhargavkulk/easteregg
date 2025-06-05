import argparse
import json
from pathlib import Path

import skia

stream = skia.Data.MakeFromFileName('example.skp')
print(stream)
picture = skia.Picture.MakeFromData(stream)
