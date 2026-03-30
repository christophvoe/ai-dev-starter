"""Tests for bot.telegram_bot path and subprocess behavior."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from bot import telegram_bot


def test_orchestration_dir_is_repo_relative() -> None:
    assert telegram_bot.ORCHESTRATION_DIR == telegram_bot.REPO_ROOT / "docs" / "orchestration"


def test_run_uses_repo_root_and_pythonpath() -> None:
    with patch("bot.telegram_bot.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="")
        output = telegram_bot._run(["python", "-m", "pytest", "tests/", "-q"])

    assert output == "ok"
    _, kwargs = mock_run.call_args
    assert kwargs["cwd"] == str(telegram_bot.REPO_ROOT)
    assert kwargs["env"]["PYTHONPATH"] == str(telegram_bot.REPO_ROOT / "src")


def test_repo_root_points_to_workspace_root() -> None:
    assert (telegram_bot.REPO_ROOT / "pyproject.toml").exists()
    assert Path(telegram_bot.REPO_ROOT / "src").exists()
