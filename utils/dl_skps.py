import argparse
import concurrent.futures
import json
import os
import subprocess
import tomllib
from io import StringIO
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def find_command(json_data: dict[str, Any], target_command: str) -> bool:
    return any(
        command.get('command') == target_command for command in json_data.get('commands', [])
    )


def parse_skp_parser_output(output: str) -> dict[str, Any]:
    """Parse skp_parser output format (current JSON or legacy header + JSON)."""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Backward compatibility for older skp_parser output:
        # first line width, second line height, then JSON payload.
        buffer = StringIO(output)
        width = int(buffer.readline().strip())
        height = int(buffer.readline().strip())
        json_data = json.loads(buffer.read())
        json_data['dim'] = [width, height]
        return json_data


def normalize_url(url: str) -> str:
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return f'https://{url}'


def dump_skp_for_url(
    browser: Any, urlname: str, url: str, path: Path, page_timeout_ms: int
) -> None:
    """Dump SKPs for one URL using an existing browser instance."""
    page = browser.new_page()
    normalized_url = normalize_url(url)
    print(f'[{urlname}] opening {normalized_url}')
    try:
        page.goto(normalized_url, timeout=page_timeout_ms)
        page.wait_for_timeout(5000)
        print(f'[{urlname}] dumping skp')
        output_dir = json.dumps(str(path.absolute()))
        page.evaluate(f'chrome.gpuBenchmarking.printToSkPicture({output_dir})')
        print(f'[{urlname}] skps dumped')
    except PlaywrightTimeoutError as exc:
        print(f'[{urlname}] timeout loading page: {exc}')
    except Exception as exc:
        print(f'[ERROR|{urlname}] failed to dump skp: {exc}')
    finally:
        page.close()


def run_skp_parser(
    skp_parser_path: Path, skp_file: Path, parser_timeout_seconds: int
) -> tuple[bool, dict[str, Any] | str]:
    try:
        result = subprocess.run(
            [str(skp_parser_path), str(skp_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=parser_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f'timed out after {parser_timeout_seconds}s'
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    if result.returncode != 0:
        return False, result.stderr.strip() or f'exit code {result.returncode}'

    try:
        return True, parse_skp_parser_output(result.stdout)
    except Exception as exc:  # noqa: BLE001
        return False, f'parse error: {exc}'


def serialize_skps_to_json(
    urlname: str,
    skp_folder: Path,
    output_folder: Path,
    skp_parser_path: Path,
    parse_workers: int,
    parser_timeout_seconds: int,
    force_reserialize: bool,
) -> None:
    print(f'[{urlname}] serializing skps to JSON')
    skp_files = sorted(skp_folder.glob('*.skp'))
    if not skp_files:
        print(f'[{urlname}] no skps found')
        return

    futures: dict[
        concurrent.futures.Future[tuple[bool, dict[str, Any] | str]], tuple[Path, Path]
    ] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=parse_workers) as executor:
        for skp_file in skp_files:
            json_path = output_folder / f'{urlname}__{skp_file.stem}.json'
            if json_path.exists() and not force_reserialize:
                continue
            future = executor.submit(
                run_skp_parser, skp_parser_path, skp_file, parser_timeout_seconds
            )
            futures[future] = (skp_file, json_path)

        if not futures:
            print(f'[{urlname}] all JSON outputs already exist; skipping re-serialization')
            return

        for future in concurrent.futures.as_completed(futures):
            skp_file, json_path = futures[future]
            ok, payload = future.result()
            if not ok:
                print(f'[ERROR|{urlname}] {skp_file.name}: {payload}')
                continue

            json_data = payload
            if not isinstance(json_data, dict):
                print(f'[ERROR|{urlname}] {skp_file.name}: unexpected parser payload')
                continue

            if find_command(json_data, 'SaveLayer'):
                print(f'[{urlname}] found "SaveLayer" @ {skp_file.stem}')
                with json_path.open('w') as file_obj:
                    json.dump(json_data, file_obj, indent=4)

    print(f'[{urlname}] done')


parser = argparse.ArgumentParser(description='dump and serialize skps to JSON')
parser.add_argument(
    'input_file', help='path to a TOML file of a list of urls to dump and serialize', type=Path
)
parser.add_argument('skp_parser', help='path to skp_parser executable', type=Path)
parser.add_argument('skp_folder', help='output path to skps', type=Path)
parser.add_argument('json_folder', help='output path to json', type=Path)
parser.add_argument(
    '--parse-workers',
    type=int,
    default=max(1, min(16, (os.cpu_count() or 1) * 2)),
    help='max parallel workers for skp_parser processes',
)
parser.add_argument(
    '--page-timeout-ms',
    type=int,
    default=20000,
    help='page load timeout in milliseconds',
)
parser.add_argument(
    '--parser-timeout-seconds',
    type=int,
    default=30,
    help='timeout per skp_parser subprocess in seconds',
)
parser.add_argument(
    '--force-reserialize',
    action='store_true',
    help='re-run skp_parser even if target JSON already exists',
)
args = parser.parse_args()
args.skp_parser = args.skp_parser.resolve()

if not args.skp_parser.exists():
    print(f'[error] skp_parser does not exist: {args.skp_parser}')
    exit(1)

toml_urls: dict[str, Any] = dict()

try:
    toml_urls = tomllib.load(args.input_file.open('rb'))
except Exception as e:
    print(f"[error] can't parse toml file: {e}")
    exit(1)


def process_urls():
    args.json_folder.mkdir(parents=True, exist_ok=True)

    urls_to_dump: list[tuple[str, str, Path]] = []
    for urlname, url in toml_urls.items():
        output_path: Path = args.skp_folder / urlname
        output_path.mkdir(parents=True, exist_ok=True)
        skip_skp_dump = any(output_path.glob('*.skp'))
        print(f'[*] processing {urlname}')
        if skip_skp_dump:
            print(f'[{urlname}] existing skps found, skipping dump')
        else:
            urls_to_dump.append((urlname, url, output_path))

    if urls_to_dump:
        with sync_playwright() as playwright:
            print('[*] starting up Chrome')
            browser = playwright.chromium.launch(
                headless=True, args=['--no-sandbox', '--enable-gpu-benchmarking']
            )
            try:
                for urlname, url, output_path in urls_to_dump:
                    dump_skp_for_url(browser, urlname, url, output_path, args.page_timeout_ms)
            finally:
                print('[*] closing browser')
                browser.close()

    for urlname, _url in toml_urls.items():
        output_path = args.skp_folder / urlname
        serialize_skps_to_json(
            urlname=urlname,
            skp_folder=output_path,
            output_folder=args.json_folder,
            skp_parser_path=args.skp_parser,
            parse_workers=args.parse_workers,
            parser_timeout_seconds=args.parser_timeout_seconds,
            force_reserialize=args.force_reserialize,
        )


process_urls()
