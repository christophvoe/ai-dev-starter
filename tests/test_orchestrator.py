"""Tests for orchestrator state machine — Tasks 2-5."""

import json
from unittest.mock import patch

import pytest

from agents.orchestrator import (
    advance_phase,
    check_loop_triggers,
    cmd_block,
    cmd_check_failed,
    cmd_done,
    cmd_explain,
    cmd_next,
    cmd_resume,
    cmd_start,
    empty_session,
    format_status,
    load_session,
    save_session,
)

# ── Task 2: data structures and file I/O ──────────────────────────────────────


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


# ── Task 3: loop prevention ───────────────────────────────────────────────────


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


# ── Task 4: phase transitions ─────────────────────────────────────────────────


def test_planning_to_implementing_same_agent():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "PLANNING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "IMPLEMENTING"
    assert result["agent"] == "copilot"


def test_implementing_to_reviewing_same_agent():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "IMPLEMENTING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "REVIEWING"
    assert result["agent"] == "copilot"


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
    assert result["agent"] == "copilot"
    assert result["iterations"] == 1


def test_fixing_to_reviewing_switches_agent():
    s = empty_session()
    s["agent"] = "copilot"
    s["phase"] = "FIXING"
    result = advance_phase(s, review_passed=True)
    assert result["phase"] == "REVIEWING"
    assert result["agent"] == "claude"


def test_advance_phase_records_history():
    s = empty_session()
    s["phase"] = "PLANNING"
    s["agent"] = "claude"
    result = advance_phase(s)
    assert len(result["history"]) == 1
    assert result["history"][0]["phase"] == "PLANNING"
    assert result["history"][0]["agent"] == "claude"


# ── Task 5: CLI commands ──────────────────────────────────────────────────────


def test_cmd_start_creates_session(tmp_path):
    session_path = tmp_path / "session.json"
    with patch("bot.notify.send_message"):
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
    with patch("bot.notify.send_message"):
        cmd_next(review_passed=True, path=session_path)
    updated = load_session(path=session_path)
    assert updated["phase"] == "IMPLEMENTING"


def test_cmd_next_blocks_on_loop_trigger(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["iterations"] = 3
    save_session(s, path=session_path)
    with patch("bot.notify.send_message") as mock_send:
        cmd_next(review_passed=True, path=session_path)
    updated = load_session(path=session_path)
    assert updated["status"] == "BLOCKED"
    assert mock_send.called


def test_cmd_block_sets_blocked(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    with patch("bot.notify.send_message"):
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
    with patch("bot.notify.send_message"):
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
    with patch("bot.notify.send_message"), patch("bot.notify.send_session_summary"):
        cmd_done(path=session_path)
    updated = load_session(path=session_path)
    assert updated["status"] == "DONE"
    assert updated["phase"] == "DONE"


def test_cmd_check_failed_increments_counter(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    with patch("bot.notify.send_message"):
        cmd_check_failed(path=session_path)
    updated = load_session(path=session_path)
    assert updated["failed_checks"] == 1


def test_cmd_check_failed_blocks_at_threshold(tmp_path):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["failed_checks"] = 1
    save_session(s, path=session_path)
    with patch("bot.notify.send_message"):
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


def test_cmd_next_blocks_when_review_failure_hits_iteration_limit(tmp_path):
    """REVIEWING -> FIXING that reaches iterations==3 should block immediately."""
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    s["phase"] = "REVIEWING"
    s["iterations"] = 2
    save_session(s, path=session_path)
    with patch("bot.notify.send_message"):
        cmd_next(review_passed=False, path=session_path)

    updated = load_session(path=session_path)
    assert updated["status"] == "BLOCKED"
    assert updated["phase"] == "FIXING"
    assert updated["iterations"] == 3


# ── cmd_explain ───────────────────────────────────────────────────────────────


def test_cmd_explain_sends_explanation_section(tmp_path):
    session_path = tmp_path / "session.json"
    handoff_path = tmp_path / "handoff.md"
    s = empty_session()
    s["task"] = "add feature X"
    save_session(s, path=session_path)
    handoff_path.write_text(
        "## Task\nAdd feature X\n\n"
        "## Changed Files\n- src/x.py:10-20\n\n"
        "## Output\n5 tests passed\n\n"
        "## Explanation\nWe added function foo() which does bar. "
        "It works by iterating over the list and calling baz().\n\n"
        "## Uncertainty\nNone\n",
        encoding="utf-8",
    )
    sent = []
    with patch("bot.notify.send_message", side_effect=lambda msg, **kw: sent.append(msg)):
        cmd_explain(path=session_path)

    assert len(sent) == 1
    assert "add feature X" in sent[0]
    assert "function foo()" in sent[0]


def test_cmd_explain_falls_back_to_output_section(tmp_path):
    session_path = tmp_path / "session.json"
    handoff_path = tmp_path / "handoff.md"
    s = empty_session()
    s["task"] = "fix bug"
    save_session(s, path=session_path)
    # No Explanation section — only Output
    handoff_path.write_text(
        "## Task\nFix bug\n\n## Output\nFixed the null pointer in line 42.\n\n## Uncertainty\nNone\n",
        encoding="utf-8",
    )
    sent = []
    with patch("bot.notify.send_message", side_effect=lambda msg, **kw: sent.append(msg)):
        cmd_explain(path=session_path)

    assert "null pointer" in sent[0]


def test_cmd_explain_no_handoff_file(tmp_path, capsys):
    session_path = tmp_path / "session.json"
    s = empty_session()
    s["task"] = "test"
    save_session(s, path=session_path)
    cmd_explain(path=session_path)
    out = capsys.readouterr().out
    assert "No handoff.md" in out
