---
description: "Use when writing or editing Python tests. Covers pytest patterns, mocking, and test structure for this project."
applyTo: "tests/**/*.py"
---
# Testing Standards

- Framework: pytest (configured in pyproject.toml)
- Files: test_*.py in tests/ directory
- Use unittest.mock for external services (HTTP calls, APIs)
- Test names: `test_<what>_<condition>_<expected>` (e.g., `test_save_empty_slug_raises`)
- Assert one concept per test
- Use fixtures for shared setup
- Mock at system boundaries, not internal functions
- Run single file when iterating: `uv run pytest tests/test_specific.py -v`
- Run all: `make test`
