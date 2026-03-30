# Getting Started: AI Tools & Workflow Guide

> The practical guide to using GitHub Copilot + Claude Code effectively.
> Both tools share the same quality gates and project conventions.

---

## 1. Setup Checklist

```bash
python --version       # 3.12+
uv --version           # 0.11+
make --version         # GNU Make
make install           # venv + deps + pre-commit hooks
make check             # verify everything works (lint + typecheck + test)
```

Also need:
- VS Code with GitHub Copilot extension
- Claude Pro subscription ($20/mo) for Claude Code terminal
- Claude Code superpowers plugin: `/plugin install superpowers@claude-plugins-official`

Optional:
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env` for remote notifications
- `GITHUB_TOKEN` in `.env` for GitHub MCP (PRs, issues, code search)

---

## 2. Commands You'll Use Daily

### Quality (run before every commit)

| Command | What It Does |
|---------|-------------|
| `make check` | **THE command.** Lint + typecheck + test. |
| `make format` | Auto-fix formatting with ruff |
| `make lint` | Ruff linter only |
| `make typecheck` | Mypy type checker only |
| `make test` | Pytest only |

### Scraping & Discovery

| Command | What It Does |
|---------|-------------|
| `make scrape` | Scrape default coding list |
| `make scrape-list URL="..."` | Scrape any Medium list |
| `make scrape-tag TAG="ai-agents"` | Scrape by tag |
| `make discover` | Discover trending articles from RSS |
| `make discover TAGS="ai-agents,llm" KEYWORDS="agent,Claude"` | Filter discovery |
| `make discover CURATE=1` | LLM picks the best articles |
| `make discover-scrape TAGS="ai-agents,llm" CURATE=1` | Discover + curate + auto-scrape |

Add `OUTPUT="path"` to save elsewhere. Add `DATED=1` for date subfolders.

See [src/knowledge/README.md](../src/knowledge/README.md) for the full scraper guide.

### Telegram Notifications

| Command | What It Does |
|---------|-------------|
| `make notify MSG="Hello"` | Send a message to Telegram |
| `make bot` | Start interactive Telegram bot |

Bot commands: `/status`, `/scrape`, `/discover`, `/ask`, `/help`

---

## 3. GitHub Copilot (VS Code)

Open with `Ctrl+Shift+I`. Fast, visual, great for small-to-medium tasks.

### Chat Agents

| Agent | What It Does | Example |
|-------|-------------|---------|
| `@workspace` | Search and answer questions about your codebase | `@workspace How does the scraper handle 403 errors?` |
| `@planner` | Plan a feature (read-only, no edits) | `@planner I want to add a Streamlit dashboard` |
| `@orchestrator` | Implement + test + review in one pass | `@orchestrator Add --limit flag to the scraper CLI` |
| `@tdd` | TDD enforcement (Red-Green-Refactor) | `@tdd Add retry logic for 429 errors` |
| `@debugger` | Systematic debugging (root cause first) | `@debugger The scraper hangs on large lists` |
| `@code-reviewer` | Review code for quality and security | `@code-reviewer Review src/knowledge/article_curator.py` |
| `@Explore` | Deep read-only codebase exploration | `@Explore How does TrendDiscoverer score articles? (thorough)` |

### Inline Editing

| Action | Shortcut |
|--------|----------|
| Edit code in-place | `Ctrl+I` → type instruction |
| Accept suggestion | `Tab` |
| Next suggestion | `Alt+]` |
| Force suggestion | `Alt+\` |

### context7 — Live Library Docs

Add `use context7` to ANY prompt for up-to-date library documentation:

```
What is the feedparser entry structure? use context7
How do I use curl_cffi for TLS impersonation? use context7
```

### Knowledge Base Access

The filesystem MCP lets Copilot read your scraped articles:

```
@workspace Read data/knowledge/raw/medium/coding/ and summarize insights on AI coding setups
```

---

## 4. Claude Code (Terminal)

Start with `claude` in your terminal. Powerful for complex, multi-file work.

### Slash Commands

| Command | What It Does |
|---------|-------------|
| `/plan [task]` | Plan before coding (read-only) |
| `/implement [task]` | Implement + test + self-review |
| `/review [file]` | Code review |
| `/test [file]` | Generate tests |
| `/check` | Run full quality gate |
| `compact` | Compress context when agent gets slow |
| `clear` | Start fresh (new feature = new session) |

### Superpowers (Auto-Active)

Superpowers is a Claude Code plugin that enforces development workflows:

| Skill | What It Does |
|-------|-------------|
| **brainstorming** | Design before code — explores approaches, writes specs |
| **writing-plans** | Detailed task plans with 2-5 min bite-sized tasks |
| **subagent-driven-development** | Fresh subagent per task + two-stage review |
| **test-driven-development** | Red-Green-Refactor enforced — no code without failing test |
| **systematic-debugging** | Root cause investigation before fixes |
| **verification-before-completion** | Evidence before claims — run commands, read output |

These skills activate automatically based on what you ask Claude Code to do.
Install once: `/plugin install superpowers@claude-plugins-official`

---

## 5. When to Use Which Tool

| Scenario | Use | Why |
|----------|-----|-----|
| Quick fix (1-2 files) | Copilot `Ctrl+I` | Fastest for small edits |
| Autocomplete | Copilot (automatic) | Always-on while typing |
| Ask about codebase | Copilot `@workspace` | Fast indexed search |
| Plan a feature | Either: `@planner` or `/plan` | Both work well |
| End-to-end feature | Copilot `@orchestrator` | Single-pass implementation |
| Complex multi-file work | Claude Code `/implement` | Better reasoning + superpowers |
| TDD workflow | Either: `@tdd` or Claude Code (auto) | Both enforce Red-Green-Refactor |
| Code review | Either: `@code-reviewer` or `/review` | Both work well |
| Complex debugging | Either: `@debugger` or Claude Code | Both do root-cause-first |
| Library docs | Copilot `use context7` | Live doc lookup |
| Remote monitoring | Telegram bot | `/status`, `/scrape` from phone |

### The Key Rule

**Copilot** = fast, visual, great for small-to-medium tasks and autocomplete.
**Claude Code** = powerful, great for large multi-file changes and deep reasoning.

Use **both together**: one implements, the other reviews.

---

## 6. The Workflow (Agent Collaboration)

Both tools share the same repo, the same quality gates, and the same conventions.
The workflow uses git branches and GitHub PRs as the collaboration surface.

```
1. PLAN     → @planner or brainstorming (read-only analysis)
2. IMPLEMENT → @orchestrator or /implement (on a feature branch)
3. VERIFY   → make check (both tools run this)
4. REVIEW   → @code-reviewer or /review (cross-review the other tool's work)
5. COMMIT   → git push → GitHub PR
6. NOTIFY   → Telegram sends status update
```

### Example: Adding a New Feature

```bash
# 1. Plan it
# In Copilot: @planner "I want to add retry logic for 429 errors"
# Or Claude Code: brainstorming activates automatically

# 2. Create a branch
git checkout -b feat/retry-429

# 3. Implement (pick one tool)
# @tdd "Add retry with exponential backoff for HTTP 429 errors"
# Or in Claude Code: /implement "Add retry with exponential backoff for HTTP 429"

# 4. Verify
make check

# 5. Cross-review (use the OTHER tool)
# @code-reviewer "Review the retry logic on this branch"
# Or in Claude Code: /review src/knowledge/medium_scraper.py

# 6. Push and notify
git push -u origin feat/retry-429
make notify MSG="feat/retry-429 ready for review"
```

### Parallel Agents (Advanced)

Use git worktrees to run both agents simultaneously:

```bash
git worktree add ../agent-copilot -b feat/copilot-task
git worktree add ../agent-claude -b feat/claude-task
```

One agent implements, the other reviews the branch via PR.
See [WORKTREES.md](WORKTREES.md) for details.

---

## 7. MCP Servers

These extend your AI tools automatically:

| Server | What It Does | How to Use |
|--------|-------------|------------|
| **context7** | Live library docs | Add `use context7` to any prompt |
| **sequential-thinking** | Step-by-step reasoning | Auto for complex decisions |
| **filesystem** | Read/write files | Auto — agents use it for file ops |
| **github** | PRs, issues, code search | Needs `GITHUB_TOKEN` in `.env` |

---

## 8. Context Management (Critical)

Agents get confused when context fills up. Keep it clean:

- **One feature per session** — don't mix unrelated work
- **Start fresh** for new features (`clear` in Claude Code, new chat in Copilot)
- **Compact** when things get slow (`compact` in Claude Code)
- **Be specific** — "Add retry logic for 429 errors" beats "fix the scraper"

---

## 9. Common Pitfalls

| Problem | Solution |
|---------|----------|
| Agent writes wrong code | Be more specific. Reference exact files and functions. |
| Context filling up | Run `compact`. Start new session for new features. |
| Tests failing | Run `uv run pytest tests/test_file.py::test_name -v` for details. |
| Lint/type errors after edit | Run `make format`, then fix mypy errors manually. |
| Agent ignores conventions | Check CLAUDE.md and copilot-instructions.md are up to date. |
| MCP not connecting | Restart VS Code. Check `.vscode/mcp.json`. |
| Scraper 403 errors | Update `MEDIUM_COOKIES` in `.env` (cookies expire). |
| Superpowers not working | Run `/plugin install superpowers@claude-plugins-official` in Claude Code. |

---

## 10. Next Steps

1. **Set up** Telegram notifications (see [ACTION-PLAN.md](ACTION-PLAN.md) Phase 2c)
2. **Try** the workflow: plan → implement → verify → review → push
3. **Cross-review**: implement with one tool, review with the other
4. **Explore** parallel agents with git worktrees (see [WORKTREES.md](WORKTREES.md))
