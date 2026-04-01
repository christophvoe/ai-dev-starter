# Getting Started — AI Dev Starter

Choose your path:

- **[Path A — Fresh repo](#path-a--fresh-repo)**: starting a new project from this template
- **[Path B — Embed in existing repo](#path-b--embed-in-existing-repo)**: drop tooling into a repo you already have

Both paths converge at the same daily workflow after setup.

---

## Path A — Fresh repo

### 1. Prerequisites

```bash
python --version       # 3.12+
uv --version           # 0.11+ (install: curl -Ls https://astral.sh/uv/install.sh | sh)
make --version         # GNU Make (WSL: already installed; Windows: use WSL or Git Bash)
```

VS Code extensions needed: **GitHub Copilot** + **Ruff** + **Mypy**

Claude Code (optional but recommended for complex work):
```bash
# Install Claude Code CLI, then inside it:
/plugin install superpowers@claude-plugins-official
```

### 2. Install

```bash
git clone https://github.com/christophvoe/ai-dev-starter
cd ai-dev-starter
make install        # creates .venv, installs deps, sets up pre-commit hooks
cp .env.example .env
make check          # verify everything works
```

### 3. Personalise

Run the interactive onboarding — it renames files, writes PROJECT.md, and configures
which tools you're using (Copilot / Claude Code / both):

```bash
make onboard
```

It asks 8 questions and writes config for you. Takes ~2 minutes.

### 4. (Optional) Set up Telegram

Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=...   # BotFather → /newbot
TELEGRAM_CHAT_ID=...     # send /start to your bot, check getUpdates
TELEGRAM_USER_ID=...     # your Telegram numeric ID
```

Test: `make notify MSG="Hello from ai-dev-starter"`

Start the bot: `make bot` (or deploy to Railway for always-on — see CHEATSHEET.md)

**You're ready.** Jump to [Daily Workflow](#the-daily-workflow).

---

## Path B — Embed in existing repo

Use this when you already have a project and want the AI tooling available without
committing it to your repo.

### 1. Clone into your existing repo

```bash
cd my-existing-repo
git clone https://github.com/christophvoe/ai-dev-starter
echo "ai-dev-starter/" >> .gitignore
echo "*.code-workspace" >> .gitignore
```

### 2. Install

```bash
cd ai-dev-starter
make install
cp .env.example .env
# Edit .env
```

### 3. Promote AI tooling into your repo

This copies the Copilot agents, instructions, and MCP config into your actual repo
so both AI tools can find them when you work there:

```bash
make promote TARGET="../"
```

What gets copied (skips files that already exist):
- `.github/agents/` — @orchestrator, @tdd, @debugger, @planner, @code-reviewer, @brainstorm
- `.github/copilot-instructions.md` — project context for every Copilot conversation
- `.github/instructions/` — code style, testing, security rules
- `.vscode/mcp.json` — context7 + sequential-thinking MCP servers
- `CLAUDE.md` — appends ai-dev-starter pointer section

### 4. Enable full AI indexing (critical)

Without this, `@workspace` can't see any ai-dev-starter code (it's gitignored).
Generate a multi-root workspace file:

```bash
make workspace TARGET="../"
code "../my-existing-repo.code-workspace"   # open this instead of the folder
```

Now `@workspace` indexes both repos. Open the `.code-workspace` file every time.

### 5. (Optional) Set up Telegram — same as Path A

**You're ready.** The daily workflow below works from both your repo and `ai-dev-starter/`.

---

## The Daily Workflow

### Step 1 — Scrape relevant knowledge (optional but powerful)

Before starting a task, scrape articles on the topic. They'll automatically appear in
`handoff.md` when you start orchestration, giving AI assistants real-world context:

```bash
cd ai-dev-starter   # or from repo root if embedded
make scrape-tag TAG="user authentication"
make scrape-tag TAG="fastapi jwt"
make discover TAGS="python,auth" CURATE=1   # LLM picks the best
```

Articles land in `data/knowledge/raw/medium/`. Query them directly:
```
@workspace summarize insights from data/knowledge/raw/medium/ on JWT auth patterns
```

### Step 2 — Start a session

```bash
make orchestrate-start TASK="add JWT auth to the API"
```

This creates `docs/orchestration/session.json` and writes `handoff.md` with:
- The task description pre-filled
- A `## Knowledge` section listing your recently scraped articles
- Empty slots for Changed Files, Output, Explanation, Uncertainty

### Step 3 — Plan (PLANNING phase)

Open `docs/orchestration/handoff.md`. The AI planning agent should:

1. Read the `## Knowledge` files listed there
2. Write the implementation plan back into handoff.md

**Copilot:**
```
@planner read docs/orchestration/handoff.md and the listed Knowledge files, then write a plan
```

or use the primary flow:
```
@orchestrator implement: [task] — read handoff.md knowledge files first
```

**Claude Code:**
```
/plan [task]
```
Claude Code reads CLAUDE.md which tells it to check the knowledge base.

Advance when done:
```bash
make orchestrate-next
```

### Step 4 — Implement (IMPLEMENTING phase)

```
@tdd implement the plan in handoff.md
```
or
```
/implement [from handoff.md]
```

Run quality gate before advancing:
```bash
make check
make orchestrate-next
```

### Step 5 — Review (REVIEWING phase)

```
@code-reviewer review the changes in handoff.md ## Changed Files
```

- Passes → `make orchestrate-next` → DONE
- Fails → `make orchestrate-next FAILED=1` → FIXING (other agent reviews)

### Step 6 — Done

```bash
make orchestrate-done
make orchestrate-explain   # send plain-English summary to Telegram
```

---

## Quick reference

### Copilot agents

| Agent | Use when | Example |
|-------|----------|---------|
| `@orchestrator` | Full feature end-to-end | `@orchestrator implement: add JWT auth` |
| `@brainstorm` | Approach unclear | `@brainstorm should we use OAuth or JWT?` |
| `@planner` | Plan first, approve before code | `@planner plan: add JWT auth` |
| `@tdd` | TDD only | `@tdd implement: add JWT auth` |
| `@debugger` | Bug, root cause unclear | `@debugger fix: 401 on POST /login` |
| `@code-reviewer` | Standalone review | `@code-reviewer review src/api/auth.py` |

### Claude Code commands

```
/implement [task]   implement + test + self-review
/plan [task]        plan only (read-only)
/review [file]      code review
/test [file]        generate tests
/check              ruff + mypy + pytest
```

### Orchestration commands

```bash
make orchestrate-start TASK="..."   # begin
make orchestrate-status             # where are we?
make orchestrate-next               # advance
make orchestrate-next FAILED=1      # review failed
make orchestrate-explain            # send summary to Telegram
make orchestrate-done               # complete
```

### Knowledge / scraping

```bash
make scrape-tag TAG="topic"         # scrape by topic
make discover TAGS="t1,t2" CURATE=1 # find + LLM-curate top articles
make summarize                      # digest of recent articles
```

---

## Common pitfalls

| Problem | Fix |
|---------|-----|
| `@workspace` can't see ai-dev-starter code | Open the `.code-workspace` file (run `make workspace TARGET="../"`) |
| Copilot agents not found | Run `make promote TARGET="../"` to copy them |
| context7 not working | Check `.vscode/mcp.json` exists (promote copies it) |
| AI ignores knowledge base | Check handoff.md has `## Knowledge` section; re-run `orchestrate-start` |
| Module not found errors | `PYTHONPATH=src` — run from inside `ai-dev-starter/` or use `uv run` |
| Pre-commit hook fails | Run `make format` then re-stage |
| Scraper 403 | Update `MEDIUM_COOKIES` in `.env` (cookies expire) |
| WSL path issues | Clone repo natively in WSL (`~/my-repo/`) rather than on `/mnt/c/` |

---

## WSL notes

`make`, `uv`, and all Python commands work natively in WSL — no admin rights needed.

- Clone your repo inside WSL (e.g., `~/ai-dev-starter`) for best performance
- If you must work on `/mnt/c/`, use `uv run python -m ...` directly instead of `make`
- The `.venv/Scripts/python.exe` path is Windows-only; WSL uses `.venv/bin/python`

---

## Next reading

- [docs/CHEATSHEET.md](CHEATSHEET.md) — all commands on one page
- [docs/EMBED-IN-EXISTING-REPO.md](EMBED-IN-EXISTING-REPO.md) — full embed guide with indexing details
- [docs/LLM-CONNECTIONS.md](LLM-CONNECTIONS.md) — API key options (Anthropic, Ollama, OpenRouter…)
