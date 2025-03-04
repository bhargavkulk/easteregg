import argparse
import asyncio
import json
import os
import tomllib
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright


def find_command(json_data, target_command):
    for command in json_data['commands']:
        if command['command'] == target_command:
            return True
    return False


async def dump_skp(urlname: str, url: str, path: Path):
    async with async_playwright() as p:
        print(f'[{urlname}] starting up Chrome')
        browser = await p.chromium.launch(
            headless=True, args=['--no-sandbox', '--enable-gpu-benchmarking']
        )
        page = await browser.new_page()

        print(f'[{urlname}] opening {url}')
        await page.goto(url, timeout=60000)
        await asyncio.sleep(5)

        try:
            print(f'[{urlname}] dumping skp')
            await page.evaluate(f"chrome.gpuBenchmarking.printToSkPicture('{path.absolute()}')")
        except Exception as e:
            print(f'Error executing command for {urlname}: {e}')

        print(f'[{urlname}] skps dumped')
        print(f'[{urlname}] closing browser')
        await browser.close()

    try:
        print(f'[{urlname}] serializing skps to JSON')
        for skp_file in path.glob('*.skp'):
            process = await asyncio.create_subprocess_exec(
                './skia/out/debug/skp_parser',
                str(skp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                print(f'[ERROR|{urlname}] stderr: {stderr.decode()}')
            else:
                json_data = json.loads(stdout.decode())
                if find_command(json_data, 'SaveLayer'):
                    print(f'[{urlname}] found "SaveLayer" @ {skp_file.stem}')
                json_file_name = skp_file.stem + '.json'
                json_file_path = path / json_file_name
                with json_file_path.open('w') as f:
                    json.dump(json_data, f, indent=4)
        print(f'[{urlname}] done')
    except Exception as e:
        print(f'[{urlname}] error running subprocess: {e}')


parser = argparse.ArgumentParser(description='dump and serialize skps to JSON')
parser.add_argument(
    'input_file', help='path to a TOML file of a list of urls to dump and serialize', type=Path
)
parser.add_argument('output_folder', help='output path to skps', type=Path)
args = parser.parse_args()

toml_urls: dict[str, Any] = dict()

try:
    toml_urls = tomllib.load(args.input_file.open('rb'))
except Exception as e:
    print(f"[error] can't parse toml file: {e}")


async def process_urls():
    todo = []
    for urlname, url in toml_urls.items():
        output_path: Path = args.output_folder / urlname
        output_path.mkdir(parents=True, exist_ok=True)

        print(f'[*] processing {urlname}')
        todo.append(dump_skp(urlname, url, output_path))

    try:
        await asyncio.gather(*todo)
    except Exception as e:
        print(f'[error] failed dumping skp: {e}')


asyncio.run(process_urls())
