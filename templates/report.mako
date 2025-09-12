<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&amp;display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="rsrc/style.css" />
    <script src="rsrc/sortable.min.js"></script>
    <title>EasterEgg Report</title>
</head>
<body>
    <h1>EasterEgg Report</h1>
    <p>
        No. of websites <span class="green">Improved</span>: ${content['improved']}/${content['num_benchmarks']}<br />
        No. of websites <span class="yellow">Unchanged</span>: ${content['unchanged']}/${content['num_benchmarks']}<br />
        No. of websites <span class="red">Regressed</span>: ${content['regressed']}/${content['num_benchmarks']}<br />
        No. of websites <span>Failed</span>:  ${content['failed']}/${content['num_benchmarks']}
    </p>
    <table data-sortable>
        <thead>
            <tr>
                <th>Benchmark</th>
                <th>JSON</th>
                <th>SkiaChrome</th>
                <th>Before</th>
                <th>After</th>
                <th>Diff</th>
                <th>#SaveLayers</th>
                <th>PNG</th>
            </tr>
        </thead>
        <tbody>
            % for row in content['results']:
            <tr>
                <td class="lgray">${row['full_name']}</td>
                <td><a href="${row['json_skp']}">${row['number_cmds']}</a></td>
                % if 'verify_error' in row:
                    <td><a href="${row['verify_error']}">!</a></td>
                % else:
                    <td class="void"></td>
                % endif
                % if row['state'] == 0:
                    <td><a href="${row['compile_error']}">!</a></td>
                    <td colspan="4" class="void"></td>
                % elif row['state'] == 1:
                    <td><a href="${row['pre_file']}">&raquo;</a></td>
                    <td><a href="${row['egglog_error']}">!</a></td>
                    <td colspan="3" class="void"></td>
                % elif row['state'] == 2:
                    <td><a href="${row['pre_file']}">&raquo;</a></td>
                    <td><a href="${row['post_file']}">&raquo;</a></td>
                    <td><a href="${row['diff_file']}">&raquo;</a></td>
                    % if row['counts'][0] > row['counts'][1]:
                        <td class="green">${row['counts'][0]} → ${row['counts'][1]}</td>
                    % elif row['counts'][0] == row['counts'][1]:
                        <td class="yellow">${row['counts'][0]} → ${row['counts'][1]}</td>
                    % else:
                        <td class="red">${row['counts'][0]} → ${row['counts'][1]}</td>
                    % endif
                    <td>
                        % if 'pre_png' in row:
                            <a href="${row['pre_png']}">&raquo;</a>
                        % elif 'pre_png_err' in row:
                            <a href="${row['pre_png_err']}">!</a>
                        % endif
                        |
                        % if 'post_png' in row:
                            <a href="${row['post_png']}">&raquo;</a>
                        % elif 'post_png_err' in row:
                            <a href="${row['post_png_err']}">!</a>
                        % endif
                        |
                        % if 'png_diff' in row:
                            <a href="${row['png_diff']}">&raquo;</a>
                        % else:
                            !
                        % endif
                    </td>
                % endif
            </tr>
            % endfor
        </tbody>
    </table>
</body>
</html>
