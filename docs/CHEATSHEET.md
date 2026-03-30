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

Full workflow order (use what you need, skip what you don't):
```
@brainstorm  "should we use RSS or scrape HTML for dev.to?"   ← explore options first
@planner     plan: add dev.to scraper                         ← concrete plan, no code
@tdd         implement: add dev.to scraper                    ← TDD implementation
@orchestrator implement: add --verbose flag to CLI            ← full plan+implement+test+review
@debugger    fix: TypeError in article_curator.py line 45     ← root cause first
@code-reviewer review src/knowledge/medium_scraper.py         ← structured review
@setup       (interactive onboarding for new projects)
```

Typical flow for a real feature:
```
@brainstorm → @planner → make orchestrate-start → @tdd → @code-reviewer
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

### context7 — live library docs (works in BOTH tools)

`context7` is an MCP server configured in `.vscode/mcp.json`. Both Claude Code and Copilot
share the same MCP config, so `use context7` works in both.

Add to any prompt — Claude Code or Copilot Chat:

```text
"How do I paginate feedparser results? use context7"
"Show me the python-telegram-bot CommandHandler API. use context7"
"What changed in anthropic SDK 0.49? use context7"
```

It fetches current docs at query time — not training data. Use it whenever you're
working with a specific library version or something that changes frequently.

### Other tips

- Paste the exact error message, not a summary ("TypeError: …" not "it crashed")
- Reference the file: "in src/knowledge/medium_scraper.py, the TrendDiscoverer class…"
- State what you've already tried
- For Claude Code: `sequential-thinking` MCP is active for complex multi-step reasoning
  (automatic, no keyword needed)
