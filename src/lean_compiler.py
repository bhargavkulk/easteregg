import argparse
import json
import pathlib

from lambda_skia import layer_to_lean
from skp_compiler import compile_skp_to_lskia

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=pathlib.Path)
    args = parser.parse_args()

    with args.input.open('rb') as f:
        skp = json.load(f)

    layer, _ = compile_skp_to_lskia(skp['commands'])
    print(layer_to_lean(layer))
