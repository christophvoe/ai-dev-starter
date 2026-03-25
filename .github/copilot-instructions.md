# AI Dev Starter — Copilot Instructions

> GitHub Copilot reads this for every chat interaction in this workspace.
> Lean by design — details in `.github/instructions/` and `.github/agents/`.

---

## Project

- **Type**: Python 3.12+ application with Medium scraper, multi-LLM agent, n8n automation
- **Deps**: uv (pyproject.toml + uv.lock), `.venv` managed by uv
- **PYTHONPATH**: `src` (injected by `.vscode/settings.json`)
- **Imports**: Absolute from src root: `from agents.base import BaseAgent`

## Commands

```bash
make check        # lint + typecheck + test (run before every commit)
make test         # pytest only
make lint         # ruff only
make typecheck    # mypy only
make format       # auto-format with ruff
make scrape       # scrape coding list (default)
make scrape-tag TAG="ai-agents"
make scrape OUTPUT=../other-repo/articles  # save elsewhere
make scrape DATED=1   # save into YYYY-MM-DD subfolder
```

## Code Style

- ruff (line-length 100) + mypy strict on src/
- snake_case functions/variables, PascalCase classes, UPPER_SNAKE_CASE constants
- Double quotes, absolute imports, `Path(__file__).resolve().parent` for paths
- Functions under ~50 lines; extract helpers when longer
- Secrets in `.env` via python-dotenv — NEVER hardcode

## Testing

- pytest in tests/, files named test_*.py
- Write tests for new features and bug fixes
- Use unittest.mock for external calls
- Prefer single test file when iterating: `uv run pytest tests/test_specific.py -v`

## Error Handling

- Validate at system boundaries (user input, APIs, HTTP responses)
- Trust internal code — don't over-validate
- Specific exceptions, not bare `except:`
- Log with context: `logger.error("Failed to fetch %s: %s", url, e)`

## Security

- Secrets in `.env` only — never in code or logs
- Validate all external input
- Pin dependency versions (uv.lock)
- Never let agents auto-install packages without review

## Git

- Commit format: `type(scope): description` (feat, fix, refactor, docs, test, chore)
- Pre-commit hooks run ruff + mypy + tests
- Run `make check` before pushing

## Architecture

```
src/agents/base.py            — BaseAgent (Anthropic + OpenAI)
src/knowledge/medium_scraper.py — Medium scraper (HTTP/RSS, no AI)
src/bot/telegram_bot.py       — Optional Telegram bot
src/utils/logger_config.py    — Logging (UTF-8 safe for Windows)
data/knowledge/raw/medium/    — Scraped article Markdown
tests/                        — Test suite
```

## MCP Servers

| Server | Purpose | Setup |
|--------|---------|-------|
| **filesystem** | Read/write project files | Auto |
| **sequential-thinking** | Step-by-step reasoning | Auto |
| **context7** | Live library docs | Auto (free, no key needed) |
| **github** | Commits, PRs, issues | `GITHUB_TOKEN` in `.env` |

### Using Context7
Add `use context7` to any prompt for live library documentation:
```
How do I configure pydantic-ai with streaming? use context7
What is the LangGraph supervisor pattern? use context7
```

### Using Knowledge Base via Filesystem MCP
```
Read all .md files in data/knowledge/raw/medium/ and summarize insights on [topic]
```

## Cross-Tool Workflow (Copilot + Claude Code)

Both tools share the same project knowledge via parallel config files.
Use them together for maximum productivity:

- **`@orchestrator`** — End-to-end: plan + implement + test + review in one pass
- **`@code-reviewer`** — Review changes made by either tool
- **`@planner`** — Plan before implementing (read-only, no edits)
- **`/implement`** — Implement + test + self-review
- **`/review`**, **`/plan`**, **`/test`**, **`/check`** — Focused tasks

**Parallel agents**: Use git worktrees (see `docs/WORKTREES.md`) to run
multiple agents on the same repo without file conflicts.
