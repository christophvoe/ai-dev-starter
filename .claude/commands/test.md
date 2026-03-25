Generate tests for: $ARGUMENTS

Follow these project conventions:
- **Framework**: pytest (configured in pyproject.toml)
- **Location**: tests/ directory, files named test_*.py
- **Imports**: Absolute from src root (`from agents.base import BaseAgent`)
- **Mocking**: Use unittest.mock for external calls (HTTP, APIs, file I/O)
- **Naming**: `test_<function>_<scenario>` (e.g., `test_fetch_articles_empty_list`)

Process:
1. Read the source code to understand what needs testing
2. Cover the happy path first
3. Add edge cases: empty input, None, malformed data, network errors, missing files
4. Mock ALL external dependencies — no real HTTP calls
5. Use specific assertions (`assert result == expected`, not just `assert result`)
6. Keep tests independent — no shared mutable state

Output the complete test file, ready to run with:
```bash
uv run pytest tests/test_<name>.py -v
```

After generating, run the tests to verify they pass.
