import shutil
import sys
from pathlib import Path
from pprint import pprint

from pyparsing import Word, alphanums, nested_expr


def parse_sexp(sexp: str, let: bool = False):
    expr = nested_expr('(', ')', content=Word(alphanums + '-.+*/='))
    return (
        expr.parse_string(sexp).as_list()[0] if not let else expr.parse_string(sexp).as_list()[0][2]
    )


def is_layer_command(sexp: list[list | str]):
    return len(sexp) >= 0 and sexp[0] in ('SrcOver', 'Src', 'DstIn', 'Other')


def split_out(sexp: list[list | str]):
    commands = []
    stack = [sexp]
    while len(stack) != 0:
        item = stack.pop()
        if isinstance(item, list):
            if is_layer_command(item):
                commands.insert(0, item[2])
                stack.append(item[1])

    pprint(commands)


if __name__ == '__main__':
    file = Path(sys.argv[1])
    with file.open('r') as f:
        sexp = f.read()

    split_out(parse_sexp(sexp, True))
