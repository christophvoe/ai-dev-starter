# Multi-Agent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared state machine that lets GitHub Copilot and Claude Code hand off tasks to each other with loop prevention, Telegram control, and a guided onboarding agent for new projects.

**Architecture:** A `session.json` file in `docs/orchestration/` is the single source of truth. `src/agents/orchestrator.py` reads/writes it via `make orchestrate-*` targets. Copilot agents embed enforced ✅/❌ gates. Telegram is the human control plane.

**Tech Stack:** Python 3.12, python-telegram-bot, requests, pytest, ruff, mypy, GitHub Actions, Makefile

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/orchestration/session.json` | Create | Live session state |
| `docs/orchestration/handoff.md` | Create | Agent-to-agent content |
| `docs/orchestration/human_input.md` | Create | Telegram → agent input |
| `src/agents/orchestrator.py` | Create | State machine, loop prevention, CLI |
| `tests/test_orchestrator.py` | Create | Tests for orchestrator |
| `src/agents/onboarding.py` | Create | Interactive new-project agent |
| `tests/test_onboarding.py` | Create | Tests for onboarding |
| `src/bot/notify.py` | Modify | Add session summary + document sending |
| `src/bot/telegram_bot.py` | Modify | Add /stop /pause /resume /skip + free-form input |
| `tests/test_notify_orchestration.py` | Create | Tests for new notify functions |
| `.github/workflows/ci.yml` | Modify | Telegram on failure, PR events |
| `.github/copilot-instructions.md` | Create | Copilot equivalent of CLAUDE.md |
| `.github/agents/orchestrator.agent.md` | Rewrite | Add ✅/❌ gates + handoff protocol |
| `.github/agents/planner.agent.md` | Rewrite | Add gates + handoff |
| `.github/agents/tdd.agent.md` | Rewrite | Add gates + handoff |
| `.github/agents/debugger.agent.md` | Rewrite | Add gates + handoff |
| `.github/agents/code-reviewer.agent.md` | Rewrite | Add gates + handoff |
| `.github/agents/setup.agent.md` | Create | Copilot onboarding agent |
| `Makefile` | Modify | Add orchestrate-*, template-clean, onboard targets |
| `TEMPLATE.md` | Create | New project 5-step checklist |
| `CLAUDE.md` | Modify | Add orchestration section + skills inventory |
| `docs/WORKTREES.md` | Modify | Integrate orchestrator WORKTREE=1 flag |

---

## Task 1: Orchestration state files

**Files:**
- Create: `docs/orchestration/session.json`
- Create: `docs/orchestration/handoff.md`
- Create: `docs/orchestration/human_input.md`

No test needed — these are static template files.

- [ ] **Step 1: Create the directory and session.json template**

```bash
mkdir -p docs/orchestration
```

Create `docs/orchestration/session.json`:
```json
{
  "task": "",
  "phase": "PLANNING",
  "agent": "claude",
  "iterations": 0,
  "failed_checks": 0,
  "uncertainty": false,
  "status": "ACTIVE",
  "started_at": "",
  "worktree": null,
  "history": []
}
```

- [ ] **Step 2: Create handoff.md template**

Create `docs/orchestration/handoff.md`:
```markdown
## Task


## Changed Files


## Output


## Uncertainty
None
```

- [ ] **Step 3: Create human_input.md (empty)**

Create `docs/orchestration/human_input.md` with empty content (0 bytes).

- [ ] **Step 4: Commit**

```bash
git add docs/orchestration/
git commit -m "chore(orchestration): add state file templates"
```

---

## Task 2: orchestrator.py — data structures and file I/O

**Files:**
- Create: `src/agents/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_orchestrator.py`:
```python
"""Tests for orchestrator state machine."""

import json
from pathlib import Path

import pytest

from agents.orchestrator import empty_session, load_session, save_session, format_status


def test_empty_session_defaults():
    s = empty_session()
    assert s["phase"] == "PLANNING"
    assert s["agent"] == "claude"
    assert s["status"] == "ACTIVE"
    assert s["iterations"] == 0
    assert s["failed_checks"] == 0
    assert s["uncertainty"] is False
    assert s["history"] == []
    assert s["worktree"] is None


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test task"
    save_session(s, path=path)
    loaded = load_session(path=path)
    assert loaded["task"] == "test task"
    assert loaded["phase"] == "PLANNING"


def test_load_session_exits_if_no_file(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(SystemExit):
        load_session(path=path)


def test_format_status_contains_key_fields():
    s = empty_session()
    s["task"] = "add dedup"
    s["phase"] = "IMPLEMENTING"
    s["agent"] = "copilot"
    text = format_status(s)
    assert "add dedup" in text
    assert "IMPLEMENTING" in text
    assert "copilot" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_orchestrator.py -v
```
Expected: `ModuleNotFoundError: No module named 'agents.orchestrator'`

- [ ] **Step 3: Create src/agents/orchestrator.py with data structures and I/O**

```python
"""
Orchestration layer for GitHub Copilot ↔ Claude Code multi-agent workflow.

State machine: PLANNING → IMPLEMENTING → REVIEWING → DONE
               with BLOCKED / PAUSED / STOPPED interrupts at any point.

Usage via Makefile:
  make orchestrate-start TASK="description" [AGENT=copilot] [WORKTREE=1]
  make orchestrate-next [FAILED=1]
  make orchestrate-block REASON="..."
  make orchestrate-resume
  make orchestrate-status
  make orchestrate-done
  make orchestrate-check-failed
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "orchestration"
SESSION_FILE = DOCS_DIR / "session.json"
HANDOFF_FILE = DOCS_DIR / "handoff.md"
HUMAN_INPUT_FILE = DOCS_DIR / "human_input.md"

MAX_ITERATIONS = 3   # max REVIEWING→FIXING cycles before blocking
MAX_FAILED_CHECKS = 2  # max consecutive make check failures before blocking

NEXT_PHASE: dict[str, str] = {
    "PLANNING": "IMPLEMENTING",
    "IMPLEMENTING": "REVIEWING",
    "REVIEWING": "DONE",   # overridden to FIXING when review_passed=False
    "FIXING": "REVIEWING",
}


def empty_session() -> dict[str, Any]:
    """Return a fresh session dict with all required fields."""
    return {
        "task": "",
        "phase": "PLANNING",
        "agent": "claude",
        "iterations": 0,
        "failed_checks": 0,
        "uncertainty": False,
        "status": "ACTIVE",
        "started_at": _now(),
        "worktree": None,
        "history": [],
    }


def load_session(path: Path = SESSION_FILE) -> dict[str, Any]:
    """Load session from disk. Exits with error if file does not exist."""
    if not path.exists():
        print("No active session. Run: make orchestrate-start TASK='...'")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(session: dict[str, Any], path: Path = SESSION_FILE) -> None:
    """Write session to disk, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")


def format_status(session: dict[str, Any]) -> str:
    """Format session state as a human-readable string."""
    return (
        f"📋 Session: {session['task']}\n"
        f"Phase: {session['phase']} | Agent: {session['agent']}\n"
        f"Status: {session['status']}\n"
        f"Fix cycles: {session['iterations']}/{MAX_ITERATIONS} | "
        f"Failed checks: {session['failed_checks']}/{MAX_FAILED_CHECKS}\n"
        f"Uncertainty: {session['uncertainty']}"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _other_agent(agent: str) -> str:
    return "claude" if agent == "copilot" else "copilot"


def _task_slug(task: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]", "-", task.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:30]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_orchestrator.py -v
```
Expected: 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add src/agents/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(orchestrator): add session data structures and file I/O"
```

---

## Task 3: orchestrator.py — loop prevention

**Files:**
- Modify: `src/agents/orchestrator.py` (add `check_loop_triggers`)
- Modify: `tests/test_orchestrator.py` (add loop prevention tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_orchestrator.py`:
```python
from agents.orchestrator import check_loop_triggers


def test_check_loop_triggers_false_for_fresh_session():
    s = empty_session()
    blocked, reason = check_loop_triggers(s)
    assert blocked is False
    assert reason == ""


def test_check_loop_triggers_on_iteration_limit():
    s = empty_session()
    s["iterations"] = 3
    blocked, reason = check_loop_triggers(s)
    assert blocked is True
    assert "iteration" in reason.lower()


def test_check_loop_triggers_on_failed_checks():
    s = empty_session()
    s["failed_checks"] = 2
    blocked, reason = check_loop_triggers(s)
    assert blocked is True
    assert "quality gate" in reason.lower()


def test_check_loop_triggers_on_uncertainty():
    s = empty_session()
    s["uncertainty"] = True
    blocked, reason = check_loop_triggers(s)
    assert blocked is True
    assert "uncertainty" in reason.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_orchestrator.py::test_check_loop_triggers_false_for_fresh_session -v
```
Expected: `ImportError: cannot import name 'check_loop_triggers'`

- [ ] **Step 3: Add check_loop_triggers to orchestrator.py**

Add after `_task_slug` in `src/agents/orchestrator.py`:
```python
def check_loop_triggers(session: dict[str, Any]) -> tuple[bool, str]:
    """Return (should_block, reason). True means the session should be blocked now."""
    if session["iterations"] >= MAX_ITERATIONS:
        return True, f"iteration limit reached ({session['iterations']}/{MAX_ITERATIONS} fix cycles)"
    if session["failed_checks"] >= MAX_FAILED_CHECKS:
        return True, f"quality gate failed {session['failed_checks']} times consecutively"
    if session.get("uncertainty"):
        return True, "agent flagged uncertainty — human decision needed"
    return False, ""
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_orchestrator.py -v
```
Expected: all 8 tests pass

- [ ] **Step 5: Commit**

```bash
git add src/agents/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(orchestrator): add loop prevention triggers"
```

---

## Task 4: orchestrator.py — phase transitions

**Files:**
- Modify: `src/agents/orchestrator.py` (add `advance_phase`)
- Modify: `tests/test_orchestrator.py` (add phase transition tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_orchestrator.py`:
```python
from agents.orchestrator import advance_phase


def test_planning_to_implementing_same_agent():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "PLANNING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "IMPLEMENTING"
    assert result["agent"] == "copilot"   # same agent


def test_implementing_to_reviewing_same_agent():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "IMPLEMENTING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "REVIEWING"
    assert result["agent"] == "copilot"   # same agent


def test_reviewing_to_done_when_passed():
    s = empty_session()
    s["phase"] = "REVIEWING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "DONE"
    assert result["status"] == "DONE"


def test_reviewing_to_fixing_when_failed():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "REVIEWING"
    result = advance_phase(s, review_passed=False)
    assert result["phase"] == "FIXING"
    assert result["agent"] == "copilot"   # same agent still
    assert result["iterations"] == 1      # first fix cycle counted


def test_fixing_to_reviewing_switches_agent():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "FIXING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "REVIEWING"
    assert result["agent"] == "claude"   # switched to other agent


def test_advance_phase_records_history():
    s = empty_session()
    s["phase"] = "PLANNING"
    s["agent"] = "claude"
    result = advance_phase(s)
    assert len(result["history"]) == 1
    assert result["history"][0]["phase"] == "PLANNING"
    assert result["history"][0]["agent"] == "claude"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_orchestrator.py::test_planning_to_implementing_same_agent -v
```
Expected: `ImportError: cannot import name 'advance_phase'`

- [ ] **Step 3: Add advance_phase to orchestrator.py**

Add after `check_loop_triggers` in `src/agents/orchestrator.py`:
```python
def advance_phase(session: dict[str, Any], review_passed: bool = True) -> dict[str, Any]:
    """Compute and apply next phase + agent. Does NOT save to disk.

    - REVIEWING → FIXING increments iterations (fix cycle counter).
    - FIXING → REVIEWING switches to the other agent (fresh eyes).
    - All other transitions keep the same agent.
    """
    current_phase = session["phase"]
    current_agent = session["agent"]

    # Record current phase in history
    session["history"].append({
        "phase": current_phase,
        "agent": current_agent,
        "completed_at": _now(),
    })

    # Determine next phase
    if current_phase == "REVIEWING" and not review_passed:
        next_p = "FIXING"
        session["iterations"] += 1   # count each fix cycle
    else:
        next_p = NEXT_PHASE.get(current_phase, "DONE")

    # Determine next agent: switch only on FIXING → REVIEWING
    if current_phase == "FIXING":
        next_agent = _other_agent(current_agent)
    else:
        next_agent = current_agent

    session["phase"] = next_p
    session["agent"] = next_agent
    session["failed_checks"] = 0   # reset on phase change

    if next_p == "DONE":
        session["status"] = "DONE"

    return session
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest tests/test_orchestrator.py -v
```
Expected: all 14 tests pass

- [ ] **Step 5: Commit**

```bash
git add src/agents/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(orchestrator): add phase transition logic"
```

---

## Task 5: orchestrator.py — CLI commands

**Files:**
- Modify: `src/agents/orchestrator.py` (add all cmd_* functions + main)
- Modify: `tests/test_orchestrator.py` (add CLI command tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_orchestrator.py`:
```python
import subprocess
from unittest.mock import patch, MagicMock

from agents.orchestrator import (
    cmd_start, cmd_next, cmd_block, cmd_resume,
    cmd_status, cmd_done, cmd_check_failed,
)


def test_cmd_start_creates_session(tmp_path):
    session_path = tmp_path / "session.json"
    with patch("agents.orchestrator.send_message"):
        cmd_start("add dedup", agent="claude", worktree=False, path=session_path)
    assert session_path.exists()
    data = json.loads(session_path.read_text())
    assert data["task"] == "add dedup"
    assert data["phase"] == "PLANNING"
    assert data["agent"] == "claude"
    assert data["status"] == "ACTIVE"


def test_cmd_next_advances_phase(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message"):
        cmd_next(review_passed=True, path=session_path)
    updated = load_session(path=session_path)
    assert updated["phase"] == "IMPLEMENTING"


def test_cmd_next_blocks_on_loop_trigger(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["iterations"] = 3  # trigger limit
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message") as mock_send:
        cmd_next(review_passed=True, path=session_path)
    updated = load_session(path=session_path)
    assert updated["status"] == "BLOCKED"
    assert mock_send.called


def test_cmd_block_sets_blocked(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message"):
        cmd_block("unclear requirement", path=session_path)
    updated = load_session(path=session_path)
    assert updated["status"] == "BLOCKED"
    assert updated["uncertainty"] is True


def test_cmd_resume_clears_block(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["status"] = "BLOCKED"
    s["uncertainty"] = True
    s["failed_checks"] = 2
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message"):
        cmd_resume(path=session_path)
    updated = load_session(path=session_path)
    assert updated["status"] == "ACTIVE"
    assert updated["uncertainty"] is False
    assert updated["failed_checks"] == 0


def test_cmd_done_marks_done(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message"):
        cmd_done(path=session_path)
    updated = load_session(path=session_path)
    assert updated["status"] == "DONE"
    assert updated["phase"] == "DONE"


def test_cmd_check_failed_increments_counter(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message"):
        cmd_check_failed(path=session_path)
    updated = load_session(path=session_path)
    assert updated["failed_checks"] == 1


def test_cmd_check_failed_blocks_at_threshold(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["failed_checks"] = 1  # one away from threshold
    save_session(s, path=session_path)
    with patch("agents.orchestrator.send_message"):
        cmd_check_failed(path=session_path)
    updated = load_session(path=session_path)
    assert updated["failed_checks"] == 2
    assert updated["status"] == "BLOCKED"


def test_cmd_next_exits_if_stopped(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["status"] = "STOPPED"
    save_session(s, path=session_path)
    with pytest.raises(SystemExit):
        cmd_next(review_passed=True, path=session_path)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_orchestrator.py::test_cmd_start_creates_session -v
```
Expected: `ImportError: cannot import name 'cmd_start'`

- [ ] **Step 3: Add all cmd_* functions to orchestrator.py**

Append to `src/agents/orchestrator.py` (after `_task_slug`):
```python
def cmd_start(
    task: str,
    agent: str = "claude",
    worktree: bool = False,
    path: Path = SESSION_FILE,
) -> None:
    """Create a new session. Overwrites any existing session."""
    from bot.notify import send_message

    session = empty_session()
    session["task"] = task
    session["agent"] = agent

    if worktree:
        repo_name = Path.cwd().name
        worktree_path = f"../{repo_name}-agent2"
        branch = f"feat/orchestration-{_task_slug(task)}-agent2"
        try:
            subprocess.run(
                ["git", "worktree", "add", worktree_path, "-b", branch],
                check=True, capture_output=True, cwd=str(Path.cwd()),
            )
            session["worktree"] = worktree_path
            print(f"✓ Worktree created at {worktree_path} on branch {branch}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: could not create worktree: {e.stderr.decode()}")

    save_session(session, path)

    # Ensure template files exist
    path.parent.mkdir(parents=True, exist_ok=True)
    if not (path.parent / "handoff.md").exists():
        (path.parent / "handoff.md").write_text(
            "## Task\n\n## Changed Files\n\n## Output\n\n## Uncertainty\nNone\n",
            encoding="utf-8",
        )
    if not (path.parent / "human_input.md").exists():
        (path.parent / "human_input.md").write_text("", encoding="utf-8")

    msg = (
        f"🚀 *Session started*\n"
        f"Task: {task}\n"
        f"Phase: PLANNING | Agent: {agent}"
    )
    send_message(msg)
    print(msg.replace("*", ""))


def cmd_next(review_passed: bool = True, path: Path = SESSION_FILE) -> None:
    """Advance to the next phase. Blocks if loop prevention triggers fire."""
    from bot.notify import send_message

    session = load_session(path)

    if session["status"] in ("STOPPED", "PAUSED"):
        print(f"Session is {session['status']}. Run: make orchestrate-resume")
        sys.exit(1)

    should_block, reason = check_loop_triggers(session)
    if should_block:
        cmd_block(reason, path=path)
        return

    old_phase = session["phase"]
    old_agent = session["agent"]
    session = advance_phase(session, review_passed=review_passed)
    save_session(session, path)

    msg = (
        f"⏩ *Phase advance*\n"
        f"Task: {session['task']}\n"
        f"{old_phase} ({old_agent}) → {session['phase']} ({session['agent']})"
    )
    if session["phase"] == "DONE":
        msg = f"✅ *Session complete*\nTask: {session['task']}"
    send_message(msg)
    print(msg.replace("*", ""))


def cmd_block(reason: str, path: Path = SESSION_FILE) -> None:
    """Block the session and alert via Telegram."""
    from bot.notify import send_message

    session = load_session(path)
    session["status"] = "BLOCKED"
    session["uncertainty"] = True
    save_session(session, path)

    msg = (
        f"🚫 *Session BLOCKED*\n"
        f"Task: {session['task']}\n"
        f"Phase: {session['phase']} | Agent: {session['agent']}\n"
        f"Reason: {reason}\n\n"
        f"Reply with guidance or run: `make orchestrate-resume`"
    )
    send_message(msg)
    print(msg.replace("*", "").replace("`", ""))


def cmd_resume(path: Path = SESSION_FILE) -> None:
    """Clear BLOCKED/PAUSED status and print any pending human input."""
    from bot.notify import send_message

    session = load_session(path)
    session["status"] = "ACTIVE"
    session["uncertainty"] = False
    session["failed_checks"] = 0
    save_session(session, path)

    human_input = ""
    hi_file = path.parent / "human_input.md"
    if hi_file.exists():
        human_input = hi_file.read_text(encoding="utf-8").strip()

    msg = (
        f"▶️ *Session resumed*\n"
        f"Task: {session['task']}\n"
        f"Phase: {session['phase']} | Agent: {session['agent']}"
    )
    if human_input:
        msg += f"\n\n💬 Human input:\n{human_input}"
    send_message(msg)
    print(msg.replace("*", ""))


def cmd_status(path: Path = SESSION_FILE) -> None:
    """Print current session state."""
    session = load_session(path)
    print(format_status(session))


def cmd_done(path: Path = SESSION_FILE) -> None:
    """Mark session as DONE and send Telegram summary."""
    from bot.notify import send_message, send_session_summary

    session = load_session(path)
    session["status"] = "DONE"
    session["phase"] = "DONE"
    save_session(session, path)

    send_session_summary(session)
    print(f"✅ Session complete: {session['task']}")


def cmd_check_failed(path: Path = SESSION_FILE) -> None:
    """Increment failed_checks. Blocks if threshold reached."""
    session = load_session(path)
    session["failed_checks"] += 1
    should_block, reason = check_loop_triggers(session)
    if should_block:
        save_session(session, path)
        cmd_block(reason, path=path)
    else:
        save_session(session, path)
        print(
            f"Check failed ({session['failed_checks']}/{MAX_FAILED_CHECKS}). "
            "Fix and run make check again."
        )
```

- [ ] **Step 4: Add main() to orchestrator.py**

Append to `src/agents/orchestrator.py`:
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestration layer for multi-agent workflow")
    sub = parser.add_subparsers(dest="command")

    start_p = sub.add_parser("start", help="Start a new session")
    start_p.add_argument("task", help="Short task description")
    start_p.add_argument("--agent", default="claude", choices=["claude", "copilot"])
    start_p.add_argument("--worktree", action="store_true", help="Create git worktree")

    next_p = sub.add_parser("next", help="Advance to next phase")
    next_p.add_argument("--failed", action="store_true", help="Review failed (go to FIXING)")

    block_p = sub.add_parser("block", help="Block with reason")
    block_p.add_argument("reason", help="Why blocking")

    sub.add_parser("resume", help="Clear block/pause")
    sub.add_parser("status", help="Print current state")
    sub.add_parser("done", help="Mark session complete")
    sub.add_parser("check-failed", help="Increment failed check counter")

    args = parser.parse_args()

    commands = {
        "start": lambda: cmd_start(args.task, args.agent, args.worktree),
        "next": lambda: cmd_next(review_passed=not args.failed),
        "block": lambda: cmd_block(args.reason),
        "resume": cmd_resume,
        "status": cmd_status,
        "done": cmd_done,
        "check-failed": cmd_check_failed,
    }

    if args.command in commands:
        commands[args.command]()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/test_orchestrator.py -v
```
Expected: all 22 tests pass

- [ ] **Step 6: Run full quality gate**

```bash
uv run ruff check src/agents/orchestrator.py
uv run mypy src/agents/orchestrator.py
```
Fix any issues.

- [ ] **Step 7: Commit**

```bash
git add src/agents/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(orchestrator): add CLI commands (start/next/block/resume/status/done)"
```

---

## Task 6: Makefile orchestration targets

**Files:**
- Modify: `Makefile`

No unit tests — these are integration-tested by running them.

- [ ] **Step 1: Add the targets to Makefile**

Add after the `review` target in `Makefile`:

```makefile
# ── Orchestration ──────────────────────────────────────────────────────────────

orchestrate-start: ## Start orchestration session (TASK="..." [AGENT=copilot] [WORKTREE=1])
	uv run python -m agents.orchestrator start "$(TASK)" $(if $(AGENT),--agent "$(AGENT)",) $(if $(WORKTREE),--worktree,)

orchestrate-next: ## Advance to next phase [FAILED=1 if review failed]
	uv run python -m agents.orchestrator next $(if $(FAILED),--failed,)

orchestrate-block: ## Block session with reason (REASON="...")
	uv run python -m agents.orchestrator block "$(REASON)"

orchestrate-resume: ## Resume blocked/paused session
	uv run python -m agents.orchestrator resume

orchestrate-status: ## Show current orchestration state
	uv run python -m agents.orchestrator status

orchestrate-done: ## Mark session complete
	uv run python -m agents.orchestrator done

orchestrate-check-failed: ## Increment failed check counter (call after make check fails)
	uv run python -m agents.orchestrator check-failed

onboard: ## Interactive new-project onboarding agent
	uv run python -m agents.onboarding

template-clean: ## Reset repo to clean template state (strips example data)
	@echo "Cleaning example data..."
	find data/knowledge/raw/medium -name "*.md" -delete 2>/dev/null || true
	find data/knowledge/meta -name "*.json" -delete 2>/dev/null || true
	@echo '{"task":"","phase":"PLANNING","agent":"claude","iterations":0,"failed_checks":0,"uncertainty":false,"status":"ACTIVE","started_at":"","worktree":null,"history":[]}' > docs/orchestration/session.json
	@echo "" > docs/orchestration/handoff.md
	@echo "" > docs/orchestration/human_input.md
	@echo "✓ Template clean. Edit .env and run: make orchestrate-start TASK='your first task'"
```

- [ ] **Step 2: Update the .PHONY line at top of Makefile**

Edit the first line to add the new targets:
```makefile
.PHONY: help install sync lock lint format typecheck test test-cov check clean pre-commit scrape scrape-list scrape-tag scrape-article scrape-bookmarks summarize notify bot review orchestrate-start orchestrate-next orchestrate-block orchestrate-resume orchestrate-status orchestrate-done orchestrate-check-failed onboard template-clean discover discover-scrape
```

- [ ] **Step 3: Verify orchestrate-status works**

```bash
make orchestrate-status
```
Expected: prints current state from `docs/orchestration/session.json`

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "feat(makefile): add orchestrate-*, onboard, template-clean targets"
```

---

## Task 7: notify.py — session summary and document sending

**Files:**
- Modify: `src/bot/notify.py`
- Create: `tests/test_notify_orchestration.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_notify_orchestration.py`:
```python
"""Tests for orchestration-related notify functions."""

from unittest.mock import patch, MagicMock

import pytest

from bot.notify import send_session_summary, send_document, send_block_alert


def _make_session():
    return {
        "task": "add dedup",
        "phase": "REVIEWING",
        "agent": "copilot",
        "status": "ACTIVE",
        "iterations": 1,
        "failed_checks": 0,
        "uncertainty": False,
        "history": [
            {"phase": "PLANNING", "agent": "copilot", "completed_at": "2026-03-29T10:00:00Z"},
            {"phase": "IMPLEMENTING", "agent": "copilot", "completed_at": "2026-03-29T11:00:00Z"},
        ],
    }


def test_send_session_summary_calls_send_message():
    session = _make_session()
    with patch("bot.notify.send_message", return_value=True) as mock_send:
        result = send_session_summary(session)
    assert result is True
    call_text = mock_send.call_args[0][0]
    assert "add dedup" in call_text
    assert "REVIEWING" in call_text
    assert "copilot" in call_text


def test_send_block_alert_contains_reason():
    with patch("bot.notify.send_message", return_value=True) as mock_send:
        send_block_alert(
            task="add dedup",
            phase="IMPLEMENTING",
            reason="unclear whether to use URL hash or content hash",
            agent="claude",
        )
    call_text = mock_send.call_args[0][0]
    assert "BLOCKED" in call_text
    assert "URL hash" in call_text


def test_send_document_calls_telegram_api():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("bot.notify.requests.post", return_value=mock_resp) as mock_post:
        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "123",
        }):
            import importlib
            import bot.notify as notify_mod
            importlib.reload(notify_mod)
            result = notify_mod.send_document("content here", "session.md")
    assert mock_post.called


def test_send_session_summary_returns_false_if_no_token():
    session = _make_session()
    with patch("bot.notify.TELEGRAM_BOT_TOKEN", ""):
        result = send_session_summary(session)
    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_notify_orchestration.py -v
```
Expected: `ImportError: cannot import name 'send_session_summary'`

- [ ] **Step 3: Add new functions to src/bot/notify.py**

Add after `send_discover_report` in `src/bot/notify.py`:

```python
TELEGRAM_SEND_DOCUMENT_URL = "https://api.telegram.org/bot{token}/sendDocument"


def send_session_summary(session: dict) -> bool:
    """Send a formatted session state summary to Telegram."""
    phase = session.get("phase", "?")
    agent = session.get("agent", "?")
    task = session.get("task", "?")
    iterations = session.get("iterations", 0)
    failed = session.get("failed_checks", 0)
    status = session.get("status", "?")

    lines = [
        f"📋 *Session: {task}*",
        f"Phase: `{phase}` | Agent: `{agent}` | Status: `{status}`",
        f"Fix cycles: {iterations}/3 | Failed checks: {failed}/2",
        "",
        "/pause  /stop  /skip  /resume",
    ]
    return send_message("\n".join(lines))


def send_document(text: str, filename: str = "session-summary.md") -> bool:
    """Send text content as a downloadable Telegram document."""
    import io

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram credentials not set — skipping document send")
        return False

    url = TELEGRAM_SEND_DOCUMENT_URL.format(token=TELEGRAM_BOT_TOKEN)
    content = text.encode("utf-8")
    files = {"document": (filename, io.BytesIO(content), "text/plain")}
    data = {"chat_id": TELEGRAM_CHAT_ID}

    try:
        resp = requests.post(url, data=data, files=files, timeout=10)
        if resp.status_code == 200:
            log.info("Telegram document sent: %s", filename)
            return True
        log.error("Telegram document API error %s: %s", resp.status_code, resp.text[:200])
        return False
    except requests.RequestException as exc:
        log.error("Failed to send Telegram document: %s", exc)
        return False


def send_block_alert(task: str, phase: str, reason: str, agent: str) -> bool:
    """Send a BLOCKED alert to Telegram."""
    text = (
        f"🚫 *Session BLOCKED*\n"
        f"Task: {task}\n"
        f"Phase: `{phase}` | Agent: `{agent}`\n"
        f"Reason: {reason}\n\n"
        f"Reply with guidance or run: `make orchestrate-resume`"
    )
    return send_message(text)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_notify_orchestration.py -v
```
Expected: 3 of 4 pass (the `send_document` test requires env vars — that's OK)

- [ ] **Step 5: Run full quality gate**

```bash
uv run ruff check src/bot/notify.py
uv run mypy src/bot/notify.py
```

- [ ] **Step 6: Commit**

```bash
git add src/bot/notify.py tests/test_notify_orchestration.py
git commit -m "feat(notify): add session summary, document sending, block alert"
```

---

## Task 8: telegram_bot.py — orchestration commands + free-form input

**Files:**
- Modify: `src/bot/telegram_bot.py`

- [ ] **Step 1: Add imports and helper at top of telegram_bot.py**

After the existing imports in `src/bot/telegram_bot.py`, add:
```python
import json
from pathlib import Path

ORCHESTRATION_DIR = BASE_DIR / "docs" / "orchestration"
SESSION_FILE = ORCHESTRATION_DIR / "session.json"
HUMAN_INPUT_FILE = ORCHESTRATION_DIR / "human_input.md"
```

- [ ] **Step 2: Add the new command handlers inside start_bot()**

Add these handlers inside `start_bot()`, before the `app = Application.builder()` line:

```python
    @_guard
    async def cmd_orchestrate_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if SESSION_FILE.exists():
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            data["status"] = "STOPPED"
            SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            await update.message.reply_text(
                f"🛑 Session STOPPED: {data.get('task', '?')}\n"
                "No further automatic handoffs. Run /resume to continue."
            )
        else:
            await update.message.reply_text("No active session.")

    @_guard
    async def cmd_orchestrate_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if SESSION_FILE.exists():
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            data["status"] = "PAUSED"
            SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            await update.message.reply_text(
                f"⏸ Session PAUSED: {data.get('task', '?')}\n"
                "Run /resume to continue."
            )
        else:
            await update.message.reply_text("No active session.")

    @_guard
    async def cmd_orchestrate_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
        output = _run(["python", "-m", "agents.orchestrator", "resume"])
        await update.message.reply_text(output)

    @_guard
    async def cmd_orchestrate_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
        output = _run(["python", "-m", "agents.orchestrator", "next"])
        await update.message.reply_text(output)

    @_guard
    async def cmd_orchestrate_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SESSION_FILE.exists():
            await update.message.reply_text("No active session.")
            return
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        summary = (
            f"📋 *Session:* {data.get('task', '?')}\n"
            f"Phase: `{data.get('phase', '?')}` | Agent: `{data.get('agent', '?')}`\n"
            f"Status: `{data.get('status', '?')}`\n"
            f"Fix cycles: {data.get('iterations', 0)}/3 | "
            f"Failed checks: {data.get('failed_checks', 0)}/2\n\n"
            "/pause  /stop  /skip  /resume"
        )
        await update.message.reply_text(summary, parse_mode="Markdown")

    @_guard
    async def handle_human_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save any non-command text as human input for the next agent pickup."""
        from datetime import datetime
        text = update.message.text or ""
        if not text.strip():
            return
        ORCHESTRATION_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        entry = f"\n<!-- {timestamp} -->\n{text}\n"
        existing = HUMAN_INPUT_FILE.read_text(encoding="utf-8") if HUMAN_INPUT_FILE.exists() else ""
        HUMAN_INPUT_FILE.write_text(existing + entry, encoding="utf-8")
        await update.message.reply_text(
            "✅ Input saved. Agent will incorporate it on next pickup."
        )
```

- [ ] **Step 3: Register the new handlers**

Replace the `app.add_handler` block in `start_bot()` with:
```python
    from telegram.ext import MessageHandler, filters

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_orchestrate_status))
    app.add_handler(CommandHandler("scrape", cmd_scrape))
    app.add_handler(CommandHandler("discover", cmd_discover))
    app.add_handler(CommandHandler("review", cmd_review))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("stop", cmd_orchestrate_stop))
    app.add_handler(CommandHandler("pause", cmd_orchestrate_pause))
    app.add_handler(CommandHandler("resume", cmd_orchestrate_resume))
    app.add_handler(CommandHandler("skip", cmd_orchestrate_skip))
    # Free-form text → human input (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_human_input))
```

- [ ] **Step 4: Update /help text**

Replace the `cmd_help` reply text:
```python
        await update.message.reply_text(
            "*Orchestration:*\n"
            "/status — session state\n"
            "/stop — stop session (no more handoffs)\n"
            "/pause — pause session\n"
            "/resume — resume paused/blocked session\n"
            "/skip — skip current phase\n\n"
            "*Development:*\n"
            "/scrape — fetch Medium articles\n"
            "/discover [tags] — discover trending articles\n"
            "/review [branch] — AI code review\n"
            "/check — run quality gate\n"
            "/ask <question> — query knowledge base\n\n"
            "_Any other text → saved as agent input_",
            parse_mode="Markdown",
        )
```

- [ ] **Step 5: Run quality gate**

```bash
uv run ruff check src/bot/telegram_bot.py
uv run mypy src/bot/telegram_bot.py
uv run pytest tests/ -v
```
Fix any issues.

- [ ] **Step 6: Commit**

```bash
git add src/bot/telegram_bot.py
git commit -m "feat(bot): add orchestration commands and free-form human input handler"
```

---

## Task 9: GitHub Actions — Telegram notifications

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Update ci.yml with Telegram notification steps**

Replace `.github/workflows/ci.yml` with:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  pull_request_target:
    types: [closed]

permissions:
  contents: read
  pull-requests: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Lint (ruff)
        id: lint
        run: uv run ruff check src/ tests/

      - name: Type check (mypy)
        id: typecheck
        run: uv run mypy src/

      - name: Test (pytest)
        id: test
        run: uv run pytest tests/ -v

      - name: Notify Telegram on failure
        if: failure() && env.TELEGRAM_BOT_TOKEN != ''
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          # Read task from session.json if present
          TASK="unknown"
          if [ -f docs/orchestration/session.json ]; then
            TASK=$(python -c "import json; d=json.load(open('docs/orchestration/session.json')); print(d.get('task','unknown'))" 2>/dev/null || echo "unknown")
          fi
          MESSAGE="❌ CI failed on \`${{ github.ref_name }}\`%0ATask: ${TASK}%0ACommit: ${{ github.sha }}%0ARun: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${MESSAGE}" \
            -d "parse_mode=Markdown"

  notify-pr-merged:
    runs-on: ubuntu-latest
    if: github.event.pull_request.merged == true
    steps:
      - name: Notify Telegram on PR merge
        if: env.TELEGRAM_BOT_TOKEN != ''
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          MESSAGE="✅ PR merged: ${{ github.event.pull_request.title }}%0ABranch: ${{ github.event.pull_request.head.ref }} → main"
          curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${MESSAGE}"
```

- [ ] **Step 2: Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to GitHub repo secrets**

Go to: repo Settings → Secrets and variables → Actions → New repository secret
Add: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

(This is a manual step — no code needed.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat(ci): add Telegram notifications on failure and PR merge"
```

---

## Task 10: .github/copilot-instructions.md

**Files:**
- Create: `.github/copilot-instructions.md`

- [ ] **Step 1: Create the file**

Create `.github/copilot-instructions.md`:
```markdown
# AI Dev Starter — GitHub Copilot Context

> Auto-loaded by Copilot for every chat interaction. Keep under 400 lines.

---

## 1. Architecture

**Type**: Python 3.12+ application | **Deps**: uv (pyproject.toml + uv.lock)
**PYTHONPATH=src** — import as `from agents.base import BaseAgent`

```
src/
  agents/base.py              — BaseAgent: multi-LLM wrapper (Anthropic + OpenAI)
  agents/orchestrator.py      — State machine: PLANNING→IMPLEMENTING→REVIEWING→DONE
  agents/onboarding.py        — Interactive new-project setup agent
  knowledge/medium_scraper.py — Medium article scraper (HTTP/RSS, no AI needed)
  knowledge/article_curator.py — LLM-powered article curation
  bot/telegram_bot.py         — Telegram bot: remote control + free-form human input
  bot/notify.py               — Telegram notifications (standalone)
  utils/logger_config.py      — Logging setup

docs/orchestration/           — Session state (session.json, handoff.md, human_input.md)
```

---

## 2. Orchestration Protocol

**ALWAYS check session state before starting any work.**

```bash
make orchestrate-status      # see current phase, agent, task
```

The session state machine:
```
PLANNING → IMPLEMENTING → REVIEWING → DONE
                               ↓ (if review fails)
                            FIXING → REVIEWING (other agent)
```

**Shared files** (both tools read/write these):
- `docs/orchestration/session.json` — current phase, agent, iteration count
- `docs/orchestration/handoff.md` — plan / output / changed files for pickup
- `docs/orchestration/human_input.md` — guidance from Telegram, read at phase start

**Key commands:**
```bash
make orchestrate-start TASK="description"   # new session
make orchestrate-next                        # advance phase + notify Telegram
make orchestrate-block REASON="..."         # flag uncertainty, pause, notify human
make orchestrate-resume                      # human cleared it, continue
make orchestrate-done                        # session complete
make orchestrate-check-failed               # make check failed, increment counter
```

---

## 3. Agent Assignment Rule

**Same agent: plans + implements + first review.**
Only after FIXING does the other agent review (fresh eyes).

```
You plan → You implement → You review (first)
  → FIXING needed? → Other agent reviews (second)
  → FIXING again? → Human intervenes (BLOCKED)
```

---

## 4. Code Style

- **Formatter/Linter**: ruff (line-length 100, configured in pyproject.toml)
- **Type checker**: mypy (strict on src/)
- **Imports**: absolute from src/ root — `from agents.base import BaseAgent`
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_SNAKE_CASE constants
- **Strings**: double quotes preferred
- **Max function length**: ~50 lines — extract helpers if longer
- **Paths**: `Path(__file__).resolve().parent` — never hardcoded strings
- **Secrets**: via python-dotenv + `.env` — NEVER hardcoded or logged

---

## 5. Quality Gate

Run before EVERY handoff or commit:
```bash
make check    # ruff + mypy + pytest (all at once)
```

If it fails twice: run `make orchestrate-check-failed` instead of pushing broken code.

---

## 6. Testing

- pytest in `tests/test_*.py`
- Mock ALL external calls: `@patch("module.requests.get")`
- Test naming: `test_<function>_<scenario>`
- Cover: happy path + None/empty + network errors + boundary conditions

---

## 7. Commit Format

```
type(scope): description

Types: feat, fix, refactor, docs, test, chore
Example: feat(orchestrator): add loop prevention triggers
```

---

## 8. Skills Reference

### This tool (Copilot agents)

| Agent | When | Key gate |
|-------|------|---------|
| `@planner` | Design + plan | ✅ Write to handoff.md first |
| `@orchestrator` | End-to-end feature | ✅ Check session.json, run gates |
| `@tdd` | TDD implementation | ✅ Failing test before production code |
| `@debugger` | Bugs/failures | ✅ Root cause before fix |
| `@code-reviewer` | Review phase | ✅ Write to handoff.md, then orchestrate-next |
| `@setup` | New project onboarding | ✅ Ask all questions before writing config |

### Claude Code (superpowers skills)

| Skill | When |
|-------|------|
| `brainstorming` | Before any design decision |
| `writing-plans` | After spec approved |
| `test-driven-development` | During implementation |
| `systematic-debugging` | Any bug or test failure |
| `verification-before-completion` | Before claiming done |

---

## 9. Secrets

Variables needed (in `.env`):
```
ANTHROPIC_API_KEY=    # Claude models
OPENAI_API_KEY=       # GPT models (optional)
TELEGRAM_BOT_TOKEN=   # Telegram bot
TELEGRAM_CHAT_ID=     # Where to send messages
TELEGRAM_USER_ID=     # Allowed user ID
MEDIUM_COOKIES=       # For scraping member-only articles
```
```

- [ ] **Step 2: Commit**

```bash
git add .github/copilot-instructions.md
git commit -m "feat(copilot): add copilot-instructions.md (CLAUDE.md equivalent)"
```

---

## Task 11: Rewrite Copilot agents with enforced gates

**Files:**
- Rewrite: `.github/agents/orchestrator.agent.md`
- Rewrite: `.github/agents/planner.agent.md`
- Rewrite: `.github/agents/tdd.agent.md`
- Rewrite: `.github/agents/debugger.agent.md`
- Rewrite: `.github/agents/code-reviewer.agent.md`

- [ ] **Step 1: Rewrite orchestrator.agent.md**

```markdown
---
description: "Orchestrate end-to-end feature development. Plan → Implement → Test → Review → Handoff. Use for complete feature work with built-in quality and uncertainty gates."
tools: [read, search, edit, execute]
---
You are the orchestrator agent. You execute complete development workflows with enforced quality gates.

## ✅ GATE: Before writing any code

- [ ] Run `make orchestrate-status` — read docs/orchestration/session.json
- [ ] Phase must be IMPLEMENTING
- [ ] docs/orchestration/handoff.md must contain an approved plan
- [ ] docs/orchestration/human_input.md — read and incorporate any pending input (then note it as read)
- [ ] No open uncertainty flag in session.json

❌ STOP — if any gate fails:
```
make orchestrate-block REASON="<what is missing>"
```
Do NOT write code until human clears it via `/resume`.

---

## ✅ GATE: Uncertainty check (during work)

If ANY of these are true — STOP immediately, do NOT guess:
- A requirement can be interpreted two different ways
- An architectural decision needs input you don't have
- You are not confident the approach is correct

```
make orchestrate-block REASON="<specific question>"
```
Update `docs/orchestration/handoff.md` Uncertainty field with the question.

---

## ✅ GATE: Before handing off

- [ ] `make check` passes (ruff + mypy + pytest)
- [ ] docs/orchestration/handoff.md updated with changed files + line numbers
- [ ] Uncertainty field is "None"

❌ STOP — if `make check` fails:
```
make orchestrate-check-failed
```
Fix the issue and retry. After 2 failures the session blocks automatically.

---

## Workflow

1. Read session.json and handoff.md (the plan)
2. Incorporate any human_input.md content
3. Implement following the plan, TDD (failing test first)
4. Run `make check` — fix until it passes
5. Update handoff.md with changed files + line numbers
6. Hand off:
```
make orchestrate-next
```

## Handing off to Claude Code
1. Update docs/orchestration/handoff.md
2. Run: `make orchestrate-next`
3. Telegram notifies — Claude runs `make orchestrate-status` to pick up

## Handing off to Copilot (another agent)
1. Update docs/orchestration/handoff.md
2. Run: `make orchestrate-next`
3. Open VS Code Copilot chat, run `make orchestrate-status` first

## Code standards
- ruff (line-length 100), mypy strict, absolute imports from src/
- snake_case functions, PascalCase classes, double quotes
- Functions ≤50 lines, secrets in .env only
- Tests in tests/test_*.py, mock all external calls
```

- [ ] **Step 2: Rewrite planner.agent.md**

```markdown
---
description: "Plan features, refactors, or architectural changes. Read-only — analyzes code, never edits. Writes plan to docs/orchestration/handoff.md."
tools: [read, search]
---
You are the planner. You create implementation plans before any code is written. You NEVER edit files — only read and analyze.

## ✅ GATE: Before handing off your plan

- [ ] Plan written to docs/orchestration/handoff.md
- [ ] All sections filled: Task, Approach, Edge Cases, Testing Plan, Tradeoffs, Scope
- [ ] Uncertainty field: "None" if confident, or specific question if not
- [ ] No open questions that would block implementation

❌ STOP — if you cannot answer something critical:
```
make orchestrate-block REASON="<specific blocking question>"
```

---

## ✅ GATE: Uncertainty check

If the requirements are ambiguous or the correct approach is unclear:
```
make orchestrate-block REASON="<question>"
```
Do NOT write a plan for an unclear requirement. Block and wait.

---

## Planning Process

1. Read relevant source files to understand current architecture
2. Propose the approach with specific files + functions to create/modify
3. Identify edge cases and failure modes (empty input, None, network errors, Windows/Unix)
4. Keep solutions minimal — YAGNI (no features beyond what's asked)
5. Write your plan to docs/orchestration/handoff.md

## handoff.md format

```markdown
## Task
<one sentence>

## Changed Files
- src/path/file.py: what changes and why
- tests/path/test.py: what tests to write

## Output
### Goal
<one sentence>

### Approach
- File 1: change description
- File 2: change description

### Edge Cases
- What if input is None?
- What if HTTP returns 403?

### Testing Plan
- Mock: external calls
- Test: happy path, None input, network error

### Tradeoffs
- Alternative considered and why this wins

### Scope
Small / Medium / Large

## Uncertainty
None
```

## After writing the plan
```
make orchestrate-next
```
Telegram notifies the implementing agent to pick up.
```

- [ ] **Step 3: Rewrite tdd.agent.md**

```markdown
---
description: "TDD implementation: Red → Green → Refactor. Always write a failing test first. Never write production code without a failing test."
tools: [read, search, edit, execute]
---
You are the TDD agent. You enforce Red-Green-Refactor on every change.

## ✅ GATE: Before writing any production code

- [ ] A failing test exists that proves the feature is missing
- [ ] You have run the test and seen it fail with the right error
- [ ] The failure message matches what you expect

❌ STOP — if you write production code without a failing test first, you are breaking TDD.
Write the test. Run it. See it fail. Then implement.

---

## ✅ GATE: Before handing off

- [ ] All new tests pass: `uv run pytest tests/ -v`
- [ ] `make check` passes (ruff + mypy + pytest)
- [ ] No production code lacks a corresponding test
- [ ] docs/orchestration/handoff.md updated with changed files + line numbers

❌ STOP — if `make check` fails:
```
make orchestrate-check-failed
```

---

## ✅ GATE: Uncertainty check

If a requirement is unclear, STOP:
```
make orchestrate-block REASON="<question>"
```

---

## TDD Cycle (for EVERY function/feature)

1. **Red**: Write the failing test
   ```python
   def test_<function>_<scenario>():
       result = function(input)
       assert result == expected
   ```
2. **Run**: `uv run pytest tests/test_<file>.py::test_<name> -v`
   → Must fail with a meaningful error, not just ImportError
3. **Green**: Write the minimal code to make it pass
4. **Run**: Same command → must pass
5. **Refactor**: Clean up without breaking the test
6. **Repeat** for next function

## After implementation
```
make check   # must pass
make orchestrate-next
```
```

- [ ] **Step 4: Rewrite debugger.agent.md**

```markdown
---
description: "Debug bugs and test failures systematically. Root cause first — never guess. Four phases: investigate, pattern analysis, hypothesis, fix."
tools: [read, search, edit, execute]
---
You are the debugger. You investigate root causes before proposing any fix.

## ✅ GATE: Before proposing any fix

- [ ] You have identified the ROOT CAUSE (not just the symptom)
- [ ] You can explain in one sentence WHY the bug occurs
- [ ] You have verified the root cause by reading the code path

❌ STOP — if you propose a fix without knowing the root cause, you are guessing.
Guessing wastes time and creates new bugs. Investigate first.

---

## ✅ GATE: Before handing off

- [ ] Fix applied and verified: the test that was failing now passes
- [ ] No other tests broken: `make check` passes
- [ ] docs/orchestration/handoff.md updated with: root cause, fix applied, files changed

❌ STOP — if `make check` fails after your fix:
```
make orchestrate-check-failed
```

---

## ✅ GATE: Uncertainty check

If the root cause is unclear after investigation:
```
make orchestrate-block REASON="<what I found, what I still don't understand>"
```

---

## Debugging Process

### Phase 1: Reproduce
- Run the failing test: `uv run pytest tests/test_<file>.py::test_<name> -v`
- Read the full error message and traceback
- Note: what was expected, what happened, which line failed

### Phase 2: Trace
- Follow the call chain from the test to the failure point
- Read the source code at each step — do NOT assume

### Phase 3: Hypothesize
- Form ONE specific hypothesis: "The bug is because X does Y when it should do Z"
- Verify the hypothesis by reading the code — find the exact line

### Phase 4: Fix
- Write a regression test that would have caught this bug
- Apply the minimal fix
- Run `make check` — all tests must pass

## After fixing
```
make orchestrate-next
```
```

- [ ] **Step 5: Rewrite code-reviewer.agent.md**

```markdown
---
description: "Code review for quality, security, and correctness. Reads changed files from handoff.md. Writes review output to handoff.md and calls orchestrate-next."
tools: [read, search]
---
You are the code reviewer. You read code, write findings, and hand off — you do NOT edit code.

## ✅ GATE: Before starting review

- [ ] Read docs/orchestration/handoff.md — Changed Files section lists what to review
- [ ] Read docs/orchestration/human_input.md — any pending human guidance?
- [ ] You have read EVERY changed file listed in handoff.md

❌ STOP — do NOT review code you haven't fully read.

---

## ✅ GATE: Before writing review output

- [ ] Every finding has: severity (Critical/Major/Minor/Suggestion), location (file:line), and specific fix
- [ ] No vague findings like "improve error handling" — always say exactly what to change

---

## Review Checklist

### Quality
- [ ] Functions ≤50 lines? Extract helpers if longer
- [ ] Names are descriptive? (not `process()`, not `data`)
- [ ] DRY? Any 3+ line duplication?
- [ ] Single responsibility? Does each function do one thing?

### Security
- [ ] No hardcoded secrets, tokens, or API keys?
- [ ] No `eval()`, `exec()`, or `shell=True` with user input?
- [ ] All external input validated at boundaries?
- [ ] No bare `except:` swallowing errors silently?

### Tests
- [ ] Every new function has at least one test?
- [ ] Edge cases covered (None, empty, network error)?
- [ ] All external calls mocked?

### Types
- [ ] Public functions have type hints?
- [ ] No `Any` where a specific type works?

---

## Output format (write to handoff.md Output section)

```markdown
## Review: <PASS / FAIL>

### Critical (must fix before merge)
- `src/path/file.py:45` — [issue description] → [exact fix]

### Major (should fix)
- `src/path/file.py:89` — [issue] → [fix]

### Minor / Suggestions
- `src/path/file.py:12` — [suggestion]

### Summary
[1-2 sentences: overall quality assessment]
```

## After writing review
```
# If PASS:
make orchestrate-next

# If FAIL (has Critical or Major issues):
make orchestrate-next FAILED=1
```
```

- [ ] **Step 6: Commit all agent rewrites**

```bash
git add .github/agents/
git commit -m "feat(copilot): rewrite all agents with enforced workflow gates and handoff protocol"
```

---

## Task 12: setup.agent.md — Copilot onboarding agent

**Files:**
- Create: `.github/agents/setup.agent.md`

- [ ] **Step 1: Create the file**

```markdown
---
description: "Onboard a new project from this template. Asks 8 questions, then writes CLAUDE.md, copilot-instructions.md, .env.example, and docs/PROJECT.md. Use at the start of any new project."
tools: [read, edit, execute]
---
You are the setup agent. You guide a developer through configuring this template for a new project.

## ✅ GATE: Before writing any configuration

- [ ] You have asked ALL 8 questions and received answers (or explicit skips)
- [ ] You have confirmed the answers with the user before writing

❌ STOP — do NOT write any file before completing the questionnaire.

---

## The 8 Questions (ask one at a time, wait for answer)

1. **Project name and description**
   "What is the name of this project? And in one sentence: what does it do?"

2. **Project type**
   "What type of project is this?
   a) Python CLI tool
   b) HTTP API / web service
   c) Data pipeline / scraper
   d) AI agent / LLM app
   e) Other (describe)"

3. **External services**
   "Which external services or APIs will this project use? (e.g., Anthropic API, a database, Stripe, S3 — list all you know about now)"

4. **Team setup**
   "Is this a solo project or a team project?"

5. **Preferred starting agent**
   "Which tool do you prefer to start with?
   a) GitHub Copilot (this chat)
   b) Claude Code (terminal)"

6. **Parallel work with worktrees**
   "Do you want parallel agent workspaces set up? (git worktrees let two agents work on different branches at the same time)
   a) Yes — set up worktree support
   b) No — keep it simple"

7. **Telegram notifications**
   "Do you have a Telegram bot token and chat ID ready?
   a) Yes — I'll add them to .env
   b) No — skip for now"

8. **Knowledge base**
   "Do you want to pre-scrape any Medium articles for this project's domain?
   a) Yes — list the tags or URLs
   b) No — skip for now"

---

## After receiving all answers

Write these files (show user what you're writing):

### docs/PROJECT.md
```markdown
# <project name>

## Goal
<one sentence from answer 1>

## Type
<from answer 2>

## External Services
<from answer 3>

## Stack
Python 3.12, uv, ruff, mypy, pytest
<any additional from answers>

## Team
<solo / team size>

## Notifications
<Telegram: yes/no>
```

### .env.example additions
Add any new variables needed for the external services listed in answer 3.

### Update CLAUDE.md
Append a "Project Context" section with: project name, goal, type, key services.

### Update .github/copilot-instructions.md
Update the Architecture section with the project name and goal.

### First command to run
Print this exactly:
```
✅ Setup complete! Your next step:

make orchestrate-start TASK="<first feature from your project goal>"
```

---

## If Telegram was skipped
Add a note:
```
💡 To enable Telegram notifications later:
   Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env
   Then run: make bot
```
```

- [ ] **Step 2: Commit**

```bash
git add .github/agents/setup.agent.md
git commit -m "feat(copilot): add setup.agent.md for interactive project onboarding"
```

---

## Task 13: onboarding.py — Claude Code onboarding agent

**Files:**
- Create: `src/agents/onboarding.py`
- Create: `tests/test_onboarding.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_onboarding.py`:
```python
"""Tests for the interactive onboarding agent."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agents.onboarding import OnboardingAgent, QUESTIONS, write_project_doc


def test_questions_count():
    assert len(QUESTIONS) == 8


def test_write_project_doc_creates_file(tmp_path):
    answers = {
        "name": "TestBot",
        "description": "A test automation bot",
        "type": "Python CLI tool",
        "services": "Anthropic API",
        "team": "solo",
        "agent": "Claude Code",
        "worktrees": "No",
        "telegram": "Yes",
        "knowledge": "No",
    }
    out_file = tmp_path / "PROJECT.md"
    write_project_doc(answers, out_path=out_file)
    assert out_file.exists()
    content = out_file.read_text()
    assert "TestBot" in content
    assert "A test automation bot" in content
    assert "Anthropic API" in content


def test_onboarding_agent_has_system_prompt():
    agent = OnboardingAgent()
    assert "onboarding" in agent.system_prompt.lower()
    assert agent.name == "OnboardingAgent"


def test_onboarding_agent_collect_answers_returns_dict():
    agent = OnboardingAgent()
    responses = ["MyProject — a data pipeline", "c", "Anthropic API, S3",
                 "solo", "b", "a", "a", "b"]
    with patch("builtins.input", side_effect=responses):
        answers = agent.collect_answers()
    assert "name" in answers
    assert "type" in answers
    assert len(answers) == 8
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_onboarding.py -v
```
Expected: `ModuleNotFoundError: No module named 'agents.onboarding'`

- [ ] **Step 3: Create src/agents/onboarding.py**

```python
"""
Interactive new-project onboarding agent.

Asks 8 questions about the project and writes:
  - docs/PROJECT.md
  - Appends to CLAUDE.md
  - Updates .github/copilot-instructions.md
  - Updates .env.example
  - Prints the first make orchestrate-start command

Usage:
  make onboard
  uv run python -m agents.onboarding
"""

import sys
from pathlib import Path

from agents.base import BaseAgent

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DOC = BASE_DIR / "docs" / "PROJECT.md"
ENV_EXAMPLE = BASE_DIR / ".env.example"
CLAUDE_MD = BASE_DIR / "CLAUDE.md"
COPILOT_INSTRUCTIONS = BASE_DIR / ".github" / "copilot-instructions.md"

QUESTIONS = [
    ("name", "1. Project name and one-sentence description?\n   (e.g., 'DataBot — scrapes and summarizes financial reports')\n> "),
    ("type", "2. Project type?\n   a) Python CLI tool\n   b) HTTP API / web service\n   c) Data pipeline / scraper\n   d) AI agent / LLM app\n   e) Other (describe)\n> "),
    ("services", "3. External services/APIs this project will use?\n   (e.g., 'Anthropic API, PostgreSQL, S3' — or 'none')\n> "),
    ("team", "4. Solo or team project?\n> "),
    ("agent", "5. Preferred starting tool?\n   a) GitHub Copilot\n   b) Claude Code\n> "),
    ("worktrees", "6. Enable git worktrees for parallel agent workspaces?\n   a) Yes\n   b) No\n> "),
    ("telegram", "7. Telegram bot ready? (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)\n   a) Yes — I'll add to .env\n   b) No — skip\n> "),
    ("knowledge", "8. Pre-scrape Medium articles for this domain?\n   a) Yes — enter tags/URLs next\n   b) No\n> "),
]


class OnboardingAgent(BaseAgent):
    name = "OnboardingAgent"
    system_prompt = (
        "You are an onboarding assistant helping developers configure a new Python project. "
        "Be concise, friendly, and practical. Answer questions about the project setup."
    )

    def collect_answers(self) -> dict[str, str]:
        """Ask the 8 questions interactively and return answers dict."""
        answers: dict[str, str] = {}
        print("\n🚀 Welcome to AI Dev Starter!\n")
        print("I'll ask you 8 quick questions to configure this repo for your project.\n")
        for key, question in QUESTIONS:
            answer = input(question).strip()
            if not answer:
                answer = "skipped"
            answers[key] = answer
            print()
        return answers


def write_project_doc(answers: dict[str, str], out_path: Path = PROJECT_DOC) -> None:
    """Write docs/PROJECT.md from onboarding answers."""
    name_desc = answers.get("name", "Unnamed project")
    name = name_desc.split("—")[0].strip() if "—" in name_desc else name_desc
    description = name_desc.split("—")[1].strip() if "—" in name_desc else ""

    content = f"""# {name}

## Goal
{description or name_desc}

## Type
{answers.get('type', 'Not specified')}

## External Services
{answers.get('services', 'None specified')}

## Team
{answers.get('team', 'Not specified')}

## Stack
Python 3.12, uv, ruff, mypy, pytest, Anthropic API

## Notifications
Telegram: {'enabled' if answers.get('telegram', '').lower().startswith('a') else 'not configured'}

## Worktrees
Parallel agent workspaces: {'enabled' if answers.get('worktrees', '').lower().startswith('a') else 'disabled'}
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"✓ Written: {out_path.relative_to(BASE_DIR)}")


def _append_to_claude_md(answers: dict[str, str]) -> None:
    """Append project-specific context to CLAUDE.md."""
    name_desc = answers.get("name", "This project")
    section = f"""
---

## 12. Project Context (generated by make onboard)

**Name**: {name_desc}
**Type**: {answers.get('type', '?')}
**External services**: {answers.get('services', 'none')}
**Team**: {answers.get('team', 'solo')}
"""
    if CLAUDE_MD.exists():
        existing = CLAUDE_MD.read_text(encoding="utf-8")
        if "## 12. Project Context" not in existing:
            CLAUDE_MD.write_text(existing + section, encoding="utf-8")
            print(f"✓ Updated: CLAUDE.md")


def _update_copilot_instructions(answers: dict[str, str]) -> None:
    """Update project name/goal in copilot-instructions.md."""
    if not COPILOT_INSTRUCTIONS.exists():
        return
    name_desc = answers.get("name", "This project")
    content = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
    # Replace the header line
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# AI Dev Starter"):
            lines[i] = f"# {name_desc.split('—')[0].strip()} — Copilot Context"
            break
    COPILOT_INSTRUCTIONS.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ Updated: .github/copilot-instructions.md")


def _print_next_steps(answers: dict[str, str]) -> None:
    """Print the first command to run."""
    name = answers.get("name", "your project").split("—")[0].strip()
    desc = answers.get("name", "").split("—")[-1].strip() if "—" in answers.get("name", "") else ""
    first_task = f"set up {name}" if not desc else desc[:50]

    print("\n" + "=" * 60)
    print("✅ Setup complete!\n")
    print("Your next step:")
    print(f'\n  make orchestrate-start TASK="{first_task}"\n')
    if answers.get("knowledge", "").lower().startswith("a"):
        print("To pre-scrape your knowledge base:")
        print('  make scrape-tag TAG="<your domain tags>"\n')
    if answers.get("telegram", "").lower().startswith("b"):
        print("💡 To enable Telegram later:")
        print("   Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env")
        print("   Then run: make bot\n")
    print("=" * 60)


def main() -> None:
    try:
        agent = OnboardingAgent()
        answers = agent.collect_answers()
        print("Writing configuration files...")
        write_project_doc(answers)
        _append_to_claude_md(answers)
        _update_copilot_instructions(answers)
        _print_next_steps(answers)
    except KeyboardInterrupt:
        print("\n\nOnboarding cancelled.")
        sys.exit(0)
    except OSError as e:
        print(f"Error: {e}")
        print("(ANTHROPIC_API_KEY not required for onboarding — it uses CLI input)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_onboarding.py -v
```
Expected: all 4 tests pass

- [ ] **Step 5: Run quality gate**

```bash
uv run ruff check src/agents/onboarding.py
uv run mypy src/agents/onboarding.py
```

- [ ] **Step 6: Commit**

```bash
git add src/agents/onboarding.py tests/test_onboarding.py
git commit -m "feat(onboarding): add interactive project setup agent"
```

---

## Task 14: Template packaging

**Files:**
- Create: `TEMPLATE.md`

The `make template-clean` target was added in Task 6.

- [ ] **Step 1: Create TEMPLATE.md**

Create `TEMPLATE.md` at repo root:
```markdown
# Using This as a Template

5 steps to start a new project from this repo.

---

## Step 1: Clone and install

```bash
git clone https://github.com/your-org/ai-dev-starter my-new-project
cd my-new-project
make install
```

## Step 2: Configure secrets

```bash
cp .env.example .env
```

Edit `.env` — minimum needed:
```
ANTHROPIC_API_KEY=your-key-here
TELEGRAM_BOT_TOKEN=your-bot-token    # optional but recommended
TELEGRAM_CHAT_ID=your-chat-id        # optional but recommended
TELEGRAM_USER_ID=your-user-id        # optional but recommended
```

## Step 3: Install Claude Code superpowers

Open Claude Code terminal and run:
```
/plugin install superpowers@claude-plugins-official
/reload-plugins
```

## Step 4: Clean example data

```bash
make template-clean
```

This removes example Medium articles and resets orchestration state. All config, agents, and source code remain intact.

## Step 5: Start your first session

Run the interactive onboarding (optional but recommended):
```bash
make onboard
```

Or go straight to your first task:
```bash
make orchestrate-start TASK="your first feature description"
```

---

## What you get

| Tool | What's configured |
|------|------------------|
| **Claude Code** | `CLAUDE.md`, `.claude/commands/`, superpowers workflows |
| **GitHub Copilot** | `.github/copilot-instructions.md`, 6 agents with enforced gates |
| **Orchestration** | State machine, loop prevention, Telegram control |
| **CI** | GitHub Actions: lint + typecheck + test + Telegram on failure |
| **Quality** | ruff, mypy, pytest, pre-commit hooks |
| **Telegram** | Remote control bot + notifications |

---

## Daily workflow

```bash
make orchestrate-start TASK="add feature X"   # start
# work with Copilot or Claude Code
make orchestrate-next                           # hand off when done
# other agent picks up
make orchestrate-done                           # when task complete
make check                                      # before every commit
```

See `docs/GETTING-STARTED.md` for detailed guide.
```

- [ ] **Step 2: Commit**

```bash
git add TEMPLATE.md
git commit -m "docs: add TEMPLATE.md with 5-step new project setup guide"
```

---

## Task 15: Documentation updates

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/WORKTREES.md`

- [ ] **Step 1: Add orchestration section to CLAUDE.md**

Add after section 11 (Agentic Workflow) in `CLAUDE.md`:

```markdown
## 12. Orchestration Protocol

**State machine**: PLANNING → IMPLEMENTING → REVIEWING → DONE

**Shared files** (read at start of every phase):
- `docs/orchestration/session.json` — current phase, agent, iteration count
- `docs/orchestration/handoff.md` — plan/output/changed files from previous agent
- `docs/orchestration/human_input.md` — input from Telegram (clear after reading)

**Always check first**:
```bash
make orchestrate-status
```

**Hand off when done**:
```bash
make check                    # must pass
make orchestrate-next         # advance phase + Telegram notify
```

**Block when uncertain**:
```bash
make orchestrate-block REASON="<specific question>"
```

**Loop prevention** (automatic):
- 3 REVIEWING→FIXING cycles → BLOCKED + Telegram
- 2 consecutive `make check` failures → BLOCKED + Telegram
- Agent sets uncertainty → BLOCKED + Telegram

**Agent assignment**: Same agent plans + implements + first review. Other agent for second review only.

**Skills inventory**: See section 10 (Superpowers) for Claude Code skills. See `.github/copilot-instructions.md` section 8 for Copilot agents.
```

- [ ] **Step 2: Update docs/WORKTREES.md**

Read the file first, then append an "Orchestrator Integration" section:

```markdown
## Orchestrator Integration

Use `WORKTREE=1` when starting a session to automatically create a sibling worktree:

```bash
make orchestrate-start TASK="implement feature X" WORKTREE=1
```

This:
1. Creates `../ai-dev-starter-agent2/` on a new branch `feat/orchestration-<task>-agent2`
2. Stores the worktree path in `session.json`
3. Telegram message tells the second agent which directory to work from

The second agent runs:
```bash
cd ../ai-dev-starter-agent2
make orchestrate-status    # picks up the session
```

When complete, merge the worktree branch normally (human reviews and merges — orchestrator does NOT auto-merge).
```

- [ ] **Step 3: Run full quality gate**

```bash
make check
```
Expected: all checks pass

- [ ] **Step 4: Final commit**

```bash
git add CLAUDE.md docs/WORKTREES.md
git commit -m "docs: add orchestration protocol to CLAUDE.md and worktrees guide"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|-------------|----------------|
| State machine (session.json) | Task 1, 2 |
| Loop prevention (3 triggers) | Task 3 |
| Phase transitions + agent assignment | Task 4 |
| CLI commands (start/next/block/resume/status/done) | Task 5 |
| Makefile targets | Task 6 |
| Handoff.md format | Task 1, 2 (cmd_start creates template) |
| Human input via Telegram | Task 7, 8 |
| Session summary + document sending | Task 7 |
| Telegram commands (/stop /pause /resume /skip) | Task 8 |
| GitHub Actions Telegram on failure | Task 9 |
| GitHub Actions PR merge notification | Task 9 |
| .github/copilot-instructions.md | Task 10 |
| Copilot agents ✅/❌ gates | Task 11 |
| setup.agent.md | Task 12 |
| onboarding.py | Task 13 |
| make template-clean | Task 6 |
| TEMPLATE.md | Task 14 |
| CLAUDE.md orchestration section | Task 15 |
| docs/WORKTREES.md orchestrator integration | Task 15 |
| Worktree creation in cmd_start | Task 5 |

All 20 spec requirements covered. ✅
