## Testing Rules

These rules apply when writing or modifying tests.

### Framework & Location
- pytest (configured in pyproject.toml)
- Tests in tests/ directory, files named test_*.py
- Run: `make test` or `uv run pytest`
- Single file: `uv run pytest tests/test_specific.py -v`

### Test Structure
- Name tests: `test_<function>_<scenario>`
- One assertion concept per test (multiple asserts OK if testing same thing)
- Keep tests independent — no shared mutable state between tests
- Use fixtures for common setup

### Mocking
- Use unittest.mock for all external calls (HTTP, APIs, file I/O)
- Never make real network calls in tests
- Mock at the boundary: patch the import in the module under test
- Example: `@patch("knowledge.medium_scraper.requests.get")`

### What to Test
- Happy path first
- Edge cases: empty input, None, malformed data
- Error paths: network errors, 403/429, timeouts, missing files
- Boundary conditions: empty lists, single items, Unicode content

### Assertions
- Use specific assertions: `assert result == expected`
- Not just `assert result` (truthy check)
- For exceptions: `with pytest.raises(SpecificError):`
