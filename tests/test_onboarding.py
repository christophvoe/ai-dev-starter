"""Tests for src/agents/onboarding.py."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agents.onboarding import (
    QUESTIONS,
    _parse_name,
    append_to_claude_md,
    collect_answers,
    print_next_steps,
    promote_to_repo,
    update_copilot_instructions,
    update_env_example,
    write_project_doc,
)

# ── Unit tests ────────────────────────────────────────────────────────────────


def test_questions_count() -> None:
    assert len(QUESTIONS) == 8  # name, type, services, team, tools, worktrees, telegram, knowledge


def test_questions_have_keys_and_prompts() -> None:
    for key, prompt in QUESTIONS:
        assert key, "Each question must have a non-empty key"
        assert prompt, "Each question must have a non-empty prompt"


def test_parse_name_em_dash() -> None:
    name, desc = _parse_name("MyBot — scrapes financial reports")
    assert name == "MyBot"
    assert desc == "scrapes financial reports"


def test_parse_name_hyphen() -> None:
    name, desc = _parse_name("MyBot - scrapes financial reports")
    assert name == "MyBot"
    assert desc == "scrapes financial reports"


def test_parse_name_no_separator() -> None:
    name, desc = _parse_name("SimpleProject")
    assert name == "SimpleProject"
    assert desc == ""


def test_parse_name_strips_whitespace() -> None:
    name, desc = _parse_name("  DataBot  —  my description  ")
    assert name == "DataBot"
    assert desc == "my description"


# ── write_project_doc ─────────────────────────────────────────────────────────


def test_write_project_doc_creates_file(tmp_path: Path) -> None:
    answers = {
        "name": "TestBot — does cool stuff",
        "type": "d) AI agent / LLM app",
        "services": "Anthropic API",
        "team": "solo",
        "telegram": "a",
        "worktrees": "a",
    }
    out = tmp_path / "PROJECT.md"
    write_project_doc(answers, out_path=out)
    assert out.exists()


def test_write_project_doc_content(tmp_path: Path) -> None:
    answers = {
        "name": "TestBot — does cool stuff",
        "type": "d) AI agent / LLM app",
        "services": "Anthropic API",
        "team": "solo",
        "telegram": "a",
        "worktrees": "b",
    }
    out = tmp_path / "PROJECT.md"
    write_project_doc(answers, out_path=out)
    content = out.read_text(encoding="utf-8")
    assert "# TestBot" in content
    assert "does cool stuff" in content
    assert "Anthropic API" in content
    assert "solo" in content
    assert "enabled" in content  # telegram = a
    assert "disabled" in content  # worktrees = b


def test_write_project_doc_telegram_not_configured(tmp_path: Path) -> None:
    answers = {
        "name": "X",
        "type": "a",
        "services": "none",
        "team": "solo",
        "telegram": "b",
        "worktrees": "b",
    }
    out = tmp_path / "PROJECT.md"
    write_project_doc(answers, out_path=out)
    content = out.read_text(encoding="utf-8")
    assert "not configured" in content


def test_write_project_doc_creates_parent_dir(tmp_path: Path) -> None:
    answers = {
        "name": "X",
        "type": "a",
        "services": "none",
        "team": "solo",
        "telegram": "b",
        "worktrees": "b",
    }
    out = tmp_path / "nested" / "deep" / "PROJECT.md"
    write_project_doc(answers, out_path=out)
    assert out.exists()


# ── append_to_claude_md ───────────────────────────────────────────────────────


def test_append_to_claude_md_adds_section(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing content\n\nSome text.\n", encoding="utf-8")
    answers = {
        "name": "TestBot — test",
        "type": "b) HTTP API",
        "services": "PostgreSQL",
        "team": "team of 3",
        "tools": "b",  # Claude Code only
    }

    with patch("agents.onboarding.CLAUDE_MD", claude_md):
        append_to_claude_md(answers)

    content = claude_md.read_text(encoding="utf-8")
    assert "## 12. Project Context" in content
    assert "TestBot" in content
    assert "b) HTTP API" in content
    assert "PostgreSQL" in content


def test_append_to_claude_md_skipped_when_copilot_only(tmp_path: Path) -> None:
    """Should not update CLAUDE.md when only Copilot is selected."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing\n", encoding="utf-8")
    answers = {"name": "Bot", "type": "a", "services": "none", "team": "solo", "tools": "c"}

    with patch("agents.onboarding.CLAUDE_MD", claude_md):
        append_to_claude_md(answers)

    content = claude_md.read_text(encoding="utf-8")
    assert "## 12. Project Context" not in content


def test_append_to_claude_md_idempotent(tmp_path: Path) -> None:
    """Should not double-append the section."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing\n", encoding="utf-8")
    answers = {"name": "Bot", "type": "a", "services": "none", "team": "solo", "tools": "a"}

    with patch("agents.onboarding.CLAUDE_MD", claude_md):
        append_to_claude_md(answers)
        append_to_claude_md(answers)

    content = claude_md.read_text(encoding="utf-8")
    assert content.count("## 12. Project Context") == 1


def test_append_to_claude_md_missing_file(tmp_path: Path) -> None:
    """Should not crash if CLAUDE.md doesn't exist."""
    missing = tmp_path / "CLAUDE.md"
    answers = {"name": "Bot", "type": "a", "services": "none", "team": "solo", "tools": "b"}
    with patch("agents.onboarding.CLAUDE_MD", missing):
        append_to_claude_md(answers)  # should not raise


# ── update_copilot_instructions ───────────────────────────────────────────────


def test_update_copilot_instructions_renames_header(tmp_path: Path) -> None:
    ci = tmp_path / "copilot-instructions.md"
    ci.write_text("# AI Dev Starter — GitHub Copilot Context\n\nSome content.\n", encoding="utf-8")
    answers = {"name": "NewProject — cool stuff", "tools": "a"}  # both tools

    with patch("agents.onboarding.COPILOT_INSTRUCTIONS", ci):
        update_copilot_instructions(answers)

    content = ci.read_text(encoding="utf-8")
    assert "# NewProject — GitHub Copilot Context" in content
    assert "AI Dev Starter" not in content


def test_update_copilot_instructions_skipped_when_claude_only(tmp_path: Path) -> None:
    """Should not update copilot-instructions.md when only Claude Code is selected."""
    ci = tmp_path / "copilot-instructions.md"
    ci.write_text("# AI Dev Starter — GitHub Copilot Context\n", encoding="utf-8")
    answers = {"name": "NewProject", "tools": "b"}  # Claude Code only

    with patch("agents.onboarding.COPILOT_INSTRUCTIONS", ci):
        update_copilot_instructions(answers)

    content = ci.read_text(encoding="utf-8")
    assert "AI Dev Starter" in content  # unchanged


def test_update_copilot_instructions_missing_file(tmp_path: Path) -> None:
    """Should silently skip if file doesn't exist."""
    missing = tmp_path / "copilot-instructions.md"
    answers = {"name": "Bot", "tools": "a"}
    with patch("agents.onboarding.COPILOT_INSTRUCTIONS", missing):
        update_copilot_instructions(answers)  # should not raise


# ── collect_answers ───────────────────────────────────────────────────────────


def test_collect_answers_returns_dict() -> None:
    # name, type, services, team, tools, worktrees, telegram, knowledge(=b — no tag prompt)
    inputs = ["MyBot — cool project", "d", "Anthropic API", "solo", "a", "b", "a", "b"]
    with patch("builtins.input", side_effect=inputs):
        answers = collect_answers()

    assert isinstance(answers, dict)
    assert answers["name"] == "MyBot — cool project"
    assert answers["type"] == "d"
    assert answers["team"] == "solo"
    assert answers["tools"] == "a"


def test_collect_answers_with_scrape_tags() -> None:
    """When knowledge=a, an extra tag prompt is shown."""
    # name, type, services, team, tools, worktrees, telegram, knowledge=a, tags
    inputs = ["MyBot — test", "d", "none", "solo", "b", "b", "b", "a", "ai-agents, llm"]
    with patch("builtins.input", side_effect=inputs):
        answers = collect_answers()

    assert answers["knowledge"] == "a"
    assert answers["scrape_tags"] == "ai-agents, llm"


def test_collect_answers_empty_input_becomes_skipped() -> None:
    # 8 empty answers — knowledge="skipped" so no tag prompt
    inputs = [""] * 8
    with patch("builtins.input", side_effect=inputs):
        answers = collect_answers()

    assert answers["name"] == "skipped"
    assert answers["tools"] == "skipped"


# ── print_next_steps ──────────────────────────────────────────────────────────


def test_print_next_steps_includes_orchestrate_command(capsys: pytest.CaptureFixture) -> None:
    answers = {"name": "MyBot — scrape stuff", "tools": "a", "knowledge": "b", "telegram": "a"}
    print_next_steps(answers)
    out = capsys.readouterr().out
    assert "make orchestrate-start" in out


def test_print_next_steps_shows_claude_hint_when_claude_only(
    capsys: pytest.CaptureFixture,
) -> None:
    answers = {"name": "MyBot — test", "tools": "b", "knowledge": "b", "telegram": "a"}
    print_next_steps(answers)
    out = capsys.readouterr().out
    assert "Claude Code" in out
    assert "@orchestrator" not in out  # Copilot hint should NOT appear


def test_print_next_steps_shows_copilot_hint_when_copilot_only(
    capsys: pytest.CaptureFixture,
) -> None:
    answers = {"name": "MyBot — test", "tools": "c", "knowledge": "b", "telegram": "a"}
    print_next_steps(answers)
    out = capsys.readouterr().out
    assert "@orchestrator" in out
    assert "Claude Code" not in out


def test_print_next_steps_shows_telegram_hint_when_skipped(capsys: pytest.CaptureFixture) -> None:
    answers = {"name": "MyBot — test", "tools": "a", "knowledge": "b", "telegram": "b"}
    print_next_steps(answers)
    out = capsys.readouterr().out
    assert "TELEGRAM_BOT_TOKEN" in out


def test_print_next_steps_includes_worktree_flag_when_enabled(
    capsys: pytest.CaptureFixture,
) -> None:
    answers = {
        "name": "MyBot — test",
        "tools": "a",
        "knowledge": "b",
        "telegram": "a",
        "worktrees": "a",
    }
    print_next_steps(answers)
    out = capsys.readouterr().out
    assert "WORKTREE=1" in out


def test_print_next_steps_no_tool_plain_template(capsys: pytest.CaptureFixture) -> None:
    answers = {"name": "SimpleApp", "tools": "d", "knowledge": "b", "telegram": "b"}
    print_next_steps(answers)
    out = capsys.readouterr().out
    assert "make check" in out
    assert "orchestrate-start" not in out


# ── promote_to_repo ────────────────────────────────────────────────────────────


def test_promote_copies_agents_dir(tmp_path: Path) -> None:
    """Agent files should be copied into target/.github/agents/."""
    target = tmp_path / "target_repo"
    target.mkdir()

    src_agents = tmp_path / "fake_src" / ".github" / "agents"
    src_agents.mkdir(parents=True)
    (src_agents / "orchestrator.agent.md").write_text("# Orchestrator\n", encoding="utf-8")

    from unittest.mock import patch

    import agents.onboarding as onboarding_mod

    with patch.object(onboarding_mod, "BASE_DIR", tmp_path / "fake_src"):
        promote_to_repo(target)

    copied = target / ".github" / "agents" / "orchestrator.agent.md"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "# Orchestrator\n"


def test_promote_skips_existing_files(tmp_path: Path) -> None:
    """Existing files in target should NOT be overwritten."""
    target = tmp_path / "target_repo"
    (target / ".github" / "agents").mkdir(parents=True)
    existing = target / ".github" / "agents" / "orchestrator.agent.md"
    existing.write_text("original content\n", encoding="utf-8")

    src_agents = tmp_path / "fake_src" / ".github" / "agents"
    src_agents.mkdir(parents=True)
    (src_agents / "orchestrator.agent.md").write_text("new content\n", encoding="utf-8")

    from unittest.mock import patch

    import agents.onboarding as onboarding_mod

    with patch.object(onboarding_mod, "BASE_DIR", tmp_path / "fake_src"):
        promote_to_repo(target)

    assert existing.read_text(encoding="utf-8") == "original content\n"


def test_promote_appends_to_claude_md(tmp_path: Path) -> None:
    """Should append the ai-dev-starter section to target CLAUDE.md."""
    target = tmp_path / "target_repo"
    target.mkdir()
    claude_md = target / "CLAUDE.md"
    claude_md.write_text("# My Project\n\nSome content.\n", encoding="utf-8")

    from unittest.mock import patch

    import agents.onboarding as onboarding_mod

    fake_src = tmp_path / "fake_src"
    fake_src.mkdir()

    with patch.object(onboarding_mod, "BASE_DIR", fake_src):
        promote_to_repo(target)

    content = claude_md.read_text(encoding="utf-8")
    assert "## AI Dev Starter tooling" in content
    assert "make scrape-tag" in content


def test_promote_does_not_duplicate_claude_md_section(tmp_path: Path) -> None:
    """Running promote twice should not double-append the section."""
    target = tmp_path / "target_repo"
    target.mkdir()
    claude_md = target / "CLAUDE.md"
    claude_md.write_text("# My Project\n", encoding="utf-8")

    from unittest.mock import patch

    import agents.onboarding as onboarding_mod

    fake_src = tmp_path / "fake_src"
    fake_src.mkdir()

    with patch.object(onboarding_mod, "BASE_DIR", fake_src):
        promote_to_repo(target)
        promote_to_repo(target)

    content = claude_md.read_text(encoding="utf-8")
    assert content.count("## AI Dev Starter tooling") == 1


def test_promote_exits_if_target_missing(tmp_path: Path) -> None:
    """Should exit with error if target path doesn't exist."""
    missing = tmp_path / "nonexistent"
    with pytest.raises(SystemExit):
        promote_to_repo(missing)


def test_promote_skips_copilot_instructions_if_exists(tmp_path: Path) -> None:
    """copilot-instructions.md should NOT be overwritten if already present in target."""
    target = tmp_path / "target_repo"
    (target / ".github").mkdir(parents=True)
    ci = target / ".github" / "copilot-instructions.md"
    ci.write_text("# My own instructions\n", encoding="utf-8")

    src_github = tmp_path / "fake_src" / ".github"
    src_github.mkdir(parents=True)
    (src_github / "copilot-instructions.md").write_text("# AI Dev Starter\n", encoding="utf-8")

    from unittest.mock import patch

    import agents.onboarding as onboarding_mod

    with patch.object(onboarding_mod, "BASE_DIR", tmp_path / "fake_src"):
        promote_to_repo(target)

    assert ci.read_text(encoding="utf-8") == "# My own instructions\n"


def test_update_env_example_adds_missing_vars(tmp_path: Path) -> None:
    env_example = tmp_path / ".env.example"
    env_example.write_text("OPENAI_API_KEY=\n", encoding="utf-8")

    answers = {
        "services": "Anthropic API, PostgreSQL, Custom CRM",
        "telegram": "a",
    }
    update_env_example(answers, env_example_path=env_example)

    content = env_example.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY=" in content
    assert "DATABASE_URL=" in content
    assert "CUSTOM_CRM_API_KEY=" in content
    assert "TELEGRAM_BOT_TOKEN=" in content
    assert "TELEGRAM_CHAT_ID=" in content
    assert "TELEGRAM_USER_ID=" in content


def test_update_env_example_does_not_duplicate_existing_vars(tmp_path: Path) -> None:
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "OPENAI_API_KEY=\nANTHROPIC_API_KEY=\nDATABASE_URL=\nTELEGRAM_BOT_TOKEN=\n",
        encoding="utf-8",
    )

    answers = {
        "services": "Anthropic API, PostgreSQL",
        "telegram": "a",
    }
    update_env_example(answers, env_example_path=env_example)

    content = env_example.read_text(encoding="utf-8")
    assert content.count("ANTHROPIC_API_KEY=") == 1
    assert content.count("DATABASE_URL=") == 1
    assert content.count("TELEGRAM_BOT_TOKEN=") == 1
