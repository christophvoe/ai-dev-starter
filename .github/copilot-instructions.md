# AI Dev Starter — GitHub Copilot Context

> Auto-loaded by Copilot for every chat interaction. Keep under 400 lines.

---

## 1. Architecture

**Type**: Python 3.12+ application | **Deps**: uv (pyproject.toml + uv.lock)
**PYTHONPATH=src** — import as `from agents.base import BaseAgent`

```
src/
  agents/base.py              — BaseAgent: multi-LLM wrapper (Anthropic + OpenAI)
  agents/orchestrator.py      — State machine: PLANNING→IMPLEMENTING→REVIEWING→DONE
  agents/onboarding.py        — Interactive new-project setup agent
  knowledge/medium_scraper.py — Medium article scraper (HTTP/RSS, no AI needed)
  knowledge/article_curator.py — LLM-powered article curation
  bot/telegram_bot.py         — Telegram bot: remote control + free-form human input
  bot/notify.py               — Telegram notifications (standalone)
  utils/logger_config.py      — Logging setup

docs/orchestration/           — Session state (session.json, handoff.md, human_input.md)
```

---

## 2. Orchestration Protocol

**ALWAYS check session state before starting any work.**

```bash
make orchestrate-status      # see current phase, agent, task
```

The session state machine:
```
PLANNING → IMPLEMENTING → REVIEWING → DONE
                               ↓ (if review fails)
                            FIXING → REVIEWING (other agent)
```

**Shared files** (both tools read/write these):
- `docs/orchestration/session.json` — current phase, agent, iteration count
- `docs/orchestration/handoff.md` — plan / output / changed files for pickup
- `docs/orchestration/human_input.md` — guidance from Telegram, read at phase start

**Key commands:**
```bash
make orchestrate-start TASK="description"   # new session
make orchestrate-next                        # advance phase + notify Telegram
make orchestrate-next FAILED=1               # review failed, go to FIXING
make orchestrate-block REASON="..."         # flag uncertainty, pause, notify human
make orchestrate-resume                      # human cleared it, continue
make orchestrate-done                        # session complete
make orchestrate-check-failed               # make check failed, increment counter
```

---

## 3. Agent Assignment Rule

**Same agent: plans + implements + first review.**
Only after FIXING does the other agent review (fresh eyes).

```
You plan → You implement → You review (first)
  → FIXING needed? → Other agent reviews (second)
  → FIXING again? → Human intervenes (BLOCKED)
```

---

## 4. Code Style

- **Formatter/Linter**: ruff (line-length 100)
- **Type checker**: mypy (strict on src/)
- **Imports**: absolute from src/ root — `from agents.base import BaseAgent`
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_SNAKE_CASE constants
- **Strings**: double quotes preferred
- **Max function length**: ~50 lines — extract helpers if longer
- **Paths**: `Path(__file__).resolve().parent` — never hardcoded strings
- **Secrets**: via python-dotenv + `.env` — NEVER hardcoded or logged

---

## 5. Quality Gate

Run before EVERY handoff or commit:
```bash
make check    # ruff + mypy + pytest (all at once)
```

If it fails twice: run `make orchestrate-check-failed` instead of pushing broken code.

---

## 6. Testing

- pytest in `tests/test_*.py`
- Mock ALL external calls: `@patch("module.requests.get")`
- Test naming: `test_<function>_<scenario>`
- Cover: happy path + None/empty + network errors + boundary conditions

---

## 7. Commit Format

```
type(scope): description

Types: feat, fix, refactor, docs, test, chore
Example: feat(orchestrator): add loop prevention triggers
```

---

## 8. Skills Reference

### This tool (Copilot agents)

| Agent | When | Key gate |
|-------|------|---------|
| `@planner` | Design + plan | ✅ Write to handoff.md first |
| `@orchestrator` | End-to-end feature | ✅ Check session.json, run gates |
| `@tdd` | TDD implementation | ✅ Failing test before production code |
| `@debugger` | Bugs/failures | ✅ Root cause before fix |
| `@code-reviewer` | Review phase | ✅ Write to handoff.md, then orchestrate-next |
| `@setup` | New project onboarding | ✅ Ask all questions before writing config |

### Claude Code (superpowers skills)

| Skill | When |
|-------|------|
| `brainstorming` | Before any design decision |
| `writing-plans` | After spec approved |
| `test-driven-development` | During implementation |
| `systematic-debugging` | Any bug or test failure |
| `verification-before-completion` | Before claiming done |
