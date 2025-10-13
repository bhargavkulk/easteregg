# Easteregg Contributor Guide

## Repository Orientation
- This repo houses the tooling for experimenting with Skia draw command traces: `.skp` files are validated (`verify.py`), converted to Egglog (`skp_compiler.py`, `egglog_runner.py`), rendered (`renderer.py`), and aggregated into HTML reports via `mk_report.py`.
- Benchmarks and nightly runs are orchestrated by scripts in `scripts/` and `nightly.sh`. If you change anything that affects the pipeline, read `README.adoc` to understand the workflow before editing code.
- **Never commit raw `.skp` binaries**—keep large assets out of version control and work with the serialized JSON that the tools already generate.

## Environment Setup
- Use Python 3.12 with [`uv`](https://github.com/astral-sh/uv) (see `README.adoc` and `pyproject.toml`). Run `uv sync` before development to install the locked dependencies, including the platform-specific `skia-python` wheels in the repo.
- Prefer `uv run ...` to execute scripts so that the correct environment and wheels are used. The legacy `requirements.txt` exists for tooling that cannot consume `pyproject.toml`; otherwise rely on `uv`.

## Coding Standards
- Follow the Ruff configuration in `pyproject.toml`: 100-character line length and single quotes by default. Run `uv run ruff format <paths>` to auto-format and `uv run ruff check <paths>` to lint.
- When you add or modify modules that expose functions or classes used across scripts, document their purpose with concise docstrings. Inline comments are encouraged for non-obvious Skia/Egglog semantics.
- Keep functions composable; most scripts are orchestrations of pipeline stages, so prefer pure helpers and avoid introducing global state when possible.

## Testing & Verification
- Run `./run.sh` from the repository root. It bootstraps the Egglog submodule, rebuilds the Rust components, installs Python dependencies with `uv`, and regenerates the HTML report so you see the same results that land in CI.
- If you need to inspect an intermediate stage, every major script (for example `verify.py`, `skp_compiler.py`, `egglog_runner.py`, and `mk_report.py`) exposes a CLI via `uv run <script> --help`. Prefer these targeted invocations only for debugging; the required validation for a change is still `./run.sh`.

## Pull Requests & Commits
- Group related changes per commit, and describe how they affect the pipeline (verification, compilation, rendering, reporting, etc.).
- Update `README.adoc` or relevant documentation when you add new steps or change assumptions described there.
- Include the exact `uv run ...` or `make ...` commands you executed in commit/PR descriptions so reviewers can reproduce results.
