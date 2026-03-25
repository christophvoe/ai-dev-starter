# AI Dev Starter

A Python starter template with a Medium knowledge scraper, multi-LLM agent, and n8n automation.

---

## Quick Start

### 1. Install uv (one-time)

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install dependencies

```bash
make install          # creates .venv, installs everything, sets up pre-commit hooks
```

### 3. Try it — scrape some articles (no API keys needed!)

```bash
make scrape-tag TAG="ai-agents"
```

That's it. Articles are saved as Markdown in `data/knowledge/raw/medium/`.

---

## Medium Scraper

The scraper uses **plain HTTP + RSS** to fetch articles. **No AI, no API keys needed** for scraping.
It only needs cookies for member-only / private bookmark access.

### Commands

```bash
make scrape                       # scrape your coding list (default)
make scrape-tag TAG="ai-agents"   # scrape a public tag (no cookies needed)
make scrape-tag TAG="python"
make scrape-article URL="https://medium.com/@author/title-abc123"
make scrape-list URL="https://medium.com/@user/list/name-abc123"
make scrape-bookmarks             # scrape private bookmarks (needs cookies)
make summarize                    # show digest of recent articles
```

### Save to a different directory / repo

Every command supports `OUTPUT=path/to/dir` to save articles outside this repo:

```bash
make scrape OUTPUT=../my-knowledge-repo/articles
make scrape-tag TAG="python" OUTPUT=C:/Users/Me/other-project/data
```

### Save into dated subfolders

Add `DATED=1` to save into a `YYYY-MM-DD` subfolder (keeps each scrape run separate):

```bash
make scrape DATED=1                   # saves to data/.../2026-03-25/
make scrape DATED=1 OUTPUT=../other   # combines both flags
```

Or use the raw CLI directly:

```bash
uv run python -m knowledge.medium_scraper --tag "ai-agents" --output ../other-repo/articles --dated
```

### Adding Medium Cookies (for bookmarks / member-only articles)

1. Open Chrome/Edge, go to https://medium.com — make sure you are **logged in**
2. Press **F12** -> **Application** tab -> **Cookies** -> `https://medium.com`
3. Copy these cookie values from the table:

| Cookie | Required | Notes |
|--------|----------|-------|
| `sid` | Yes | Session ID, valid for months |
| `uid` | Yes | User ID, never changes |
| `xsrf` | Recommended | XSRF token for API calls |
| `cf_clearance` | Recommended | Cloudflare bypass token |

4. Set in `.env`:

```
MEDIUM_COOKIES=sid=YOUR_SID; uid=YOUR_UID; xsrf=YOUR_XSRF; cf_clearance=YOUR_CF
```

5. Test it:

```bash
make scrape-bookmarks
```

---

## .env Configuration

```bash
cp .env.example .env
```

**Only `MEDIUM_COOKIES` is needed to start scraping.** Everything else is optional:

| Variable | Needed for | Required? |
|----------|-----------|-----------|
| `MEDIUM_COOKIES` | Bookmarks + member-only articles | Only for `--bookmarks` |
| `ANTHROPIC_API_KEY` | BaseAgent (LLM chat) | Only if using BaseAgent |
| `OPENAI_API_KEY` | BaseAgent with GPT models | Only if using GPT |
| `TELEGRAM_BOT_TOKEN` | n8n Telegram notifications | Optional |
| `GITHUB_TOKEN` | GitHub MCP in Copilot | Optional |

---

## Using Your Knowledge Base

Once you have articles scraped, ask Copilot or Claude Code:

```
Read all .md files in data/knowledge/raw/medium/ and summarize insights on [topic]
What do the saved articles say about multi-agent systems?
```

Add `use context7` to any prompt for live library documentation.

---

## n8n Workflows (optional)

n8n adds a **visual UI** where you can easily switch the output directory and source list
without touching the terminal. Both workflows are manual trigger (click to run).

```bash
npx n8n start    # opens at http://localhost:5678
```

Then: **Workflows** menu -> **Import from File** -> select a JSON from `n8n_workflows/`:

| Workflow | What it does |
|----------|-------------|
| **00 -- Scrape Medium List** | Scrape articles, show results |
| **01 -- Scrape + Summarize** | Scrape + print preview of each article |

### What n8n gives you

Open the **Configure** node and change these 4 variables at the top:

```js
const OUTPUT_DIR = 'C:\\Users\\Voelt\\other-repo\\articles';  // save to any folder/repo
const MODE       = 'list';                                     // list / tag / article / feed / bookmarks
const SOURCE     = 'https://medium.com/@user/list/name-123';  // URL or tag name
const MAX        = 20;                                         // max articles
```

This is the n8n value-add: **visually switch output repo and source list** without editing any files.

---

## Code Quality

```bash
make check        # lint + typecheck + test (all at once)
make lint         # ruff only
make typecheck    # mypy only
make test         # pytest only
make test-cov     # pytest with coverage
make format       # auto-format with ruff
make help         # show all available commands
```

---

## Project Structure

```
src/
  agents/base.py            -- BaseAgent (Anthropic + OpenAI)
  knowledge/medium_scraper.py -- Medium article scraper (HTTP/RSS, no AI)
  bot/telegram_bot.py       -- optional Telegram bot
  utils/logger_config.py    -- logging setup

data/knowledge/raw/medium/  -- scraped article Markdown files
n8n_workflows/              -- 2 n8n workflow JSONs
tests/                      -- test suite
```

---

## MCP Servers

Configured in `.vscode/mcp.json` — extend Copilot and Claude Code.

| Server | Purpose | Setup |
|--------|---------|-------|
| **filesystem** | Read/write project files | Auto |
| **sequential-thinking** | Step-by-step reasoning | Auto |
| **context7** | Live library docs | Auto (free) |
| **github** | Commits, PRs, issues | `GITHUB_TOKEN` in `.env` |
