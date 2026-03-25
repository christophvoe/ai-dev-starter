# AI Dev Starter -- Claude Code Context

> Auto-read by Claude Code at session start. Keep under 500 lines.
> See @README.md for project overview. See @pyproject.toml for dependencies.

---

## 1. Architecture Blueprint

**Type**: Python 3.12+ application
**Dep management**: uv (pyproject.toml + uv.lock)
**Runtime**: .venv created by uv, PYTHONPATH=src

```
src/
  agents/base.py              -- BaseAgent: multi-LLM wrapper (Anthropic + OpenAI)
  knowledge/medium_scraper.py -- Medium article scraper (pure HTTP, curl_cffi, RSS)
  bot/telegram_bot.py         -- Optional Telegram bot
  utils/logger_config.py      -- Logging setup (UTF-8 safe for Windows)

data/knowledge/raw/medium/    -- Scraped articles as Markdown
data/knowledge/meta/          -- JSON metadata sidecars
n8n_workflows/                -- 2 n8n workflow JSONs (visual config layer)
tests/                        -- Test suite (pytest)
```

**Data flow**: CLI/n8n -> MediumScraper -> HTTP/RSS fetch -> HTML parse -> Markdown + JSON save
**No AI needed for scraping** -- pure HTTP with curl_cffi for Cloudflare bypass.

---

## 2. Command Center

```bash
# Setup
make install          # First-time: venv + deps + pre-commit hooks
make sync             # Quick dependency sync

# Code quality (run before every commit)
make check            # lint + typecheck + test (all at once)
make lint             # ruff only
make typecheck        # mypy only
make test             # pytest only
make format           # auto-format with ruff

# Scraping
make scrape           # Scrape coding list (default)
make scrape-tag TAG="ai-agents"
make scrape-bookmarks # Private bookmarks (needs cookies)
make summarize        # Show article digest

# Save to different repo / dated subfolder
make scrape OUTPUT=../other-repo/articles
make scrape DATED=1   # saves into YYYY-MM-DD subfolder
```

---

## 3. Code Style

- **Formatter/Linter**: ruff (configured in pyproject.toml, line-length 100)
- **Type checker**: mypy (strict on src/)
- **Imports**: Absolute imports from src/ root (e.g., `from agents.base import BaseAgent`)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Strings**: Double quotes preferred
- **Constants**: UPPER_SNAKE_CASE at module level
- **Max function length**: ~50 lines; split into helpers if longer
- **Paths**: Always `Path(__file__).resolve().parent`, never hardcoded strings
- **Secrets**: Via python-dotenv + `.env`, NEVER hardcoded
- **Async**: Wrap with `asyncio.run()` at entry point, never mix sync/async

---

## 4. Testing

- **Framework**: pytest (configured in pyproject.toml)
- **Location**: tests/ directory, files named test_*.py
- **Run**: `make test` or `uv run pytest`
- **Philosophy**: Write tests for new features and bug fixes. Run tests before every commit.
- **Prefer single test**: When iterating, run one test file: `uv run pytest tests/test_specific.py -v`
- **Mocking**: Use unittest.mock for external services (HTTP calls, APIs)
- **Coverage**: `make test-cov` for coverage report

---

## 5. Error Handling

- Validate at system boundaries (user input, external APIs, HTTP responses)
- Trust internal code and framework guarantees -- don't over-validate
- Use specific exceptions, not bare `except:`
- Log errors with context: `logger.error("Failed to fetch %s: %s", url, e)`
- HTTP errors: Check status codes, handle timeouts, retry with backoff for transient failures
- File I/O: Use `Path` methods, handle encoding explicitly (UTF-8)
- Never swallow exceptions silently

---

## 6. Clean Code

- Functions under ~50 lines; extract helpers when longer
- DRY: If you repeat 3+ lines, extract a function
- Single Responsibility: Each function/class does one thing
- Descriptive names: `fetch_article_content()` not `process()`
- No dead code or commented-out blocks (version control handles history)
- Avoid premature abstraction: Don't create helpers for one-time operations

---

## 7. Security

- Secrets in `.env` only, loaded via `python-dotenv`. Never in code or logs.
- Validate all external input (user arguments, API responses, scraped HTML)
- Use parameterized queries for any database operations
- Never `eval()` or `exec()` on external data
- Pin dependency versions (uv.lock). Audit before updating.
- Never let agents auto-install packages without review
- Cookie handling: Treat MEDIUM_COOKIES as sensitive credentials

---

## 8. Git & Teamwork

- **Branch from**: main
- **Commit format**: `type(scope): description` (e.g., `feat(scraper): add --output flag`)
- **Types**: feat, fix, refactor, docs, test, chore
- **Pre-commit**: Hooks run ruff + mypy + tests on every commit
- **PR etiquette**: Run `make check` before pushing. Describe what changed and why.

---

## 9. Edge Cases

Before implementing, think about:
- What if the input is empty, None, or malformed?
- What if the network request times out or returns 403/429?
- What if the file already exists or the directory is missing?
- What if the user passes an invalid URL or path?
- What happens on Windows vs Unix (path separators, encoding)?

Flag edge cases during design before writing code.

---

## 10. Agentic Workflow

**Pattern**: Plan -> Implement -> Verify -> Adjust

1. **Plan**: Describe approach before writing code. For complex tasks, propose a plan first.
2. **Implement**: Work in small, testable chunks. One concern per commit.
3. **Verify**: Run `make check` after changes. Confirm tests pass.
4. **Adjust**: If tests fail or lint errors appear, fix before moving on.

**Slash commands available**:
- `/plan` -- Plan before coding
- `/implement` -- Implement + test + self-review in one pass
- `/review` -- Code review for quality and security
- `/test` -- Generate tests for a file or feature
- `/check` -- Run full quality gate (ruff + mypy + pytest)

**Context management**:
- Run `compact` when conversation gets long (>70% of context window)
- Run `clear` when switching to a completely different task
- Don't dump entire files when a targeted search suffices

**Parallel agents with git worktrees** (see docs/WORKTREES.md):
- Create worktrees for parallel work: `git worktree add ../agent-2 -b feature/task`
- One agent implements, the other reviews the branch
- Merge after review passes; remove worktree when done

**MCP Servers available**:

| MCP | Purpose | When to use |
|-----|---------|-------------|
| filesystem | Read/write project files | File operations |
| sequential-thinking | Step-by-step reasoning | Complex planning |
| context7 | Live library docs | Add `use context7` to prompt |
| github | Commits, PRs, history | Git operations (needs GITHUB_TOKEN) |

---

## Conventions Summary

- **uv** for deps (pyproject.toml + uv.lock)
- **ruff** for lint/format, **mypy** for types, **pytest** for tests
- **pre-commit** hooks enforce quality on every commit
- `PYTHONPATH=src` -- import as `from agents.base import BaseAgent`
- Secrets in `.env` -- see `.env.example` for template
