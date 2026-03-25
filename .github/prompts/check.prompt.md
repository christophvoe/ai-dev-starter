---
description: "Run all quality checks: lint with ruff, typecheck with mypy, run tests with pytest"
agent: "agent"
tools: [read, search]
---
Run the full quality gate for this project:

1. **Lint**: `uv run ruff check src/ tests/` — fix any violations
2. **Format**: `uv run ruff format --check src/ tests/` — report formatting issues
3. **Typecheck**: `uv run mypy src/` — fix any type errors
4. **Tests**: `uv run pytest tests/ -v` — all tests must pass

For each failure:
- State the file and specific error
- Provide the fix
- Explain why it matters

End with: pass/fail summary and the command to re-verify (`make check` or the individual commands above).
