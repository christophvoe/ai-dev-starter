# Using AI Dev Starter Inside an Existing Repo

You don't have to start from this template. You can drop `ai-dev-starter` as a
**gitignored subfolder** inside any existing project and get full access to:

- Medium scraping + article discovery
- Telegram notifications and bot
- Multi-agent orchestration (PLANNING → IMPLEMENTING → REVIEWING)
- GitHub Copilot agents (@orchestrator, @tdd, @debugger, @planner, @code-reviewer)
- Claude Code slash commands (/implement, /review, /test, /check)

---

## Setup (5 minutes)

### 1. Clone ai-dev-starter into your existing repo

```bash
cd my-existing-repo
git clone https://github.com/christophvoe/ai-dev-starter
```

### 2. Gitignore it

Add to your repo's `.gitignore`:

```
ai-dev-starter/
*.code-workspace
```

This keeps the scraper tooling and workspace file out of your commits.

### 3. Install dependencies

```bash
cd ai-dev-starter
make install    # creates .venv, installs everything
cp .env.example .env
# Edit .env — add MEDIUM_COOKIES for scraping, optional API keys
```

### 4. Promote AI tooling into your repo

This copies Copilot agents and instructions so they're visible when you work in your repo:

```bash
make promote TARGET="../"
```

### 5. Enable full AI indexing with a workspace file

**This is the critical step.** Without it, `@workspace` in Copilot Chat and Claude Code
are blind to everything inside `ai-dev-starter/` (because it's gitignored). The workspace
file fixes this by telling VS Code to index both folders together:

```bash
make workspace TARGET="../"
```

Then open the generated `.code-workspace` file in VS Code:

```bash
code "../my-existing-repo.code-workspace"
```

From now on, open your project using this workspace file instead of the folder directly.
Both codebases are indexed — your code AND the ai-dev-starter tooling.

---

## Why the workspace file matters

Copilot Chat's `@workspace` and Claude Code both index only what VS Code considers the
"workspace". If `ai-dev-starter/` is gitignored, it's invisible — the AI assistants
can't answer "how does the scraper work?" or "what does orchestrator.py do?".

The `.code-workspace` file adds both folders as roots:

```json
{
  "folders": [
    { "path": ".", "name": "my-existing-repo" },
    { "path": "ai-dev-starter", "name": "AI Dev Starter (tooling)" }
  ]
}
```

With this open:

```
@workspace how does the Medium scraper handle Cloudflare bypass?
@workspace what does make orchestrate-start do step by step?
@workspace show me the handoff.md format
```

All of these now work — Copilot can read across both codebases.

---

## What each command does

- **`make promote TARGET="../"`** — Copies `.github/agents/`, instructions, and copilot-instructions.md into your repo. Skips existing files.
- **`make workspace TARGET="../"`** — Generates a `.code-workspace` file for multi-root indexing.

Run both once after the initial clone. Re-run `promote` after pulling updates to get new agent files.

---

## Full picture after setup

```
my-existing-repo/
├── .github/
│   ├── agents/                   ← promoted: @orchestrator, @tdd, @debugger, etc.
│   │   ├── orchestrator.agent.md
│   │   ├── tdd.agent.md
│   │   └── ...
│   └── copilot-instructions.md   ← promoted (project context for Copilot)
├── CLAUDE.md                     ← ai-dev-starter section appended
├── my-existing-repo.code-workspace  ← multi-root workspace (gitignored)
├── src/
│   └── ...your code...
│
└── ai-dev-starter/               ← gitignored subfolder
    ├── .venv/
    ├── src/agents/               ← orchestrator, reviewer, onboarding
    ├── src/knowledge/            ← medium scraper
    ├── src/bot/                  ← telegram bot + notify
    ├── data/knowledge/           ← scraped articles (stays here, gitignored)
    ├── docs/orchestration/       ← session.json, handoff.md
    └── Makefile
```

---

## Using the AI assistants after setup

### Copilot Chat (in your repo)

The promoted agents are fully functional:

```
@orchestrator implement: add user auth endpoint
@tdd          implement: write tests for auth service
@debugger     fix: 401 on POST /login
@code-reviewer review src/api/auth.py
```

And because the workspace file is open, `@workspace` can also answer questions
about the tooling:

```
@workspace how do I scrape articles tagged "python"?
@workspace what Telegram commands does the bot support?
@workspace explain the orchestration phase flow
```

### Claude Code (from your repo root or ai-dev-starter/)

Claude Code reads `CLAUDE.md` — it now has an `## AI Dev Starter tooling` section
appended by `promote`, pointing it to the subfolder. You can run Claude Code from
either directory:

```bash
# From your repo root — Claude sees your code + the CLAUDE.md pointer
claude

# From ai-dev-starter/ — full orchestration, scraping, bot commands
cd ai-dev-starter
claude
make orchestrate-start TASK="add auth to the parent repo"
```

### Adding more context for Copilot

The promoted `copilot-instructions.md` gives Copilot your project context. Edit it
to describe your repo — Copilot reads it automatically on every conversation:

```markdown
# MyProject — GitHub Copilot Context

This is a FastAPI service for managing user subscriptions.
Stack: Python 3.12, FastAPI, PostgreSQL, SQLAlchemy.

Key paths:
- src/api/      — FastAPI routers
- src/models/   — SQLAlchemy models
- src/services/ — business logic

AI Dev Starter tooling lives in ai-dev-starter/ (gitignored).
Use @workspace to ask about the scraper or orchestration system.
```

---

## Running commands

All `make` commands run from inside `ai-dev-starter/`:

```bash
cd ai-dev-starter

make scrape-tag TAG="python"                        # scrape articles
make scrape-tag TAG="python" OUTPUT="../docs/research"  # scrape into your repo
make orchestrate-start TASK="add auth endpoint"     # start orchestration
make bot                                             # Telegram bot
make review BRANCH="feat/auth"                      # AI code review
```

**WSL users**: `make` and `uv run` both work from WSL natively. No admin rights needed.

---

## Keeping it updated

```bash
cd ai-dev-starter
git pull        # get latest improvements
make sync       # sync any new dependencies

# Re-run promote to copy any new agent files (existing files are never overwritten)
make promote TARGET="../"
```

---

## Telegram bot

The bot runs from inside `ai-dev-starter/` and reads `.env` there:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_USER_ID=...
```

```bash
cd ai-dev-starter
make bot
```

For always-on deployment see [docs/RAILWAY-DEPLOY.md](RAILWAY-DEPLOY.md) (3 env vars + Railway free tier).

---

## LLM connections

Medium scraping and Telegram work with zero API keys. For LLM-powered features
(article curation, AI code review), see [docs/LLM-CONNECTIONS.md](LLM-CONNECTIONS.md)
for options: Anthropic, OpenAI, Ollama (free/offline), OpenRouter, GitHub Models.
