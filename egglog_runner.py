import os
import subprocess
from pathlib import Path


def run_cmd(cmd, **kwargs):
    try:
        # Copy the current environment
        # my_env = os.environ.copy()
        # for key in kwargs.keys():
        #     my_env[key] = kwargs[key]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, '', str(e)


def run_egglog(egg_file):
    prelude = Path('./egg-files/lambda_skia.egg')
    extraction = Path('./egg-files/extract.egg')

    command = (
        f'cargo run --quiet --manifest-path egglog/Cargo.toml -- {prelude} {egg_file} {extraction}'
    )
    return run_cmd(command.split(), RUST_LOG='error')
