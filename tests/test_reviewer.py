"""Tests for agents.reviewer — AI code review module."""

from unittest.mock import MagicMock, patch

from agents.reviewer import REVIEW_SYSTEM_PROMPT, get_diff, review_diff


class TestGetDiff:
    @patch("agents.reviewer.subprocess.run")
    def test_get_diff_uncommitted(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="diff --git a/foo.py b/foo.py\n+new line"
        )
        result = get_diff()
        assert "diff --git" in result
        mock_run.assert_called_once_with(
            ["git", "diff", "HEAD"], capture_output=True, text=True, check=False
        )

    @patch("agents.reviewer.subprocess.run")
    def test_get_diff_branch(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="diff --git a/bar.py b/bar.py")
        result = get_diff("feat/retry")
        assert "diff --git" in result
        mock_run.assert_called_once_with(
            ["git", "diff", "main..feat/retry"], capture_output=True, text=True, check=False
        )

    @patch("agents.reviewer.subprocess.run")
    def test_get_diff_fallback_on_empty(self, mock_run: MagicMock) -> None:
        # First call returns empty (HEAD), second returns content (unstaged)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="unstaged changes"),
        ]
        result = get_diff()
        assert result == "unstaged changes"
        assert mock_run.call_count == 2

    @patch("agents.reviewer.subprocess.run")
    def test_get_diff_fallback_on_error(self, mock_run: MagicMock) -> None:
        # First call fails (HEAD), second returns content
        mock_run.side_effect = [
            MagicMock(returncode=128, stdout=""),
            MagicMock(returncode=0, stdout="cached diff"),
        ]
        result = get_diff()
        assert result == "cached diff"


class TestReviewDiff:
    @patch("agents.reviewer.BaseAgent")
    def test_review_diff_calls_agent(self, mock_agent_cls: MagicMock) -> None:
        mock_agent = MagicMock()
        mock_agent.complete.return_value = "APPROVE: looks good"
        mock_agent_cls.return_value = mock_agent

        result = review_diff("diff content here")
        assert result == "APPROVE: looks good"
        mock_agent.complete.assert_called_once()
        call_arg = mock_agent.complete.call_args[0][0]
        assert "diff content here" in call_arg

    @patch("agents.reviewer.BaseAgent")
    def test_review_diff_truncates_large_diff(self, mock_agent_cls: MagicMock) -> None:
        mock_agent = MagicMock()
        mock_agent.complete.return_value = "review"
        mock_agent_cls.return_value = mock_agent

        large_diff = "x" * 40000
        review_diff(large_diff)
        call_arg = mock_agent.complete.call_args[0][0]
        assert "truncated" in call_arg

    @patch("agents.reviewer.BaseAgent")
    def test_review_diff_custom_model(self, mock_agent_cls: MagicMock) -> None:
        mock_agent = MagicMock()
        mock_agent.complete.return_value = "ok"
        mock_agent_cls.return_value = mock_agent

        review_diff("diff", model="claude-sonnet-4-5")
        mock_agent_cls.assert_called_once_with(model="claude-sonnet-4-5", max_tokens=2048)


class TestSystemPrompt:
    def test_prompt_contains_project_standards(self) -> None:
        assert "ruff" in REVIEW_SYSTEM_PROMPT
        assert "mypy" in REVIEW_SYSTEM_PROMPT
        assert "pytest" in REVIEW_SYSTEM_PROMPT

    def test_prompt_requests_verdict(self) -> None:
        assert "APPROVE" in REVIEW_SYSTEM_PROMPT
        assert "REQUEST_CHANGES" in REVIEW_SYSTEM_PROMPT
