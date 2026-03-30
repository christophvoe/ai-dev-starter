# Quick Reference — AI Dev Starter

## When to use what

| Task complexity | Tool |
|----------------|------|
| Question / explanation / typo fix | Chat directly in Claude or Copilot |
| One small change (1–2 files) | `/implement` (Claude) or `@tdd` (Copilot) |
| Real feature / refactor / new module | `make orchestrate-start TASK="..."` |

---

## Quick commands (no orchestration needed)

### Claude Code slash commands
```
/implement add a --verbose flag to the CLI
/plan      refactor MediumScraper into smaller classes
/review    src/knowledge/medium_scraper.py
/test      src/agents/reviewer.py
/check     (runs ruff + mypy + pytest)
```

### GitHub Copilot agent commands (Copilot Chat)
```
@orchestrator implement: add --verbose flag to CLI
@tdd         write tests for the notify module
@planner     plan: refactor MediumScraper
@debugger    fix: TypeError in article_curator.py line 45
@code-reviewer review src/knowledge/medium_scraper.py
```

### Useful prompts for chat (no command needed)
```
"Explain how TrendDiscoverer scores articles"
"What does session.json look like after REVIEWING fails?"
"Show me all functions in src/agents/orchestrator.py"
"Why is my test failing? [paste error]"
"Rewrite this function to be under 50 lines: [paste]"
```

---

## Knowledge base

```bash
make scrape-tag TAG="ai-agents"              # scrape by topic
make scrape-list URL="https://medium.com/…"  # scrape your saved list
make discover TAGS="llm,python"              # find trending articles
make discover TAGS="llm" CURATE=1           # LLM picks the best ones
make discover-scrape TAGS="llm" CURATE=1    # discover + auto-scrape top 10
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
**Fail flow**: `REVIEWING → FIXING → REVIEWING` (other agent reviews)
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
/discover [tags]  find trending articles
/review [branch]  AI code review
/check     run quality gate
/ask <question>   search knowledge base
```

Any other text you send → saved to `human_input.md` for the next agent to pick up.

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

## Context tips for better AI answers

Add to any Claude Code or Copilot prompt:

- `use context7` → pulls live library docs (e.g., "how do I use feedparser? use context7")
- Paste the exact error message, not a summary
- Reference the file: "in src/knowledge/medium_scraper.py, the TrendDiscoverer class…"
- State what you've already tried
