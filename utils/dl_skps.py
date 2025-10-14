import argparse
import json
import subprocess
import sys
import tomllib
from io import StringIO
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def find_command(json_data, target_command):
    for command in json_data['commands']:
        if command['command'] == target_command:
            return True
    return False


def dump_skp(flag: bool, urlname: str, url: str, path: Path, outputPath: Path):
    if not flag:
        with sync_playwright() as p:
            print(f'[{urlname}] starting up Chrome')
            browser = p.chromium.launch(
                headless=True, args=['--no-sandbox', '--enable-gpu-benchmarking']
            )
            page = browser.new_page()

            if not url.startswith('https://'):
                url = 'https://' + url
                print(f'[{urlname}] opening {url}')
            try:
                page.goto(url, timeout=20000)
            except PlaywrightTimeoutError as e:
                print(f'[{urlname}] timeout loading page: {e}')
                browser.close()
                return

            page.wait_for_timeout(5000)

            try:
                print(f'[{urlname}] dumping skp')
                page.evaluate(f"chrome.gpuBenchmarking.printToSkPicture('{path.absolute()}')")
            except Exception as e:
                print(f'Error executing command for {urlname}: {e}')

            print(f'[{urlname}] skps dumped')
            print(f'[{urlname}] closing browser')
            browser.close()

    try:
        print(f'[{urlname}] serializing skps to JSON')
        for skp_file in path.glob('*.skp'):
            print(skp_file)
            result = subprocess.run(
                ['./../skia/out/debug/skp_parser', str(skp_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                print(f'[ERROR|{urlname}] stderr: {result.stderr.decode()}')
            else:
                buffer = StringIO(result.stdout.decode())
                width = buffer.readline()
                height = buffer.readline()
                json_data = json.loads(buffer.read())
                json_data['dim'] = [int(width), int(height)]
                if find_command(json_data, 'SaveLayer'):
                    print(f'[{urlname}] found "SaveLayer" @ {skp_file.stem}')
                    json_file_name = skp_file.stem + '.json'
                    json_file_path = outputPath / (urlname + '__' + json_file_name)
                    with json_file_path.open('w') as f:
                        json.dump(json_data, f, indent=4)
        print(f'[{urlname}] done')
    except Exception as e:
        print(f'[{urlname}] error running subprocess: {e}')


parser = argparse.ArgumentParser(description='dump and serialize skps to JSON')
parser.add_argument(
    'input_file', help='path to a TOML file of a list of urls to dump and serialize', type=Path
)
parser.add_argument('skp_folder', help='output path to skps', type=Path)
parser.add_argument('json_folder', help='output path to json', type=Path)
args = parser.parse_args()

toml_urls: dict[str, Any] = dict()

try:
    toml_urls = tomllib.load(args.input_file.open('rb'))
except Exception as e:
    print(f"[error] can't parse toml file: {e}")
    exit(1)


def process_urls():
    skip_skp_dump = args.skp_folder.exists()
    print(skip_skp_dump)
    for urlname, url in toml_urls.items():
        output_path: Path = args.skp_folder / urlname
        output_path.mkdir(parents=True, exist_ok=True)
        args.json_folder.mkdir(parents=True, exist_ok=True)

        print(f'[*] processing {urlname}')
        dump_skp(skip_skp_dump, urlname, url, output_path, args.json_folder)


process_urls()
