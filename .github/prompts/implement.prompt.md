---
description: "Implement a feature and then automatically review it. Chains implementation with code review for quality assurance."
argument-hint: "Describe what to implement"
agent: "agent"
tools: [read, search, edit]
---
You are an orchestrator that chains IMPLEMENTATION and REVIEW in sequence.

## Phase 1: Plan
Before writing code, briefly outline:
- Files to create or modify
- Edge cases to handle
- What tests are needed

## Phase 2: Implement
Implement the feature: $ARGUMENTS

Follow project standards:
- ruff (line-length 100), mypy strict, absolute imports from src/
- Functions under ~50 lines, descriptive names, double quotes
- Secrets in `.env` via python-dotenv, never hardcoded

## Phase 3: Test
Write tests for the new code in tests/test_*.py:
- Use unittest.mock for external calls
- Cover happy path + edge cases
- Run: `uv run pytest tests/ -v`

## Phase 4: Self-Review
After implementing, review your OWN changes critically:
1. **Code Quality**: DRY violations? Functions too long? Names descriptive?
2. **Security**: Any hardcoded secrets, unsafe input, eval/exec?
3. **Error Handling**: Specific exceptions? Boundary validation?
4. **Type Safety**: Type hints on public APIs?

For each issue found in self-review, fix it before finishing.

## Phase 5: Quality Gate
Run `uv run ruff check src/ tests/` and `uv run mypy src/` and fix any issues.

## Output
End with a summary: what was implemented, what was tested, what the self-review found and fixed.
