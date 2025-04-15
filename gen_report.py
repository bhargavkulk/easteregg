import argparse
import shutil
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('json', type=Path)
    parser.add_argument('eegg', type=Path)
    parser.add_argument('err', type=Path)
    parser.add_argument('opt', type=Path)
    parser.add_argument('report', type=Path)

    args = parser.parse_args()

    args.report.mkdir(exist_ok=True)

    def copytree(thing):
        shutil.copytree(thing, args.report / thing.name)

    copytree(args.json)
    copytree(args.eegg)
    copytree(args.err)
    copytree(args.opt)

    string = """<!DOCTYPE html><html><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EasterEgg Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
  <style type="text/css">:root{--uchu-gray-raw: 84.68% 0.002 197.12;--uchu-gray: oklch(var(--uchu-gray-raw));--uchu-yellow-raw: 90.92% 0.125 92.56;--uchu-yellow: oklch(var(--uchu-yellow-raw));--uchu-red-raw: 62.73% 0.209 12.37;--uchu-red: oklch(var(--uchu-red-raw));--uchu-green-raw: 79.33% 0.179 145.62;--uchu-green: oklch(var(--uchu-green-raw));}body{margin:40px
auto;max-width:650px;line-height:1.6;font-size:18px;color:#444;padding:0
10px}h1,h2,h3{line-height:1.2}.success{background-color:var(--uchu-green)}.compilefail{background-color:var(--uchu-gray)}.fail{background-color:var(--uchu-red)}.same{background-color:var(--uchu-yellow)}body{font-family:'Public Sans',sans-serif}</style></head>
  <body><header><h1>EasterEgg Report</h1></header>\n"""

    rows = []
    improved = 0
    regressed = 0
    unchanged = 0
    failed_to_compile = 0
    for json_file in args.json.glob('*.json'):
        if (egg_path := (args.eegg / (json_file.stem + '.txt'))).exists():
            # then compilation sucessful
            opt_path = args.opt / (json_file.stem + '.txt')
            with egg_path.open('r') as f:
                egg = f.read()
            with opt_path.open('r') as f:
                opt = f.read()

            start = egg.count('SaveLayer')
            end = opt.count('SaveLayer')

            thing = ''
            if start == end:
                thing = 'same'
                unchanged += 1
            elif start > end:
                improved += 1
                thing = 'success'
            else:
                regressed += 1
                thing = 'fail'

            row = f"""<tr>
  <td>{json_file.stem}</td>
  <td><a href="{json_file}">»</td>
  <td class="success"><a href="{egg_path}">»</a></td>
  <td><a href="{opt_path}">»</a></td>
  <td class="{thing}">{start} → {end}</td>
</tr>\n"""
            rows.append((json_file.stem, row))
        else:
            failed_to_compile += 1
            err_path = args.err / (json_file.stem + '.txt')
            row = f"""<tr>
  <td>{json_file.stem}</td>
  <td><a href="{json_file}">»</a></td>
  <td class="compilefail"><a href="{err_path}">»</a></td>
</tr>\n"""
            rows.append((json_file.stem, row))

    rows.sort(key=lambda x: x[0])
    string += (
        f'<p>No. of websites <span class="success">Improved</span>: {improved}/{len(rows)}<br/>\n'
    )
    string += f'No. of websites <span class="fail">Regressed</span>: {regressed}/{len(rows)}<br/>\n'
    string += f'No. of websites <span class="same">Unchanged</span>: {unchanged}/{len(rows)}<br/>\n'
    string += f'No. of websites <span class="compilefail">Failed to Compile</span>: {failed_to_compile}/{len(rows)}</p>\n'

    string += """<table>
<tr>
  <th>SKP</th>
  <th>JSON</th>
  <th>EGG</th>
  <th>OPT</th>
  <th>#SaveLayer</th>
</tr>"""
    for row in rows:
        string += row[1]
    string += '</table></body></html>'

    with (args.report / 'index.html').open('w') as f:
        f.write(string)
