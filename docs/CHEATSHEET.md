# Quick Reference — AI Dev Starter

## When to use what

| Task | Tool |
|------|------|
| Quick question / explanation / typo fix | Chat directly in Claude or Copilot |
| One small change (1–2 files) | `/implement` (Claude) or `@tdd` (Copilot) |
| Real feature / refactor / new module | `make orchestrate-start TASK="..."` |
| Debug a specific error | `@debugger` (Copilot) or `/check` (Claude) |
| Plan before coding | `@brainstorm` → `@planner` (Copilot) or `/plan` (Claude) |
| Code review | `make review` or `@code-reviewer` |

---

## GitHub Copilot Chat agents

### Primary flow — @orchestrator does everything

```
@orchestrator implement: add --verbose flag to CLI
```

This runs: brainstorm (if needed) → plan → implement → test → review in one pass.
**Use this for 90% of tasks.** The other agents below are escape hatches.

### Specialist agents (use only when you hit the specific situation)

| Agent | When to use | Example |
|-------|-------------|---------|
| `@brainstorm` | Approach is genuinely unclear — explore options first | `@brainstorm should we use RSS or scrape HTML for dev.to?` |
| `@planner` | You know what to build, want to approve plan before code | `@planner plan: add dev.to scraper` |
| `@tdd` | TDD only, no full orchestration | `@tdd implement: add dev.to scraper` |
| `@debugger` | Bug with unclear root cause | `@debugger fix: TypeError in article_curator.py line 45` |
| `@code-reviewer` | Standalone review of a file or feature | `@code-reviewer review src/knowledge/medium_scraper.py` |
| `@setup` | Interactive onboarding for a new project | `@setup` |

### Copilot Chat tips

```
@workspace how does TrendDiscoverer score articles?
@workspace what does session.json look like after REVIEWING fails?
@workspace show all functions in src/agents/orchestrator.py
@workspace explain the orchestration phase flow
```

`@workspace` searches your entire codebase. If you have `ai-dev-starter/` as an embedded
subfolder, open the `.code-workspace` file (see `make workspace`) so Copilot indexes both repos.

**Add `use context7` to any prompt for live library docs:**

```
How do I paginate feedparser results? use context7
Show me the python-telegram-bot CommandHandler API. use context7
What changed in anthropic SDK 0.49? use context7
```

context7 fetches current docs at query time — not training data. Use whenever you're
working with a specific library version.

---

## Claude Code slash commands

```
/implement add a --verbose flag to the CLI
/plan      refactor MediumScraper into smaller classes
/review    src/knowledge/medium_scraper.py
/test      src/agents/reviewer.py
/check     (runs ruff + mypy + pytest)
```

Claude Code also has **superpowers** workflows that activate automatically:

| Workflow | What triggers it | What it does |
|----------|-----------------|--------------|
| `brainstorming` | Before planning | Explores 2–3 approaches, picks one |
| `writing-plans` | Before implementing | Detailed task-by-task plan with TDD |
| `test-driven-development` | While implementing | Red→Green→Refactor enforced |
| `systematic-debugging` | On a bug | Root cause first, no guessing |
| `verification-before-completion` | Before claiming done | Runs commands, reads output |

---

## Quality gate

```bash
make check        # ruff + mypy + pytest (run before every handoff)
make lint         # ruff only
make typecheck    # mypy only
make test         # pytest only
make format       # auto-fix formatting
```

---

## Knowledge base (scraping)

```bash
make scrape-tag TAG="ai-agents"              # scrape by topic
make scrape-tag TAG="python" OUTPUT="../docs/research"  # save into your repo
make scrape-list URL="https://medium.com/…"  # scrape your saved list
make discover TAGS="llm,python"              # find trending articles
make discover TAGS="llm" CURATE=1            # LLM picks the best ones
make discover-scrape TAGS="llm" CURATE=1     # discover + auto-scrape top 10
make summarize                               # show digest of saved articles
```

---

## Orchestration (for real features)

```bash
make orchestrate-start TASK="add X"   # begin — creates session.json + handoff.md
make orchestrate-status               # where are we?
make orchestrate-next                 # advance phase after work is done
make orchestrate-next FAILED=1        # advance after review fails (→ FIXING)
make orchestrate-explain              # send Explanation to Telegram
make orchestrate-block REASON="…"     # pause + alert (need human input)
make orchestrate-resume               # clear block, continue
make orchestrate-done                 # mark complete
make orchestrate-check-failed         # call after make check fails
```

**Phase flow**: `PLANNING → IMPLEMENTING → REVIEWING → DONE`
**Fail flow**: `REVIEWING → FIXING → REVIEWING` (opposite agent reviews)
**Auto-block**: 3 fix cycles, 2 failed quality gates, or uncertainty flag

---

## Telegram bot commands (while `make bot` is running)

```
/status    session state
/pause     pause session
/stop      stop session
/resume    resume blocked/paused
/skip      skip current phase
/scrape    trigger Medium scrape
/discover [tags]    find trending articles
/review [branch]    AI code review
/check     run quality gate
/ask <question>     search knowledge base
```

Any other text you send → saved to `human_input.md` for the next agent to pick up.

---

## Embedding in an existing repo

Use `ai-dev-starter` as a gitignored subfolder in any project — full scraping,
Telegram, and orchestration without cluttering your commits.

```bash
cd my-existing-repo
git clone https://github.com/christophvoe/ai-dev-starter
echo "ai-dev-starter/" >> .gitignore

cd ai-dev-starter
make install
make promote TARGET="../"    # copy agents + copilot-instructions into your repo
make workspace TARGET="../"  # generate multi-root .code-workspace for Copilot indexing

# Open the workspace file so @workspace sees both repos:
code "../my-existing-repo.code-workspace"
```

See [docs/EMBED-IN-EXISTING-REPO.md](EMBED-IN-EXISTING-REPO.md) for the full guide.

---

## Onboarding a new project

```bash
make onboard          # interactive setup (renames files, writes PROJECT.md, etc.)
make template-clean   # reset repo to clean template state
```

---

## LLM connections

Scraping and Telegram work with **zero API keys**. For curation + AI review:

| Provider | Cost | Command |
|----------|------|---------|
| Anthropic (Claude) | ~$0.01/run | `ANTHROPIC_API_KEY=sk-ant-...` |
| OpenAI (GPT) | ~$0.01/run | `OPENAI_API_KEY=sk-...` |
| Ollama (local) | Free | `ollama pull llama3.2` |
| OpenRouter | Free tier | `OPENROUTER_API_KEY=sk-or-...` |
| GitHub Models | Free (Copilot) | `GITHUB_TOKEN=ghp_...` |

See [docs/LLM-CONNECTIONS.md](LLM-CONNECTIONS.md) for setup instructions.

---

## Always-on Telegram bot (Railway)

Deploy to Railway for a bot that keeps running when the laptop is closed:

1. Push to GitHub
2. Create project at railway.app → Deploy from GitHub repo
3. Set env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_USER_ID`
4. Set start command: `uv run python -m bot.telegram_bot`

Free tier covers a personal bot easily.
