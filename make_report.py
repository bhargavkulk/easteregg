import argparse
import difflib
import json
import shutil
import sys
from pathlib import Path

import yattag

from egglog_runner import run_egglog
from printegg import Formatter, parse_sexp
from skp2eegg import compile_json_skp

EGG = 'egg'
JSON = 'json'


def index_template(table):
    string = """<!DOCTYPE html><html><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EasterEgg Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
  <style type="text/css">:root{--uchu-gray-raw: 84.68% 0.002 197.12;--uchu-gray: oklch(var(--uchu-gray-raw));--uchu-yellow-raw: 90.92% 0.125 92.56;--uchu-yellow: oklch(var(--uchu-yellow-raw));--uchu-red-raw: 62.73% 0.209 12.37;--uchu-red: oklch(var(--uchu-red-raw));--uchu-green-raw: 79.33% 0.179 145.62;--uchu-green: oklch(var(--uchu-green-raw));}body{margin:40px
auto;max-width:800px;line-height:1.6;font-size:18px;color:#444;padding:0
10px}h1,h2,h3{line-height:1.2}.ctr{text-align:center;}th{border:1px solid black;padding:0 5px;}td{border:1px solid black;padding:0 5px;}.green{background-color:var(--uchu-green)}.gray{background-color:var(--uchu-gray)}.red{background-color:var(--uchu-red)}.yellow{background-color:var(--uchu-yellow)}body{font-family:'Public Sans',sans-serif}</style></head>
  <body><header><h1>EasterEgg Report</h1></header>\n"""
    string += table
    string += '</body></html>'
    return string


def bench_template(inside):
    string = """<!DOCTYPE html><html><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EasterEgg Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
  <style type="text/css">:root{--uchu-gray-raw: 84.68% 0.002 197.12;--uchu-gray: oklch(var(--uchu-gray-raw));--uchu-yellow-raw: 90.92% 0.125 92.56;--uchu-yellow: oklch(var(--uchu-yellow-raw));--uchu-red-raw: 62.73% 0.209 12.37;--uchu-red: oklch(var(--uchu-red-raw));--uchu-green-raw: 79.33% 0.179 145.62;--uchu-green: oklch(var(--uchu-green-raw));}body{margin:40px
auto;max-width:800px;line-height:1.6;font-size:18px;color:#444;padding:0
10px}h1,h2,h3{line-height:1.2}.ctr{text-align:center;}td{padding:0 5px;border:1px solid black;}.green{background-color:var(--uchu-green)}.gray{background-color:var(--uchu-gray)}.red{background-color:var(--uchu-red)}.yellow{background-color:var(--uchu-yellow)}body{font-family:'Public Sans',sans-serif}</style></head>
  <body><pre style="white-space: pre; overflow: auto;">\n"""
    string += inside
    string += '</pre></html>'
    return string


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # benchmarks
    parser.add_argument('bench', type=Path)
    # output folder
    parser.add_argument('output', type=Path)

    args = parser.parse_args()

    if args.output.exists():
        print('output folder exists, delete before running script', file=sys.stderr)
        sys.exit(1)

    args.output.mkdir()
    (args.output / EGG).mkdir()
    (args.output / JSON).mkdir()

    EGG_FOLDER = args.output / EGG
    JSON_FOLDER = args.output / JSON

    benchmarks = []
    formatter = Formatter()

    for benchmark in args.bench.glob('*.json'):
        print('[easteregg] running ' + str(benchmark))
        bench_name = benchmark.stem
        data = dict()
        data['name'] = bench_name

        with benchmark.open('rb') as f:
            skp = json.load(f)

        shutil.copy(benchmark, JSON_FOLDER / benchmark.name)
        data['json'] = str(JSON_FOLDER / benchmark.name).replace('report', '.')

        # 1. Compile to Egg
        egg = None
        try:
            egg = compile_json_skp(skp)
        except Exception as e:
            error_msg = str(e)
            err_file = args.output / (bench_name + '__NOOPT_ERR.html')
            with err_file.open('w') as f:
                f.write(bench_template(error_msg))
            data['compile_error'] = str(err_file).replace('report', '.')
            data['state'] = 0
            continue

        assert egg is not None

        egg_file = args.output / (bench_name + '__NOOPT.html')
        egglog_file = EGG_FOLDER / (bench_name + '.egg')

        with egg_file.open('w') as f:
            f.write(bench_template(egg))

        with egglog_file.open('w') as f:
            f.write('(let test ' + egg + ')')

        fmt_egg_file = args.output / (bench_name + '__NOOPT_FMT.html')
        fmt_egg = None
        with fmt_egg_file.open('w') as f:
            formatter.fmt_layer(parse_sexp(egg))
            fmt_egg = formatter.buffer.getvalue()
            formatter.clear()
            f.write(bench_template(fmt_egg))

        data['egg_file'] = str(egg_file).replace('report', '.')
        data['fmt_egg_file'] = str(fmt_egg_file).replace('report', '.')

        # 2. Optimize
        opt_file = args.output / (bench_name + '__OPT.html')
        opt_fmt_file = args.output / (bench_name + '__OPT_FMT.html')
        opt_err_file = args.output / (bench_name + '__OPT_ERR.html')
        #    run egglog
        ret_code, opt, stderr = run_egglog(egglog_file)

        fmt_opt = None

        if ret_code == 0:
            with opt_file.open('w') as f:
                f.write(bench_template(opt))

            with opt_fmt_file.open('w') as f:
                formatter.fmt_layer(parse_sexp(opt))
                fmt_opt = formatter.buffer.getvalue()
                formatter.clear()
                f.write(bench_template(fmt_opt))
        else:
            with opt_err_file.open('w') as f:
                f.write(bench_template(stderr))
            data['opt_err_file'] = str(opt_err_file).replace('report', '.')
            data['state'] = 1
            continue

        assert fmt_opt is not None
        data['opt_file'] = str(opt_file).replace('report', '.')
        data['opt_fmt_file'] = str(opt_fmt_file).replace('report', '.')

        # 3. Collect Stats, file names
        #    Count SaveLayers before and after
        before = egg.count('SaveLayer')
        after = opt.count('SaveLayer')

        data['counts'] = [before, after]

        if before == after:
            data['change'] = 'yellow'
        elif before < after:
            data['change'] = 'red'
        elif before > after:
            data['change'] = 'green'

        data['state'] = 2

        diff = difflib.HtmlDiff().make_file(
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

        # 4. Save Stats
        benchmarks.append(data)

    # 5. Sort Report
    benchmarks = sorted(benchmarks, key=lambda d: [p.lower() for p in d['name'].split('__', 1)])

    # 6. Make Report
    with (args.output / 'report.json').open('w') as f:
        json.dump({'benchmarks': benchmarks}, f)

    doc, tag, text = yattag.Doc().tagtext()

    with tag('table', style='white-space: nowrap;border-collapse: collapse;'):
        with tag('tr', klass='gray'):
            with tag('th', style='padding:0 5px;'):
                text('Benchmark')
            with tag('th', style='padding:0 5px;'):
                text('JSON')
            with tag('th', style='padding:0 5px', colspan=2):
                text('Before')
            with tag('th', style='padding:0 5px;', colspan=2):
                text('After')
            with tag('th'):
                text('Diff')
            with tag('th', style='padding:0 5px;'):
                text('#SaveLayers')
        for benchmark in benchmarks:
            with tag('tr'):
                with tag('td', klass='lgray'):
                    text(benchmark['name'])

                with tag('td', klass='ctr'):
                    with tag('a', href=benchmark['json']):
                        text('»')

                if benchmark['state'] == 0:
                    # compile failed
                    with tag('td', klass='ctr', colspan=2):
                        with tag('a', href=benchmark['compile_error']):
                            text('!')
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
    with (args.output / 'index.html').open('w', encoding='utf-8') as f:
        f.write(index_template(yattag.indent(doc.getvalue())))
