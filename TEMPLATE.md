# AI Dev Starter — New Project Setup

5 steps to go from this template to your own AI-assisted project.

---

## Step 1: Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/ai-dev-starter.git my-new-project
cd my-new-project
make install
```

---

## Step 2: Configure environment

```bash
cp .env.example .env
# Edit .env — add your API keys and Telegram credentials
```

Required variables (add only what you need):

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude Code AI review, BaseAgent |
| `TELEGRAM_BOT_TOKEN` | Telegram notifications and bot |
| `TELEGRAM_CHAT_ID` | Where notifications are sent |
| `TELEGRAM_USER_ID` | Bot security: only this user ID is accepted |
| `MEDIUM_COOKIES` | Scraping bookmarks / member-only articles |

---

## Step 3: Run onboarding

```bash
make onboard
```

This asks 8 questions about your project and writes:
- `docs/PROJECT.md` — project spec
- Appends project context to `CLAUDE.md`
- Updates the GitHub Copilot instructions header
- Prints your first `make orchestrate-start` command

---

## Step 4: Clean example data

```bash
make template-clean
```

Removes example scraped articles, resets orchestration state, and clears human input.

---

## Step 5: Start your first task

```bash
make orchestrate-start TASK="your first task description"
```

The orchestrator creates `docs/orchestration/session.json` and `handoff.md`.
Open the handoff file in your AI tool (Copilot or Claude Code) and start working.

---

## Orchestration Quick Reference

```bash
make orchestrate-status          # show current session state
make orchestrate-next            # advance phase after review passes
make orchestrate-next FAILED=1   # advance after review fails (triggers FIXING)
make orchestrate-block REASON="need input on X"   # pause with reason
make orchestrate-resume          # resume blocked/paused session
make orchestrate-done            # mark session complete
```

Telegram commands (if bot is running): `/status`, `/pause`, `/stop`, `/resume`, `/skip`

---

## Parallel agent workspaces (optional)

```bash
make orchestrate-start TASK="your task" WORKTREE=1
```

Creates a sibling `../ai-dev-starter-agent2/` git worktree so a second agent
can work in parallel without conflicts.

---

## Quality gate

Run before every commit:

```bash
make check    # lint + typecheck + tests
```
