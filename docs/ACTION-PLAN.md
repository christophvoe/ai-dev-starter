# Action Plan: AI Dev Starter

> Sequenced phases with exact commands. Updated for superpowers + agent collaboration.
> For tools guide, see [GETTING-STARTED.md](GETTING-STARTED.md).

---

## Phase 0: Verify Setup

```bash
python --version       # 3.12+
uv --version           # 0.11+
make check             # lint + typecheck + test
```

- [x] Python 3.12+, uv, GNU Make installed
- [x] `make check` passes (60/60 tests, ruff clean, mypy clean)
- [x] VS Code + Copilot extension active
- [x] Claude Code with superpowers plugin installed

---

## Phase 1: Knowledge Base (Done)

```bash
make scrape-list URL="https://medium.com/@voeltzke.christoph/list/coding-6c7978acb372" OUTPUT="data/knowledge/raw/medium/coding"
make discover TAGS="ai-agents,llm" KEYWORDS="agent,Claude,trading" CURATE=1
```

- [x] 4 lists scraped (28 quality articles)
- [x] Trending discovery working
- [x] LLM curation tested (`CURATE=1`)

---

## Phase 2: Agent Collaboration Setup (Current)

> Goal: Copilot and Claude Code work semi-autonomously, challenge each other.

### 2a. Superpowers (Claude Code)

```bash
# In Claude Code terminal:
/plugin install superpowers@claude-plugins-official
```

- [x] Superpowers installed (brainstorming, TDD, subagent-driven-dev, debugging)
- [x] CLAUDE.md references superpowers skills
- [x] `.claude/commands/` complement superpowers with project-specific context

### 2b. Copilot Agents (Mirror superpowers)

- [x] `@tdd` — TDD enforcement (Red-Green-Refactor)
- [x] `@debugger` — Systematic debugging (root cause first)
- [x] `@orchestrator` — End-to-end: plan + implement + test + review
- [x] `@code-reviewer` — Code review with project standards
- [x] `@planner` — Plan before implementing (read-only)
- [x] `workflow.instructions.md` — Verification-before-completion

### 2c. Telegram Notifications

```bash
# Set up in .env:
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_USER_ID=your-user-id

# Test:
make notify MSG="Hello from AI Dev Starter!"
```

- [x] `src/bot/notify.py` — standalone notifications (send_message, send_scrape_report)
- [x] Telegram bot: /status, /scrape, /discover, /ask, /help
- [x] 16 tests for notify module

### 2d. Agent Workflow

The two AI tools collaborate through git and GitHub:

```
Copilot (VS Code)          Claude Code (Terminal)
     │                            │
     ├── @planner → plan          │
     │                            ├── brainstorming → spec
     ├── @tdd → implement         │
     │                            ├── subagent-driven → implement
     ├── @code-reviewer            │
     │                            ├── requesting-code-review
     └── git push                 └── git push
              │                          │
              └──── GitHub PR ───────────┘
                       │
              Telegram notification
```

- [ ] Both agents share the same repo and quality gates
- [ ] GitHub PRs as the review surface
- [ ] Telegram bot sends status updates

---

## Phase 3: Remote Monitoring & Control

> Goal: Monitor and control both agents from Telegram on your phone.

```bash
# Start the bot (or run via n8n)
uv run python -m bot.telegram_bot
```

- [ ] Telegram `/status` shows project health
- [ ] Telegram `/scrape` triggers knowledge collection
- [ ] Telegram `/discover` finds trending content
- [ ] GitHub notifications forwarded to Telegram
- [ ] Accept/reject agent PRs from Telegram

---

## Phase 4: Productization (Future)

- [ ] Template branch cleaned for sale
- [ ] LinkedIn content from knowledge base
- [ ] n8n daily automation active

---

## Daily Workflow

```bash
# Morning (5 min from phone)
# Telegram: /discover ai-agents
# Telegram: /scrape

# Work session (use either tool)
# Copilot: @orchestrator "Implement [feature]"
# Claude: "brainstorm [feature]" → plan → implement

# Evening (automated)
make check
git push
# → Telegram notification with results
```
