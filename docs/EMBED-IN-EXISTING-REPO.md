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
git clone https://github.com/christophvoeltzke/ai-dev-starter
```

### 2. Gitignore it

Add to your repo's `.gitignore`:

```
ai-dev-starter/
```

This keeps the scraper tooling out of your commits. It's a separate project.

### 3. Install dependencies

```bash
cd ai-dev-starter
make install    # creates .venv, installs everything
cp .env.example .env
# Edit .env — add MEDIUM_COOKIES for scraping, optional API keys
```

### 4. Run any command from the subfolder

All `make` commands and `uv run python -m ...` commands work from inside `ai-dev-starter/`:

```bash
cd ai-dev-starter
make scrape-tag TAG="python"
make bot
make orchestrate-start TASK="add user auth to my API"
```

**WSL users**: `make` and `uv run` both work from WSL natively. No admin rights needed.
If you cloned your repo inside WSL (e.g., `~/my-repo/`), run commands from there.
If the repo is on `/mnt/c/`, use the Windows `.venv/Scripts/` path or run from PowerShell.

---

## Promoting AI tooling into your repo

The `promote` command copies the Copilot agents and instructions into your actual repo's
`.github/` folder — so Copilot Chat can find them when you're working in your repo.

```bash
cd ai-dev-starter
make promote TARGET="../"          # promote into parent repo
make promote TARGET="../../other"  # promote into a sibling repo
```

Or with `uv run` directly:

```bash
uv run python -m agents.onboarding --promote-to ../
```

### What gets copied

| Source (ai-dev-starter) | Destination (your repo) | Behavior |
|-------------------------|------------------------|----------|
| `.github/agents/*.agent.md` | `.github/agents/` | Copy — skip if file exists |
| `.github/instructions/` | `.github/instructions/` | Copy — skip if file exists |
| `.github/prompts/` | `.github/prompts/` | Copy — skip if file exists |
| `.github/copilot-instructions.md` | `.github/copilot-instructions.md` | Copy — skip if exists |
| (nothing) | `CLAUDE.md` | Append ai-dev-starter section (idempotent) |

**Nothing is overwritten.** If a file already exists in your repo, promote skips it and
prints `Skipped (exists): ...`. You stay in control.

### After promoting

In Copilot Chat (your repo):

```
@orchestrator implement: add user auth endpoint
@tdd         implement: write tests for auth service
@debugger    fix: 401 on POST /login
```

These work because the `.agent.md` files are now in your repo's `.github/agents/`.

---

## Architecture

```
my-existing-repo/
├── .github/
│   ├── agents/          ← promoted from ai-dev-starter (Copilot sees these)
│   │   ├── orchestrator.agent.md
│   │   ├── tdd.agent.md
│   │   └── ...
│   └── copilot-instructions.md   ← promoted (or your existing one)
├── CLAUDE.md            ← ai-dev-starter section appended
├── src/
│   └── ...your code...
│
└── ai-dev-starter/      ← gitignored subfolder
    ├── .venv/
    ├── src/agents/      ← orchestrator, reviewer, onboarding
    ├── src/knowledge/   ← medium scraper
    ├── src/bot/         ← telegram bot + notify
    ├── data/knowledge/  ← scraped articles (stays here, gitignored)
    ├── docs/orchestration/   ← session.json, handoff.md
    └── Makefile
```

---

## Keeping it updated

`ai-dev-starter` is a normal git repo inside your folder:

```bash
cd ai-dev-starter
git pull        # get latest improvements
make sync       # sync any new dependencies
```

Re-run `make promote TARGET="../"` after an update if you want the latest agent files
in your repo. Existing files in your repo are never overwritten — only new files get
copied.

---

## What about the knowledge base?

Scraped articles land in `ai-dev-starter/data/knowledge/raw/medium/` (gitignored).

You can point Claude Code or Copilot at them from your repo:

```
Read all .md files in ai-dev-starter/data/knowledge/raw/medium/ and summarize insights on auth patterns
```

Or scrape directly into your repo:

```bash
cd ai-dev-starter
make scrape-tag TAG="python" OUTPUT="../docs/research"
```

---

## Telegram bot

The bot runs from inside `ai-dev-starter/`:

```bash
cd ai-dev-starter
make bot
```

It reads `.env` in `ai-dev-starter/` — set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`TELEGRAM_USER_ID` there.

For always-on deployment (so it keeps running when you close the laptop), see
[docs/RAILWAY-DEPLOY.md](RAILWAY-DEPLOY.md) (3 env vars + Railway free tier).
