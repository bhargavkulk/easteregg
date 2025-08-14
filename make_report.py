import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, final

import yattag

from compiler import compile_to_lambda_skia
from eegg2png import egg_to_png
from egglog_runner import run_cmd, run_egglog
from printegg import Formatter, parse_sexp
from skp2eegg import compile_json_skp, get_reset_warnings
from verify import verify_skp

EGG = 'egg'
JSON = 'json'


@final
class SaneHtmlDiff(difflib.HtmlDiff):
    _legend = ''


def rewrite_name(string: str) -> str:
    suite, name = string.split('__', 1)
    name = name.replace('_', ' ')
    suite = suite.replace('_', ' ')
    return suite + ' | ' + name


def code_page(string: str, doc: yattag.SimpleDoc):
    doc, tag, text = doc.tagtext()
    with tag('pre', style='white-space: pre; overflow: auto;'):
        text(string)


def collate_data(args):
    assert isinstance(args.output, Path)
    EGG_FOLDER: Path = args.output / EGG
    JSON_FOLDER: Path = args.output / JSON

    benchmarks = []
    improved = 0
    unchanged = 0
    regressed = 0
    failed = 0
    formatter = Formatter()
    files: list[Path] = list(args.bench.glob('*.json'))
    for i, benchmark in enumerate(files):
        print(f'[{i + 1}/{len(files)}] running ' + str(benchmark))
        bench_name = benchmark.stem
        data: dict[str, Any] = dict()
        data['name'] = bench_name
        suite, _ = bench_name.split('__', 1)
        data['website'] = suite.replace('_', '-').lower()

        with benchmark.open('rb') as f:
            skp = json.load(f)

        _ = shutil.copy(benchmark, JSON_FOLDER / benchmark.name)
        data['json'] = str(JSON_FOLDER / benchmark.name).replace('report', '.')

        # 0. Verify
        try:
            verify_skp(skp)
        except:
            tb = traceback.format_exc()
            err_file = args.output / (bench_name + '__VERIFY.html')
            with err_file.open('w') as f:
                f.write(page_template(lambda d: code_page(tb, d)).getvalue())
            data['verify_error'] = str(err_file).replace('report', '.')

        # 1. Compile to Egg
        egg = None
        try:
            # egg = compile_json_skp(skp)
            lambda_skia_expr = compile_to_lambda_skia(skp['commands'])
            egg = lambda_skia_expr.sexp()
        except Exception:
            tb = traceback.format_exc()
            err_file = args.output / (bench_name + '__NOOPT_ERR.html')
            with err_file.open('w') as f:
                f.write(page_template(lambda d: code_page(tb, d)).getvalue())
            data['compile_error'] = str(err_file).replace('report', '.')
            data['state'] = 0
            benchmarks.append(data)
            failed += 1
            continue

        assert egg is not None

        # Check if number of save layers is same

        expected_count = 0
        for command in skp['commands']:
            if command['command'] == 'SaveLayer':
                expected_count += 1
        actual_count = egg.count('SaveLayer')

        print(f'{bench_name}: {expected_count} -- {actual_count}')
        if expected_count != actual_count:
            data['compile_error'] = f'{expected_count} ≠ {actual_count}'
            data['state'] = 99
            benchmarks.append(data)
            failed += 1
            continue

        # Collect Warnings

        warnings = get_reset_warnings()

        egg_file: Path = args.output / (bench_name + '__NOOPT.html')
        warning_file: Path = args.output / (bench_name + '__WARN.txt')
        egglog_file: Path = EGG_FOLDER / (bench_name + '.egg')

        with egg_file.open('w') as f:
            f.write(page_template(lambda d: code_page(egg, d)).getvalue())

        with egglog_file.open('w') as f:
            f.write('(let test ' + egg + ')')

        if len(warnings) != 0:
            with warning_file.open('w') as f:
                f.write('\n'.join(warnings) + '\n')
            data['warn_file'] = str(warning_file).replace('report', '.')

        fmt_egg_file = args.output / (bench_name + '__NOOPT_FMT.html')
        fmt_egg = None
        with fmt_egg_file.open('w') as f:
            # formatter.fmt_layer(parse_sexp(egg))
            fmt_egg = 'NOT YET DONT'  # formatter.buffer.getvalue()
            # formatter.clear()
            f.write(page_template(lambda d: code_page(str(fmt_egg), d)).getvalue())

        data['egg_file'] = str(egg_file).replace('report', '.')
        data['fmt_egg_file'] = str(fmt_egg_file).replace('report', '.')

        # 2. Optimize
        opt_file = args.output / (bench_name + '__OPT.html')
        opt_fmt_file = args.output / (bench_name + '__OPT_FMT.html')
        opt_err_file = args.output / (bench_name + '__OPT_ERR.txt')
        egg_warn_file = args.output / (bench_name + '__EWARN.txt')
        #    run egglog
        ret_code, opt, stderr = run_egglog(egglog_file)

        fmt_opt = None

        if ret_code == 0:
            with opt_file.open('w') as f:
                f.write(page_template(lambda d: code_page(opt, d)).getvalue())

            with opt_fmt_file.open('w') as f:
                # formatter.fmt_layer(parse_sexp(opt))
                fmt_opt = 'NOTE YET DONE'
                # formatter.clear()
                f.write(page_template(lambda d: code_page(str(fmt_opt), d)).getvalue())

            with egg_warn_file.open('w') as f:
                f.write(stderr)
        else:
            with opt_err_file.open('w') as f:
                f.write(stderr)
            data['opt_err_file'] = str(opt_err_file).replace('report', '.')
            data['state'] = 1
            benchmarks.append(data)
            failed += 1
            continue

        assert fmt_opt is not None
        data['opt_file'] = str(opt_file).replace('report', '.')
        data['opt_fmt_file'] = str(opt_fmt_file).replace('report', '.')
        data['egg_warn_file'] = str(egg_warn_file).replace('report', '.')

        # 3. Collect Stats, file names
        #    Count SaveLayers before and after
        before = egg.count('SaveLayer')
        after = opt.count('SaveLayer')

        data['counts'] = [before, after]

        if before == after:
            data['change'] = 'yellow'
            unchanged += 1
        elif before < after:
            data['change'] = 'red'
            regressed += 1
        elif before > after:
            data['change'] = 'green'
            improved += 1

        data['state'] = 2

        diff = SaneHtmlDiff().make_file(
            fmt_egg.splitlines(), fmt_opt.splitlines(), fromdesc='NoOpt', todesc='Opt'
        )

        google_fonts_link = '<link href="https://fonts.googleapis.com/css2?family=Inconsolata:wght@200..900&display=swap" rel="stylesheet">'

        custom_css = "<style>pre, code, .diff { font-family: 'Inconsolata', monospace; }</style>"

        injection = google_fonts_link + '\n' + custom_css + '\n'

        diff = diff.replace('</head>', injection + '</head>')

        diff_file = args.output / (bench_name + '__DIFF.html')
        with diff_file.open('w', encoding='utf-8') as f:
            f.write(diff)

        data['diff_file'] = str(diff_file).replace('report', '.')

        # Make PNG files
        # - Make pre opt
        pre_opt = args.output / (bench_name + '__PRE.png')
        res1 = egg_to_png(skp, egg, pre_opt)

        # - Make post opt
        post_opt = args.output / (bench_name + '__POST.png')
        res2 = egg_to_png(skp, opt, post_opt)

        if res1 is None:
            data['pre_png'] = str(pre_opt).replace('report', '.')
        else:
            pre_error = args.output / (bench_name + '__PRE_ERROR.txt')
            with pre_error.open('w', encoding='utf-8') as f:
                f.write(res1)
            data['pre_error'] = str(pre_error).replace('report', '.')

        if res2 is None:
            data['post_png'] = str(post_opt).replace('report', '.')
        else:
            post_error = args.output / (bench_name + '__POST_ERROR.txt')
            with post_error.open('w', encoding='utf-8') as f:
                f.write(res2)
            data['post_error'] = str(post_error).replace('report', '.')

        if (res1 is None) and (res2 is None):
            image_diff = args.output / (bench_name + '__IMG_DIFF.png')
            ret, stdout, stdin = run_cmd(f'compare {pre_opt} {post_opt} {image_diff}'.split())
            data['image_diff'] = str(image_diff).replace('report', '.')

        # 4. Save Stats
        benchmarks.append(data)

    # 5. Sort Report
    benchmarks = sorted(benchmarks, key=lambda d: [p.lower() for p in d['name'].split('__', 1)])

    benchmarks = {
        'benchmarks': benchmarks,
        'num_benchmarks': len(benchmarks),
        'improved': improved,
        'unchanged': unchanged,
        'regressed': regressed,
        'failed': failed,
    }

    # 6. Make Report
    with (args.output / 'report.json').open('w') as f:
        json.dump(benchmarks, f)

    return benchmarks


def report_table(benchmarks, doc: yattag.SimpleDoc):
    doc, tag, text = doc.tagtext()
    num_benchmarks = benchmarks['num_benchmarks']
    improved = benchmarks['improved']
    unchanged = benchmarks['unchanged']
    regressed = benchmarks['regressed']
    failed = benchmarks['failed']

    with tag('h1'):
        text('EasterEgg Report')

    if os.path.isdir('.git'):
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True
        ).strip()
        with tag('a', href=f'https://github.com/bhargavkulk/easteregg/tree/{commit}'):
            text(commit[:8])
        text(f' on ')
        with tag('a', href=f'https://github.com/bhargavkulk/easteregg/tree/{branch}'):
            text(branch)

    with tag('p'):
        text('No. of websites ')
        with tag('span', klass='green'):
            text('Improved')
        text(f': {improved} / {num_benchmarks}')
        doc.stag('br')

        text('No. of websites ')
        with tag('span', klass='yellow'):
            text('Unchanged')
        text(f': {unchanged} / {num_benchmarks}')
        doc.stag('br')

        text('No. of websites ')
        with tag('span', klass='red'):
            text('Regressed')
        text(f': {regressed} / {num_benchmarks}')
        doc.stag('br')

        text('No. of websites ')
        with tag('span'):
            text('Failed')
        text(f': {failed} / {num_benchmarks}')

    with tag('p'):
        with tag('label'):
            with tag(
                'input',
                type='checkbox',
                onchange="toggleHidden('cw', this)",
                style='margin-right: 8px',
            ):
                text('Show Compiler Warnings')
        doc.stag('br')
        with tag('label'):
            with tag(
                'input',
                type='checkbox',
                onchange="toggleHidden('ew', this)",
                style='margin-right: 8px',
            ):
                text('Show Egglog Warnings')

    with tag('table', style='white-space: nowrap;'):
        with tag('tr', klass='gray'):
            with tag('th'):
                text('Benchmark')
            with tag('th'):
                text('JSON')
            with tag('th'):
                text('SkiaChrome')
            with tag('th', colspan=2):
                text('Before')
            with tag('th', colspan=2):
                text('After')
            with tag('th'):
                text('Diff')
            with tag('th'):
                text('#SaveLayers')
            with tag('th'):
                text('PNG')
            with tag('th', klass='cw hidden'):
                text('CW')
            with tag('th', klass='ew hidden'):
                text('EW')
        for benchmark in benchmarks['benchmarks']:
            with tag('tr', klass=benchmark['website']):
                with tag('td', klass='lgray'):
                    text(rewrite_name(benchmark['name']))

                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['json']):
                        text('»')

                if 'verify_error' in benchmark:
                    with tag('td', klass='ctr'):
                        with tag('a', href=benchmark['verify_error']):
                            text('!')
                else:
                    with tag('td', klass='void'):
                        text('')

                if benchmark['state'] == 0:
                    # compile failed
                    with tag('td', klass='ctr', colspan=2):
                        with tag('a', href=benchmark['compile_error']):
                            text('!')
                    with tag('td', colspan=5, klass='void'):
                        text('')
                    with tag('td', klass='void cw hidden'):
                        text('')
                    with tag('td', klass='void ew hidden'):
                        text('')
                    continue
                elif benchmark['state'] == 99:
                    with tag('td', klass='ctr', colspan=2):
                        text(benchmark['compile_error'])
                    with tag('td', colspan=5, klass='void'):
                        text('')
                    with tag('td', klass='void cw hidden'):
                        text('')
                    with tag('td', klass='void ew hidden'):
                        text('')
                    continue

                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['egg_file']):
                        text('»')
                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['fmt_egg_file']):
                        text('»')

                if benchmark['state'] == 1:
                    # egglog failed
                    with tag('td', klass='ctr', colspan=2):
                        with tag('a', href=benchmark['opt_err_file']):
                            text('!')
                    with tag('td', colspan=3, klass='void'):
                        text('')
                    with tag('td', klass='void cw hidden'):
                        text('')
                    with tag('td', klass='void ew hidden'):
                        text('')
                    continue

                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['opt_file']):
                        text('»')

                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['opt_fmt_file']):
                        text('»')

                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['diff_file']):
                        text('»')

                with tag('td', klass=f'{benchmark["change"]} ctr'):
                    text(f'{benchmark["counts"][0]} → {benchmark["counts"][1]}')

                with tag('td', klass='ctr'):
                    if 'pre_png' in benchmark.keys():
                        with tag('a', href=benchmark['pre_png']):
                            text('»')
                    else:
                        with tag('a', href=benchmark['pre_error']):
                            text('!')

                    text('|')

                    if 'post_png' in benchmark.keys():
                        with tag('a', href=benchmark['post_png']):
                            text('»')
                    else:
                        with tag('a', href=benchmark['post_error']):
                            text('!')

                    text('|')

                    if 'image_diff' in benchmark.keys():
                        with tag('a', href=benchmark['image_diff']):
                            text('»')
                    else:
                        with tag('a'):
                            text('!')

                if 'warn_file' in benchmark.keys():
                    with tag('td', klass='ctr cw hidden'):
                        with tag('a', href=benchmark['warn_file']):
                            text('»')
                else:
                    with tag('td', klass='cw hidden void'):
                        text('')

                if 'egg_warn_file' in benchmark.keys():
                    with tag('td', klass='ctr ew hidden'):
                        with tag('a', href=benchmark['egg_warn_file']):
                            text('»')
                else:
                    with tag('td', klass='ew hidden void'):
                        text('')

    with tag('script', type='text/javascript'):
        doc.asis("""function toggleHidden(s, c) {
    document.querySelectorAll(`.${s}`).forEach(cell => {
        if (c.checked) {
            cell.classList.remove('hidden');
        } else {
            cell.classList.add('hidden');
        }
    });
}""")


def page_template(content: Callable[[yattag.SimpleDoc], None]):
    doc, tag, text = yattag.Doc().tagtext()

    doc.asis('<!DOCTYPE html>')
    with tag('html'):
        with tag('head'):
            doc.stag('meta', charset='utf-8')
            doc.stag('meta', name='viewport', content='width=device-width, initial-scale=1')
            with tag('title'):
                text('EasterEgg Report')
            doc.stag('link', rel='preconnect', href='https://fonts.googleapis.com')
            doc.stag('link', rel='preconnect', href='https://fonts.gstatic.com', crossorigin='')
            doc.stag(
                'link',
                href='https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap',
                rel='stylesheet',
            )
            doc.stag('link', rel='stylesheet', href='rsrc/style.css')
        with tag('body'):
            content(doc)
    return doc
    #   <style type="text/css">:root{--uchu-light-gray-raw: 95.57% 0.003 286.35;--uchu-light-gray: oklch(var(--uchu-light-gray-raw));--uchu-gray-raw: 84.68% 0.002 197.12;--uchu-gray: oklch(var(--uchu-gray-raw));--uchu-yellow-raw: 90.92% 0.125 92.56;--uchu-yellow: oklch(var(--uchu-yellow-raw));--uchu-red-raw: 62.73% 0.209 12.37;--uchu-red: oklch(var(--uchu-red-raw));--uchu-green-raw: 79.33% 0.179 145.62;--uchu-green: oklch(var(--uchu-green-raw));}body{margin:40px
    # auto;max-width:800px;line-height:1.6;font-size:18px;color:#444;padding:0
    # 10px}h1,h2,h3{line-height:1.2}.ctr{text-align:center;}th{border:1px solid black;padding:0 5px;}td{border:1px solid black;padding:0 5px;}.green{background-color:var(--uchu-green)}.gray{background-color:var(--uchu-gray)}.red{background-color:var(--uchu-red);color:white}.lgray{background-color:var(--uchu-light-gray)}.yellow{background-color:var(--uchu-yellow)}body{font-family:'Public Sans',sans-serif}.hidden{display: none;}.void{background-image:repeating-linear-gradient(45deg, #ccc, #ccc 10px, #fff 10px, #fff 20px);}</style></head>


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # benchmarks
    parser.add_argument('bench', type=Path)
    # resources
    parser.add_argument('rsrc', type=Path)
    # output folder
    parser.add_argument('output', type=Path)

    args = parser.parse_args()

    if args.output.exists():
        print('output folder exists, delete before running script', file=sys.stderr)
        sys.exit(1)

    args.output.mkdir()
    (args.output / EGG).mkdir()
    (args.output / JSON).mkdir()

    benchmarks = collate_data(args)
    report = page_template(lambda d: report_table(benchmarks, d))

    with (args.output / 'index.html').open('w') as f:
        f.write(yattag.indent(report.getvalue()))

    shutil.copytree(args.rsrc, args.output / args.rsrc)
