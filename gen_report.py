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
  <title>EasterEgg Report</title><style type="text/css">body{margin:40px
auto;max-width:650px;line-height:1.6;font-size:18px;color:#444;padding:0
10px}h1,h2,h3{line-height:1.2}td.success{background-color:green}td.fail{background-color:red}</style></head>
  <body><header><h1>EasterEgg Report</h1></header>
<table>
<tr>
  <th>SKP</th>
  <th>JSON</th>
  <th>EGG</th>
  <th>OPT</th>
</tr>"""

    rows = []
    for json_file in args.json.glob('*.json'):
        if (egg_path := (args.eegg / (json_file.stem + '.txt'))).exists():
            # then compilation sucessful
            opt_path = args.opt / (json_file.stem + '.txt')
            row = f"""<tr>
  <td>{json_file.stem}</td>
  <td><a href="{json_file}">»</td>
  <td class="success"><a href="{egg_path}">»</a></td>
  <td><a href="{opt_path}">»</a></td>
</tr>\n"""
            rows.append((json_file.stem, row))
        else:
            err_path = args.err / (json_file.stem + '.txt')
            row = f"""<tr>
  <td>{json_file.stem}</td>
  <td><a href="{json_file}">»</a></td>
  <td class="fail"><a href="{err_path}">»</a></td>
</tr>\n"""
            rows.append((json_file.stem, row))

    rows.sort(key=lambda x: x[0])
    for row in rows:
        string += row[1]
    string += '</table></body></html>'

    with (args.report / 'index.html').open('w') as f:
        f.write(string)
