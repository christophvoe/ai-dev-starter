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

**Default: always the other agent.** If Copilot planned → Claude implements. If Claude implemented → Copilot reviews. If Copilot reviewed → Claude fixes. This alternating pattern keeps each agent working from a fresh perspective.

**Override**: human can direct a specific agent by replying via Telegram before unblocking, or by editing `session.json` `agent` field. The orchestrator respects whatever is in the field — it never auto-assigns over a human override.

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
| `docs/orchestration/session.json` | Create | Live session state |
| `docs/orchestration/handoff.md` | Create | Agent-to-agent content transfer |
| `docs/orchestration/human_input.md` | Create | Telegram → agent input channel |
| `tests/test_orchestrator.py` | Create | Tests for orchestrator logic |
| `.github/copilot-instructions.md` | Create | Copilot equivalent of CLAUDE.md |
| `.github/agents/orchestrator.agent.md` | Rewrite | Add enforced ✅/❌ gates |
| `.github/agents/planner.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/tdd.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/debugger.agent.md` | Rewrite | Add enforced gates + handoff |
| `.github/agents/code-reviewer.agent.md` | Rewrite | Add enforced gates + handoff |
| `src/bot/telegram_bot.py` | Modify | New commands + free-form input handler |
| `src/bot/notify.py` | Modify | Session summary + document sending |
| `.github/workflows/ci.yml` | Modify | session.json integration + Telegram on failure |
| `Makefile` | Modify | Add orchestrate-* and template-clean targets |
| `TEMPLATE.md` | Create | New project setup checklist |
| `CLAUDE.md` | Modify | Add orchestration protocol section |

---

## 12. Out of Scope

- n8n workflow automation (separate concern)
- Multi-repo orchestration (this repo only)
- Real-time agent streaming (agents complete full phases before handoff)
- Automatic git commits by orchestrator (human always commits)
