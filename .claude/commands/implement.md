Implement, test, and self-review the following: $ARGUMENTS

## Phase 1: Plan
Before writing code, briefly outline:
- Files to create or modify
- Edge cases to handle
- What tests are needed

## Phase 2: Implement
Write the code following project standards:
- ruff (line-length 100), mypy strict, absolute imports from src/
- Functions under ~50 lines, descriptive names, double quotes
- Secrets in `.env` via python-dotenv, never hardcoded

## Phase 3: Test
Write tests in tests/test_*.py:
- Use unittest.mock for external calls
- Cover happy path + edge cases
- Run: `uv run pytest tests/ -v`

## Phase 4: Self-Review
After implementing, critique your own changes:
1. **Code Quality**: DRY violations? Functions too long? Descriptive names?
2. **Security**: Hardcoded secrets, unsafe input handling, eval/exec?
3. **Error Handling**: Specific exceptions? Boundary validation?
4. **Type Safety**: Type hints on public APIs?

Fix any issues found before finishing.

## Phase 5: Quality Gate
Run `uv run ruff check src/ tests/` and `uv run mypy src/` to verify.

## Output
Summarize: what was implemented, tested, and fixed during self-review.
