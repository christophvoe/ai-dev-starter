---
description: "Use when editing Makefile, pyproject.toml, .pre-commit-config.yaml, or other build/config files. Covers project toolchain conventions."
applyTo: "{Makefile,pyproject.toml,.pre-commit-config.yaml}"
---
# Build & Config Standards

- **Package manager**: uv (not pip, not poetry). Deps in pyproject.toml, locked in uv.lock
- **Makefile**: Primary task runner. All commands use `uv run` prefix
- **Quality gates**: `make check` = lint + typecheck + test (required before every commit)
- **Linter/formatter**: ruff (configured in pyproject.toml [tool.ruff])
- **Type checker**: mypy strict on src/ (configured in pyproject.toml [tool.mypy])
- **Tests**: pytest (configured in pyproject.toml [tool.pytest.ini_options])
- **Pre-commit**: ruff + mypy hooks in .pre-commit-config.yaml
- **Python version**: >= 3.11, target py311 in ruff
- **PYTHONPATH**: src (set in pyproject.toml and .vscode/settings.json)
