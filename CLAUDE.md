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
  knowledge/medium_scraper.py -- Medium article scraper + TrendDiscoverer (HTTP, RSS)
  knowledge/article_curator.py -- ArticleCurator: LLM-powered article selection agent
  bot/telegram_bot.py         -- Telegram bot: /status, /scrape, /discover, /ask
  bot/notify.py               -- Telegram notification module (standalone)
  utils/logger_config.py      -- Logging setup (UTF-8 safe for Windows)

data/knowledge/raw/medium/    -- Scraped articles as Markdown
data/knowledge/meta/          -- JSON metadata sidecars
tests/                        -- Test suite (pytest)
Makefile                      -- Task runner (make check, make scrape, etc.)
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
make scrape                                    # default coding list
make scrape-list URL="https://medium.com/@user/list/name-abc123"
make scrape-tag TAG="github copilot, claude code"
make scrape-bookmarks
make summarize

# Discovery + LLM curation
make discover TAGS="ai-agents,llm" KEYWORDS="agent,Claude"
make discover TAGS="ai-agents,llm" CURATE=1        # LLM picks the best
make discover-scrape TAGS="ai-agents,llm" CURATE=1  # discover + auto-scrape

# Save to custom dir / dated subfolder
make scrape-list URL="..." OUTPUT="../other-repo/articles"
make scrape-list URL="..." DATED=1                  # saves into YYYY-MM-DD subfolder
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

## 10. Superpowers (Claude Code Plugin)

**Install** (run inside a Claude Code session, NOT in PowerShell):
```
1. Open terminal → type: claude
2. Inside the Claude Code REPL, type: /plugin install superpowers@claude-plugins-official
```
⚠ `/plugin` is a Claude Code command — it does NOT work in PowerShell or bash.

Superpowers provides enforced workflows. Key skills it activates automatically:
- **brainstorming** -- Design before code. Explores approaches, writes specs.
- **writing-plans** -- Detailed task-by-task implementation plans with TDD.
- **subagent-driven-development** -- Fresh subagent per task + two-stage review.
- **test-driven-development** -- Red-Green-Refactor enforced. No code without failing test.
- **systematic-debugging** -- Root cause investigation before fixes. No guessing.
- **verification-before-completion** -- Evidence before claims. Run commands, read output.
- **using-git-worktrees** -- Isolated workspaces for parallel development.
- **requesting-code-review** -- Structured review with spec compliance + quality checks.

**Workflow**: brainstorming -> writing-plans -> subagent-driven-development -> finishing-a-development-branch

Our `.claude/commands/` and `.claude/rules/` complement superpowers with project-specific context.

---

## 11. Agentic Workflow

**Pattern**: Plan -> Implement -> Verify -> Adjust

**Slash commands** (project-specific, complement superpowers):
- `/plan` -- Plan before coding
- `/implement` -- Implement + test + self-review in one pass
- `/review` -- Code review for quality and security
- `/test` -- Generate tests for a file or feature
- `/check` -- Run full quality gate (ruff + mypy + pytest)

**Telegram notifications** (see `src/bot/notify.py`):
- `make notify MSG="your message"` -- Send a message to Telegram
- Scraper auto-notifies after runs via `send_scrape_report()`
- Bot commands: /status, /scrape, /discover, /review, /check, /ask, /help

**Automated code review** (see `src/agents/reviewer.py`):
- `make review` -- AI reviews uncommitted changes (needs ANTHROPIC_API_KEY)
- `make review BRANCH=feat/x` -- AI reviews a branch vs main
- `make review NOTIFY=1` -- Review + send results to Telegram
- Telegram `/review [branch]` -- trigger review from phone

**Context management**:
- Run `compact` when conversation gets long (>70% of context window)
- Run `clear` when switching to a completely different task

**Parallel agents with git worktrees** (see docs/WORKTREES.md):
- Create worktrees for parallel work: `git worktree add ../agent-2 -b feature/task`
- One agent implements, the other reviews the branch

**MCP Servers available**:

| MCP | Purpose | When to use |
|-----|---------|-------------|
| filesystem | Read/write project files | File operations |
| sequential-thinking | Step-by-step reasoning | Complex planning |
| context7 | Live library docs | Add `use context7` to prompt |
| github | Commits, PRs, history | Git operations (needs GITHUB_TOKEN) |

---

## 12. Orchestration Protocol

**State machine**: PLANNING → IMPLEMENTING → REVIEWING → DONE
**Interrupt states**: BLOCKED (needs human), PAUSED (human command), STOPPED (terminated)

**Shared state files** (in `docs/orchestration/`):

- `session.json` — machine state (phase, agent, counters, status)
- `handoff.md` — agent content: task, changed files with line numbers, output, uncertainty
- `human_input.md` — free-form Telegram input for next agent pickup

**Agent assignment rule**:

- Same agent plans + implements + first review
- Opposite agent only on second review (after FIXING cycle)

**Loop prevention — triggers BLOCKED + Telegram alert**:

- `iterations >= 3` (fix cycles)
- `failed_checks >= 2` (quality gate failures)
- `uncertainty = true` (agent flags uncertainty in handoff.md)

**Orchestration commands**:

```bash
make orchestrate-start TASK="..." [AGENT=copilot] [WORKTREE=1]
make orchestrate-status
make orchestrate-next            # advance after review passes
make orchestrate-next FAILED=1   # advance after review fails
make orchestrate-block REASON="..."
make orchestrate-resume
make orchestrate-done
make orchestrate-check-failed    # call after make check fails
make orchestrate-explain         # send Explanation section to Telegram
```

**Handoff format** (`docs/orchestration/handoff.md`):

```markdown
## Task
<what was done>

## Changed Files
- src/agents/orchestrator.py:45-78 (add phase transition logic)

## Output
<test results, key observations>

## Explanation
<plain English: what changed, why, how the key logic works>

## Uncertainty
None  (or describe what needs human input)
```

**Telegram control plane**:

- `/status` — session state summary
- `/pause` `/stop` `/resume` `/skip` — session control
- Any free-form text → saved to `human_input.md` for next agent pickup

---

## Conventions Summary

- **uv** for deps (pyproject.toml + uv.lock)
- **ruff** for lint/format, **mypy** for types, **pytest** for tests
- **pre-commit** hooks enforce quality on every commit
- **superpowers** plugin for enforced TDD, planning, review workflows
- `PYTHONPATH=src` -- import as `from agents.base import BaseAgent`
- Secrets in `.env` -- see `.env.example` for template
