"""
Orchestration layer for GitHub Copilot <-> Claude Code multi-agent workflow.

State machine: PLANNING -> IMPLEMENTING -> REVIEWING -> DONE
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = PROJECT_DIR / "docs" / "orchestration"
KNOWLEDGE_DIR = PROJECT_DIR / "data" / "knowledge" / "raw" / "medium"
SESSION_FILE = DOCS_DIR / "session.json"
HANDOFF_FILE = DOCS_DIR / "handoff.md"
HUMAN_INPUT_FILE = DOCS_DIR / "human_input.md"

KNOWLEDGE_LOOKBACK_DAYS = 7
KNOWLEDGE_MAX_FILES = 8

MAX_ITERATIONS = 3
MAX_FAILED_CHECKS = 2

NEXT_PHASE: dict[str, str] = {
    "PLANNING": "IMPLEMENTING",
    "IMPLEMENTING": "REVIEWING",
    "REVIEWING": "DONE",
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
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def save_session(session: dict[str, Any], path: Path = SESSION_FILE) -> None:
    """Write session to disk, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")


def format_status(session: dict[str, Any]) -> str:
    """Format session state as a human-readable string."""
    return (
        f"Session: {session['task']}\n"
        f"Phase: {session['phase']} | Agent: {session['agent']}\n"
        f"Status: {session['status']}\n"
        f"Fix cycles: {session['iterations']}/{MAX_ITERATIONS} | "
        f"Failed checks: {session['failed_checks']}/{MAX_FAILED_CHECKS}\n"
        f"Uncertainty: {session['uncertainty']}"
    )


def check_loop_triggers(session: dict[str, Any]) -> tuple[bool, str]:
    """Return (should_block, reason). True means the session should be blocked now."""
    if session["iterations"] >= MAX_ITERATIONS:
        return (
            True,
            f"iteration limit reached ({session['iterations']}/{MAX_ITERATIONS} fix cycles)",
        )
    if session["failed_checks"] >= MAX_FAILED_CHECKS:
        return True, f"quality gate failed {session['failed_checks']} times consecutively"
    if session.get("uncertainty"):
        return True, "agent flagged uncertainty — human decision needed"
    return False, ""


def advance_phase(session: dict[str, Any], review_passed: bool = True) -> dict[str, Any]:
    """Compute and apply next phase + agent. Does NOT save to disk.

    - REVIEWING -> FIXING increments iterations (fix cycle counter).
    - FIXING -> REVIEWING switches to the other agent (fresh eyes).
    - All other transitions keep the same agent.
    """
    current_phase = session["phase"]
    current_agent = session["agent"]

    session["history"].append(
        {
            "phase": current_phase,
            "agent": current_agent,
            "completed_at": _now(),
        }
    )

    if current_phase == "REVIEWING" and not review_passed:
        next_p = "FIXING"
        session["iterations"] += 1
    else:
        next_p = NEXT_PHASE.get(current_phase, "DONE")

    session["phase"] = next_p
    session["agent"] = _other_agent(current_agent) if current_phase == "FIXING" else current_agent
    session["failed_checks"] = 0

    if next_p == "DONE":
        session["status"] = "DONE"

    return session


def _recent_knowledge_files(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[Path]:
    """Return recently modified scraped article files, newest first."""
    import time

    if not knowledge_dir.exists():
        return []
    cutoff = time.time() - KNOWLEDGE_LOOKBACK_DAYS * 86400
    files = [f for f in knowledge_dir.rglob("*.md") if f.stat().st_mtime >= cutoff]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[:KNOWLEDGE_MAX_FILES]


def _knowledge_section(knowledge_dir: Path = KNOWLEDGE_DIR) -> str:
    """Build the ## Knowledge section for handoff.md listing recent articles."""
    files = _recent_knowledge_files(knowledge_dir)
    if not files:
        return ""
    lines = [
        "\n## Knowledge\n",
        f"Recently scraped articles (last {KNOWLEDGE_LOOKBACK_DAYS} days) — read these before planning:\n",
    ]
    for f in files:
        try:
            rel = f.relative_to(PROJECT_DIR)
        except ValueError:
            rel = f
        lines.append(f"- {rel}")
    lines.append(
        "\nTip: ask your AI assistant to read these files for context before writing the plan.\n"
    )
    return "\n".join(lines)


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
                check=True,
                capture_output=True,
                cwd=str(Path.cwd()),
            )
            session["worktree"] = worktree_path
            print(f"Worktree created at {worktree_path} on branch {branch}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: could not create worktree: {e.stderr.decode()}")

    save_session(session, path)

    handoff = path.parent / "handoff.md"
    human_input = path.parent / "human_input.md"
    knowledge = _knowledge_section()
    handoff.write_text(
        f"## Task\n\n{task}\n\n"
        "## Changed Files\n\n\n"
        "## Output\n\n(test results, key observations)\n\n"
        "## Explanation\n\n(plain English: what was changed, why, and how)\n\n"
        "## Uncertainty\n\nNone" + knowledge,
        encoding="utf-8",
    )
    if not human_input.exists():
        human_input.write_text("", encoding="utf-8")

    msg = f"Session started\nTask: {task}\nPhase: PLANNING | Agent: {agent}"
    send_message(msg)
    print(msg)


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

    # Enforce loop-prevention immediately after a transition too. This catches
    # boundary cases like REVIEWING -> FIXING causing iterations to hit the limit.
    should_block_after, reason_after = check_loop_triggers(session)
    if should_block_after:
        save_session(session, path)
        cmd_block(reason_after, path=path)
        return

    save_session(session, path)

    if session["phase"] == "DONE":
        msg = f"Session complete\nTask: {session['task']}"
    else:
        msg = (
            f"Phase advance\n"
            f"Task: {session['task']}\n"
            f"{old_phase} ({old_agent}) -> {session['phase']} ({session['agent']})"
        )
    send_message(msg)
    print(msg)


def cmd_block(reason: str, path: Path = SESSION_FILE) -> None:
    """Block the session and alert via Telegram."""
    from bot.notify import send_message

    session = load_session(path)
    session["status"] = "BLOCKED"
    session["uncertainty"] = True
    save_session(session, path)

    msg = (
        f"Session BLOCKED\n"
        f"Task: {session['task']}\n"
        f"Phase: {session['phase']} | Agent: {session['agent']}\n"
        f"Reason: {reason}\n\n"
        f"Reply with guidance or run: make orchestrate-resume"
    )
    send_message(msg)
    print(msg)


def cmd_resume(path: Path = SESSION_FILE) -> None:
    """Clear BLOCKED/PAUSED status and print any pending human input."""
    from bot.notify import send_message

    session = load_session(path)
    session["status"] = "ACTIVE"
    session["uncertainty"] = False
    session["failed_checks"] = 0
    save_session(session, path)

    hi_file = path.parent / "human_input.md"
    human_input = ""
    if hi_file.exists():
        human_input = hi_file.read_text(encoding="utf-8").strip()

    msg = (
        f"Session resumed\n"
        f"Task: {session['task']}\n"
        f"Phase: {session['phase']} | Agent: {session['agent']}"
    )
    if human_input:
        msg += f"\n\nHuman input:\n{human_input}"
    send_message(msg)
    print(msg)


def cmd_status(path: Path = SESSION_FILE) -> None:
    """Print current session state."""
    session = load_session(path)
    print(format_status(session))


def cmd_done(path: Path = SESSION_FILE) -> None:
    """Mark session as DONE and send Telegram summary."""
    from bot.notify import send_session_summary

    session = load_session(path)
    session["status"] = "DONE"
    session["phase"] = "DONE"
    save_session(session, path)

    send_session_summary(session)
    print(f"Session complete: {session['task']}")


def cmd_explain(path: Path = SESSION_FILE) -> None:
    """Read the Explanation section from handoff.md and send it to Telegram."""
    from bot.notify import send_message

    session = load_session(path)
    handoff_path = path.parent / "handoff.md"

    if not handoff_path.exists():
        print("No handoff.md found.")
        return

    content = handoff_path.read_text(encoding="utf-8")

    # Extract the ## Explanation section if present, otherwise fall back to ## Output
    explanation = _extract_section(content, "Explanation") or _extract_section(content, "Output")

    if not explanation:
        print("No Explanation or Output section found in handoff.md.")
        return

    msg = (
        f"*Explanation — {session['task']}*\n"
        f"Phase: `{session['phase']}` | Agent: `{session['agent']}`\n\n"
        f"{explanation[:3500]}"
    )
    send_message(msg)
    print(f"Explanation sent to Telegram ({len(explanation)} chars).")


def _extract_section(content: str, heading: str) -> str:
    """Extract the text under a ## heading until the next ## heading."""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def cmd_check_failed(path: Path = SESSION_FILE) -> None:
    """Increment failed_checks. Blocks automatically if threshold reached."""
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


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _other_agent(agent: str) -> str:
    return "claude" if agent == "copilot" else "copilot"


def _task_slug(task: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]", "-", task.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:30]


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
    sub.add_parser("explain", help="Send Explanation from handoff.md to Telegram")

    args = parser.parse_args()

    dispatch: dict[str, Any] = {
        "start": lambda: cmd_start(args.task, args.agent, args.worktree),
        "next": lambda: cmd_next(review_passed=not args.failed),
        "block": lambda: cmd_block(args.reason),
        "resume": cmd_resume,
        "status": cmd_status,
        "done": cmd_done,
        "check-failed": cmd_check_failed,
        "explain": cmd_explain,
    }

    if args.command in dispatch:
        dispatch[args.command]()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
