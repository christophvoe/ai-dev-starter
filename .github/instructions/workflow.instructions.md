---
description: "Use when implementing features, fixing bugs, or completing tasks. Covers verification, TDD, and development workflow standards."
---
# Development Workflow Standards

## Verification Before Completion

**Evidence before claims, always.**

Before claiming work is complete:
1. **IDENTIFY**: What command proves this claim?
2. **RUN**: Execute the full command (fresh, complete)
3. **READ**: Full output, check exit code
4. **VERIFY**: Does output confirm the claim?
5. **ONLY THEN**: Make the claim

Never use "should", "probably", or "seems to" when reporting status.

## Quality Gate

Run before every commit:
```bash
make check   # = ruff + mypy + pytest
```

Or individually:
```bash
uv run ruff check src/ tests/     # lint
uv run mypy src/                   # types
uv run pytest tests/ -v            # tests
```

## TDD Workflow

For features and bug fixes:
1. Write failing test first
2. Watch it fail (confirms it tests the right thing)
3. Write minimal code to pass
4. Watch it pass
5. Refactor (keep tests green)

## Enforced Copilot Workflow

For feature implementation in Copilot, follow this exact order:
1. `make orchestrate-status`
2. Read `docs/orchestration/handoff.md` and `docs/orchestration/human_input.md`
3. Implement only if phase is `IMPLEMENTING`
4. Run `make check`
5. Update `docs/orchestration/handoff.md`
6. Run `make orchestrate-next`

If phase is wrong or requirements are unclear:
- Run `make orchestrate-block REASON="<specific blocker>"`
- Stop instead of guessing

## Commit Discipline

- Format: `type(scope): description`
- Types: feat, fix, refactor, docs, test, chore
- Run `make check` before every commit
- One concern per commit
