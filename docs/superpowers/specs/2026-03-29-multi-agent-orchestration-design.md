# Multi-Agent Orchestration Design

**Date**: 2026-03-29
**Status**: Approved
**Scope**: GitHub Copilot ↔ Claude Code orchestration with loop prevention, Telegram control, and template packaging

---

## 1. Goal

Create an orchestrated development workflow where GitHub Copilot and Claude Code collaborate on tasks through a shared state machine. Humans start the workflow and can intervene at any point. Agents hand off to each other at meaningful milestones (not on every file edit). Loop prevention ensures agents never run indefinitely. Telegram is the human control plane.

The entire setup lives in this repo and can be copied to start any new project with one command.

---

## 2. Architecture Overview

```
Human (VS Code / Telegram)
        │
        ▼
┌───────────────────────────────────────────────┐
│           Orchestration Layer                 │
│  docs/orchestration/session.json  (state)     │
│  docs/orchestration/handoff.md    (content)   │
│  docs/orchestration/human_input.md (input)    │
│  src/agents/orchestrator.py       (logic)     │
│  Makefile targets                             │
└───────────────┬───────────────────────────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
GitHub Copilot      Claude Code
(VS Code chat)      (Terminal)
       │                 │
       └────────┬────────┘
                ▼
       GitHub Actions (CI gates)
                │
                ▼
        Telegram Bot (notifications + control)
```

---

## 3. Orchestration State Machine

### State file: `docs/orchestration/session.json`

```json
{
  "task": "short task description",
  "phase": "IMPLEMENTING",
  "agent": "claude",
  "iterations": 1,
  "failed_checks": 0,
  "uncertainty": false,
  "status": "ACTIVE",
  "started_at": "2026-03-29T10:00:00Z",
  "history": [
    {"phase": "PLANNING", "agent": "copilot", "completed_at": "...", "summary": "..."}
  ]
}
```

**Fields:**
- `phase`: `PLANNING | IMPLEMENTING | REVIEWING | FIXING | DONE`
- `agent`: `copilot | claude | human`
- `status`: `ACTIVE | BLOCKED | PAUSED | STOPPED | DONE`
- `iterations`: resets to 0 on phase change
- `failed_checks`: count of consecutive `make check` failures in current phase

### Phase transitions

```
START
  └─▶ PLANNING   (Copilot @planner OR Claude /plan)
        └─▶ IMPLEMENTING  (other agent picks up)
              └─▶ REVIEWING  (reviewing agent writes output)
                    ├─▶ DONE        (review passes)
                    └─▶ FIXING      (review fails with actionable feedback)
                          └─▶ REVIEWING  (loop, max 3 times)
```

At any phase, status can become `BLOCKED | PAUSED | STOPPED`.

### Agent assignment rule

**Default: same agent plans, implements, AND does the first review.** This keeps context intact — the agent that planned knows the intent best.

Only the **second review** (after FIXING) switches to the other agent. Fresh eyes only when actually needed, not on every phase.

```
Copilot plans → Copilot implements → Copilot reviews (first)
  → if FIXING needed → Claude reviews (second, fresh perspective)
  → if FIXING needed again → human intervenes (BLOCKED)
```

**Override**: human can direct a specific agent via Telegram before unblocking, or by editing `session.json` `agent` field directly. The orchestrator never auto-assigns over a human override.

---

## 4. Loop Prevention

All three triggers pause the session and fire a Telegram notification:

| Trigger | Condition | Action |
|---------|-----------|--------|
| Iteration limit | `iterations >= 3` in same phase | `status = BLOCKED`, Telegram ping |
| Quality gate failure | `failed_checks >= 2` | `status = BLOCKED`, Telegram ping |
| Uncertainty flag | Agent sets `"uncertainty": true` | `status = BLOCKED`, Telegram ping |

The orchestrator checks these conditions **before every state advance**. If any is true, the advance is cancelled and the human is notified.

---

## 5. Handoff Protocol

### When a handoff fires

| Event | Handoff? | Notes |
|-------|----------|-------|
| Updating handoff.md mid-work | ❌ No | Too noisy |
| Full plan written, no open uncertainty | ✅ Yes | PLANNING → IMPLEMENTING |
| First complete implementation + `make check` passes | ✅ Yes | IMPLEMENTING → REVIEWING |
| Review output written with actionable feedback | ✅ Yes | REVIEWING → FIXING or DONE |
| Fixes applied + `make check` passes | ✅ Yes | FIXING → REVIEWING |
| Agent flags uncertainty mid-work | ⏸ Pause | Telegram ping, wait for human |

### Handoff content format: `docs/orchestration/handoff.md`

```markdown
## Task
<short description>

## Changed Files
- src/path/to/file.py (lines X-Y): what changed
- tests/path/to/test.py (lines X-Y): what changed

## Output
<plan / implementation notes / review findings>

## Uncertainty
None  /  "<specific question that needs human decision>"
```

### Human input: `docs/orchestration/human_input.md`

Any free-form message sent via Telegram (not a `/command`) is stored here.
The receiving agent reads and incorporates it at the start of their phase, then clears the file.

---

## 6. Makefile Targets

```bash
make orchestrate-start TASK="description"   # create session.json, open new session
make orchestrate-next                        # advance phase, hand off, Telegram notify
make orchestrate-block REASON="..."         # flag uncertainty, set BLOCKED, Telegram ping
make orchestrate-resume                      # human clears BLOCKED/PAUSED, continue
make orchestrate-status                      # print current state to terminal
make orchestrate-done                        # mark session DONE, send Telegram summary
make template-clean                          # strip example data, reset orchestration files
```

---

## 7. Copilot Superpowers Parity

### New file: `.github/copilot-instructions.md`

Root-level file auto-loaded by Copilot for every chat interaction. Mirrors `CLAUDE.md` in content and structure. Includes:
- Project architecture and conventions
- The orchestration protocol (session.json, handoff.md, make targets)
- Cross-agent handoff rules
- Quality gate requirements

### Enforced workflow gates in every agent

All `.github/agents/*.agent.md` files get embedded ✅/❌ gates. Example for `orchestrator.agent.md`:

```markdown
## ✅ GATE: Before writing any code

- [ ] Check docs/orchestration/session.json — phase must be IMPLEMENTING
- [ ] Read docs/orchestration/handoff.md — approved plan must exist
- [ ] Read docs/orchestration/human_input.md — incorporate any pending input
- [ ] No open uncertainty flags in session.json

❌ STOP — if any gate fails:
   Run: make orchestrate-block REASON="<what is missing>"
   Do NOT proceed until human clears it via /resume
```

```markdown
## ✅ GATE: Before handing off

- [ ] make check passes (ruff + mypy + pytest)
- [ ] handoff.md updated with changed files + line numbers
- [ ] Uncertainty field is "None" or has a specific question

❌ STOP — if make check fails twice:
   Run: make orchestrate-block REASON="quality gate failed: <error summary>"
```

```markdown
## ✅ GATE: Uncertainty check (during work)

If any requirement is ambiguous, architectural decision is unclear,
or you are not confident in the correct approach:

❌ STOP immediately — do NOT guess and proceed:
   Run: make orchestrate-block REASON="<specific question>"
   Update handoff.md Uncertainty field
   Wait for human input via Telegram
```

### Cross-agent handoff instructions (in every agent)

```markdown
## Handing off to Claude Code
1. Update docs/orchestration/handoff.md (output + changed files)
2. Run: make orchestrate-next
3. Telegram will notify — Claude picks up via `make orchestrate-status`

## Handing off to Copilot
1. Update docs/orchestration/handoff.md
2. Run: make orchestrate-next
3. Telegram will notify — open VS Code Copilot chat, check handoff.md

## Requesting human decision
Run: make orchestrate-block REASON="need decision on X"
Do NOT continue working while blocked.
```

### Agents updated

| Agent | Gate added | Handoff instruction |
|-------|-----------|---------------------|
| `orchestrator.agent.md` | Before coding, before handoff, uncertainty | Full protocol |
| `planner.agent.md` | Before handing off plan | PLANNING → IMPLEMENTING |
| `tdd.agent.md` | Before writing production code, before handoff | IMPLEMENTING → REVIEWING |
| `debugger.agent.md` | Before proposing fix, before handoff | Root cause first |
| `code-reviewer.agent.md` | Before writing review output | REVIEWING → DONE/FIXING |

---

## 8. Telegram Enhancements

### Automatic events

| Event | Message sent |
|-------|-------------|
| Phase advance | Summary: task, old phase → new phase, agent, changed files |
| BLOCKED | Alert: what triggered block, what human needs to decide |
| `make check` failure | Alert: which check failed, iteration count |
| PR merged to main | "✅ merged: [task]" |
| Session DONE | Full session summary as document |

### Session summary format (sent as Telegram document on `/status` and at DONE)

```
📋 Session: <task>
Phase: <current>  |  Agent: <current>
Iteration: <n>/3  |  Checks: <n> failed

Changed files:
  • src/path/file.py (lines X-Y)
  • tests/path/test.py (lines X-Y)

Last action: <summary>
Uncertainty: <none / question>

/pause  /stop  /skip  /resume
```

### New commands

| Command | Action |
|---------|--------|
| `/stop` | Set status=STOPPED, no further automatic handoffs |
| `/pause` | Set status=PAUSED, next handoff waits for /resume |
| `/resume` | Clear PAUSED or BLOCKED, continue from current phase |
| `/skip` | Skip current phase, advance to next |
| `/status` | Send session summary (+ document for long sessions) |

### Free-form input

Any Telegram message that is not a `/command` is stored in `docs/orchestration/human_input.md` with a timestamp. Bot replies: "✅ Input saved. Agent will incorporate it on next pickup."

---

## 9. GitHub Actions Enhancements

### Updated `ci.yml`

- On push: run `make check` → if fails, read session.json for context → send Telegram alert directly (does NOT write back to session.json — no push conflicts)
- On PR open: run `make review` → post result as PR comment + send Telegram summary
- On PR merge to main: send Telegram "✅ merged: [branch]"

**Important**: GitHub Actions only READS session.json (for context in notifications). It never writes to it. All session state changes happen locally via `orchestrator.py`. This prevents merge conflicts between CI commits and developer commits.

`session.json` is committed to git so both local tools and CI can read it. `human_input.md` and `handoff.md` are also committed (short-lived content, cleared after agent reads them).

---

## 10. Template Packaging

### `make template-clean`

Strips this repo to a clean starting state for a new project:
- Removes `data/knowledge/raw/medium/` contents
- Removes `data/knowledge/meta/` contents
- Resets `docs/orchestration/session.json` to empty template
- Clears `docs/orchestration/handoff.md` and `human_input.md`
- Leaves all config, agents, instructions, Makefile, src/ intact

### `TEMPLATE.md` (root level)

5-step "clone and go" checklist:
1. Clone repo, run `make install`
2. Copy `.env.example` → `.env`, fill in tokens
3. Install superpowers: `/plugin install superpowers@claude-plugins-official`
4. Run `make template-clean` to reset example data
5. Start first session: `make orchestrate-start TASK="your first feature"`

---

## 11. Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/agents/orchestrator.py` | Create | State machine logic, loop prevention, Telegram triggers |
| `src/agents/onboarding.py` | Create | Interactive onboarding agent (BaseAgent-powered) |
| `docs/orchestration/session.json` | Create | Live session state |
| `docs/orchestration/handoff.md` | Create | Agent-to-agent content transfer |
| `docs/orchestration/human_input.md` | Create | Telegram → agent input channel |
| `docs/PROJECT.md` | Create (by onboarding) | One-page project brief |
| `tests/test_orchestrator.py` | Create | Tests for orchestrator logic |
| `tests/test_onboarding.py` | Create | Tests for onboarding agent |
| `.github/copilot-instructions.md` | Create | Copilot equivalent of CLAUDE.md |
| `.github/agents/orchestrator.agent.md` | Rewrite | Add enforced ✅/❌ gates |
| `.github/agents/planner.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/tdd.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/debugger.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/code-reviewer.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/setup.agent.md` | Create | Copilot onboarding agent |
| `src/bot/telegram_bot.py` | Modify | New commands + free-form input handler |
| `src/bot/notify.py` | Modify | Session summary + document sending |
| `.github/workflows/ci.yml` | Modify | Telegram on failure (reads session.json, no write) |
| `Makefile` | Modify | orchestrate-*, template-clean, onboard targets |
| `TEMPLATE.md` | Create | New project setup checklist |
| `CLAUDE.md` | Modify | Add orchestration protocol + skills inventory section |
| `docs/WORKTREES.md` | Modify | Integrate with orchestrator worktree support |

---

## 12. Skills & Agents Inventory

A clear reference of every agent and skill, what it does, and when to use it. Both tools load this so new projects start with full clarity.

### Claude Code (superpowers skills)

| Skill | When to invoke | Gate |
|-------|---------------|------|
| `brainstorming` | Before any new feature or design decision | Hard — no code before spec |
| `writing-plans` | After spec approved | Hard — no implementation before plan |
| `test-driven-development` | During implementation | Hard — failing test before production code |
| `systematic-debugging` | Any bug or unexpected behavior | Hard — root cause before fix |
| `verification-before-completion` | Before claiming done | Hard — run commands, show output |
| `subagent-driven-development` | Executing multi-task plans | Delegates to subagents per task |
| `using-git-worktrees` | Parallel feature work or parallel agents | Creates isolated branch per agent |
| `requesting-code-review` | After implementation, before merge | Structured review checklist |
| `finishing-a-development-branch` | When all tests pass and ready to integrate | Merge / PR / cleanup options |

### GitHub Copilot (agents)

| Agent | When to invoke | Key gate |
|-------|---------------|---------|
| `@planner` | Design + plan before coding | ✅ Write plan to handoff.md first |
| `@orchestrator` | End-to-end feature work | ✅ Check session.json before starting |
| `@tdd` | TDD implementation | ✅ Failing test before production code |
| `@debugger` | Bugs, test failures | ✅ Root cause before fix proposal |
| `@code-reviewer` | Review after implementation | ✅ Output to handoff.md, then orchestrate-next |
| `@setup` *(new)* | Onboarding a new project | ✅ Ask all questions before writing any config |

---

## 13. Worktrees Integration

Git worktrees let two agents work simultaneously on different branches without file conflicts.

### When to use worktrees

- A feature is large enough that Copilot implements while Claude reviews a previous PR
- Parallel tasks from the implementation plan that touch different files
- The orchestrator detects two independent tasks in the plan → suggests worktree setup

### Worktree naming convention

```bash
# Main agent workspace (current repo)
ai-dev-starter/           → branch: feat/task-name

# Second agent worktree (sibling directory)
../ai-dev-starter-agent2/ → branch: feat/task-name-review
```

### Orchestrator worktree support

`make orchestrate-start` gains an optional `WORKTREE=1` flag:
- Creates a sibling worktree automatically
- Updates session.json with `"worktree": "../ai-dev-starter-agent2"`
- Telegram message tells the second agent exactly which directory to work from
- On `make orchestrate-done`: merges worktree branch, removes worktree

### Branch visibility

Both agents see the same git history. The reviewing agent pulls the implementation branch into its worktree — no need to copy files.

---

## 14. Onboarding Agent (`@setup` / `make onboard`)

An interactive agent that guides setup of a new project from this template. Available as both a Copilot agent (`@setup`) and a Claude Code command (`make onboard`).

### What it does

Runs a structured conversation (5–8 questions), then writes all config automatically so the developer knows exactly where to start.

### Questions it asks

1. **Project name and description** — what are you building?
2. **Project type** — Python app / API / scraper / data pipeline / other
3. **External services** — which APIs, databases, or services will this project use? (sets up `.env.example` with the right variables)
4. **Team setup** — solo dev or team? (configures review strictness)
5. **Preferred starting agent** — Copilot-first or Claude-first?
6. **Parallel work** — want worktrees enabled for parallel agent tasks?
7. **Telegram** — have a bot token and chat ID? (configures notifications)
8. **Knowledge base** — any Medium lists or tags to pre-scrape for this domain?

### What it outputs

After the conversation:

| Output | Where |
|--------|-------|
| Project-specific `CLAUDE.md` section | Appended to existing CLAUDE.md |
| Updated `.github/copilot-instructions.md` | Project name, goal, key APIs |
| Configured `.env.example` | Only the variables this project needs |
| Initial `docs/orchestration/session.json` | Empty session, ready to start |
| `docs/PROJECT.md` | One-page project brief: goal, stack, conventions |
| First `make orchestrate-start` command | Printed to terminal, ready to copy |

### Implementation

- Claude Code: `make onboard` → runs `src/agents/onboarding.py` → uses `BaseAgent` for the conversation → writes files
- Copilot: `@setup` agent definition in `.github/agents/setup.agent.md` — same questions, writes same files via chat
- Both produce identical output so either tool can be used for setup

---

## 15. Out of Scope

- n8n workflow automation (separate concern)
- Multi-repo orchestration (this repo only)
- Real-time agent streaming (agents complete full phases before handoff)
- Automatic git commits by orchestrator (human always commits)
- Automatic worktree merge (human reviews and merges)
