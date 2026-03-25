---
description: "Generate or improve tests for a file or feature using pytest conventions"
argument-hint: "File path or feature to test"
agent: "agent"
tools: [read, search, edit]
---
Generate tests for: $ARGUMENTS

Follow these project conventions:
- **Framework**: pytest (configured in pyproject.toml)
- **Location**: tests/ directory, files named test_*.py
- **Imports**: Absolute from src root: `from agents.base import BaseAgent`
- **Mocking**: Use unittest.mock for external calls (HTTP, APIs, file I/O)
- **Naming**: `test_<function>_<scenario>` (e.g., `test_fetch_articles_empty_list`)

For each test:
1. Read the source code to understand what to test
2. Cover the happy path first
3. Add edge cases: empty input, None, malformed data, network errors, missing files
4. Mock all external dependencies (no real HTTP calls in tests)
5. Use specific assertions (`assert result == expected`, not just `assert result`)
6. Keep tests independent — no shared mutable state

Output the complete test file, ready to run with `uv run pytest tests/test_<name>.py -v`.
