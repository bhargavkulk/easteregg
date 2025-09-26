import argparse
import json
import shutil
import sys
import traceback
from argparse import Namespace
from difflib import HtmlDiff
from pathlib import Path
from typing import Any, final

from mako.template import Template

from egglog_runner import run_cmd, run_egglog
from lambda_skia import pretty_print_layer
from parse_sexp import parse_sexp
from renderer import egg_to_png
from skp_compiler import compile_skp_to_lskia, get_reset_warnings
from verify import verify_skp

EGG = 'egg'
JSON = 'json'


@final
class CleanHtmlDiff(HtmlDiff):
    _legend = ''


def rewrite_name(string: str) -> str:
    suite, name = string.split('__', 1)
    name = name.replace('_', ' ')
    suite = suite.replace('_', ' ')
    return suite + ' | ' + name


class Args(Namespace):
    bench: Path
    rsrc: Path
    output: Path


def collate_data(args: Args):
    def htmlify_path(path: Path):
        return './' + str(path.relative_to(args.output))

    EGG_FOLDER: Path = args.output / EGG
    JSON_FOLDER: Path = args.output / JSON

    results = []
    improved = 0
    unchanged = 0
    regressed = 0
    failed = 0

    benchmarks: list[Path] = list(args.bench.glob('*.json'))

    for i, benchmark in enumerate(benchmarks):
        print(f'[{i + 1}/{len(benchmarks)}] running ' + str(benchmark))

        data: dict[str, Any] = dict()
        data['state'] = 2

        name = benchmark.stem
        data['name'] = name

        full_name = rewrite_name(name)
        data['full_name'] = full_name

        suite, _ = name.split('__', 1)
        data['website'] = suite.replace('_', '-'.lower())

        # 1. read JSON skp

        with benchmark.open('rb') as f:
            json_skp = json.load(f)

        shutil.copy(benchmark, JSON_FOLDER / benchmark.name)
        data['json_skp'] = htmlify_path(JSON_FOLDER / benchmark.name)

        data['number_cmds'] = len(json_skp['commands'])

        # 2. verify the JSON skp conforms to our skia subset
        try:
            verify_skp(json_skp)
        except Exception:
            tb = traceback.format_exc()
            error_file = args.output / (name + '__VERIFY_ERR.txt')
            error_file.write_text(tb)
            data['verify_error'] = htmlify_path(error_file)

        # 3. compile to lambda skia
        try:
            pre_expr = compile_skp_to_lskia(json_skp['commands'])
            egglog_input = pre_expr.sexp()

            warnings = get_reset_warnings()
            warning_file: Path = args.output / (name + '__CWARN.txt')
            if len(warnings) != 0:
                warning_file.write_text('\n'.join(warnings) + '\n')
                data['warn_file'] = htmlify_path(warning_file)

            egglog_file: Path = EGG_FOLDER / (name + '.egg')
            egglog_file.write_text('(let test ' + egglog_input + ')')

            fmt_file = args.output / (name + '__PRE.txt')
            pre_fmt = pretty_print_layer(pre_expr)
            fmt_file.write_text(pre_fmt)
            data['pre_file'] = htmlify_path(fmt_file)

        except Exception:
            tb = traceback.format_exc()
            error_file = args.output / (name + '__PRE_ERR.txt')
            error_file.write_text(tb)
            data['compile_error'] = htmlify_path(error_file)
            data['state'] = 0
            results.append(data)
            failed += 1
            continue

        # 4. optimize in egglog
        ret_code, egglog_output, stderr = run_egglog(egglog_file)

        if ret_code == 0:
            fmt_file = args.output / (name + '__POST.txt')
            post_expr = parse_sexp(egglog_output)
            post_fmt = pretty_print_layer(post_expr)
            fmt_file.write_text(post_fmt)
            data['post_file'] = htmlify_path(fmt_file)

            egglog_warning_file = args.output / (name + '__EWARN.txt')
            egglog_warning_file.write_text(stderr)
        else:
            err_file = args.output / (name + '__POST_ERR.txt')
            err_file.write_text(stderr)
            data['egglog_error'] = htmlify_path(err_file)
            data['state'] = 1
            results.append(data)
            failed += 1
            continue

        # 5. Make the diff
        diff = CleanHtmlDiff().make_file(
            pre_fmt.splitlines(),
            post_fmt.splitlines(),
            fromdesc='Pre Opt',
            todesc='Post Opt',
        )
        diff_file = args.output / (name + '__DIFF.html')
        diff_file.write_text(diff)
        data['diff_file'] = htmlify_path(diff_file)

        # 6. Count savelayers
        before = egglog_input.count('SaveLayer')
        after = egglog_output.count('SaveLayer')

        data['counts'] = [before, after]

        if before == after:
            unchanged += 1
        elif before < after:
            regressed += 1
        else:
            improved += 1

        # 6. draw lambda skia to png
        pre_png = args.output / (name + '__PRE.png')
        pre_res = egg_to_png(json_skp, pre_expr, pre_png)

        post_png = args.output / (name + '__POST.png')
        post_res = egg_to_png(json_skp, post_expr, post_png)

        if pre_res is None:
            data['pre_png'] = htmlify_path(pre_png)
        else:
            pre_png_error = args.output / (name + '__PRE_PNG_ERR.txt')
            pre_png_error.write_text(pre_res)
            data['pre_png_err'] = htmlify_path(pre_png_error)

        if post_res is None:
            data['post_png'] = htmlify_path(post_png)
        else:
            post_png_error = args.output / (name + '__POST_PNG_ERR.txt')
            post_png_error.write_text(post_res)
            data['post_png_err'] = htmlify_path(post_png_error)

        if pre_res is None and post_res is None:
            png_diff = args.output / (name + '__PNG_DIFF.png')
            ret, stdout, stdin = run_cmd(f'compare {pre_png} {post_png} {png_diff}'.split())
            data['png_diff'] = htmlify_path(png_diff)

        results.append(data)

    results = sorted(results, key=lambda d: [p.lower() for p in d['name'].split('__', 1)])

    json_results = {
        'results': results,
        'num_benchmarks': len(benchmarks),
        'improved': improved,
        'unchanged': unchanged,
        'regressed': regressed,
        'failed': failed,
    }

    with (args.output / 'report.json').open('w') as f:
        json.dump(json_results, f)

    return json_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bench', type=Path)
    parser.add_argument('rsrc', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(namespace=Args())

    if args.output.exists():
        print('output folder exists, delete before running script', file=sys.stderr)
        sys.exit(1)

    args.output.mkdir()
    (args.output / EGG).mkdir()
    (args.output / JSON).mkdir()

    content = collate_data(args)

    template = Template(filename='./templates/report.mako')
    report = template.render(content=content)
    (args.output / 'index.html').write_text(report, encoding='utf-8')

    shutil.copytree(args.rsrc, args.output / args.rsrc)
