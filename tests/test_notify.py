"""Tests for src/bot/notify.py — Telegram notification module."""

from unittest.mock import MagicMock, patch

from bot.notify import (
    MAX_MESSAGE_LENGTH,
    send_discover_report,
    send_message,
    send_scrape_report,
)

# ── send_message ─────────────────────────────────────────────────────────────


class TestSendMessage:
    """Tests for the send_message function."""

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    @patch("bot.notify.requests.post")
    def test_send_message_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        assert send_message("Hello!") is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["text"] == "Hello!"
        assert call_kwargs[1]["json"]["chat_id"] == "12345"

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    @patch("bot.notify.requests.post")
    def test_send_message_api_error(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=403, text="Forbidden")
        assert send_message("Hello!") is False

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    def test_send_message_no_token(self) -> None:
        assert send_message("Hello!") is False

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "")
    def test_send_message_no_chat_id(self) -> None:
        assert send_message("Hello!") is False

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    def test_send_message_empty_text(self) -> None:
        assert send_message("") is False
        assert send_message("   ") is False

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    @patch("bot.notify.requests.post")
    def test_send_message_truncates_long_text(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        long_text = "x" * 5000
        send_message(long_text)
        sent_text = mock_post.call_args[1]["json"]["text"]
        assert len(sent_text) <= MAX_MESSAGE_LENGTH
        assert sent_text.endswith("_(truncated)_")

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    @patch("bot.notify.requests.post")
    def test_send_message_network_error(self, mock_post: MagicMock) -> None:
        import requests

        mock_post.side_effect = requests.ConnectionError("timeout")
        assert send_message("Hello!") is False

    @patch("bot.notify.TELEGRAM_BOT_TOKEN", "fake-token")
    @patch("bot.notify.TELEGRAM_CHAT_ID", "12345")
    @patch("bot.notify.requests.post")
    def test_send_message_parse_mode(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        send_message("Hello!", parse_mode="HTML")
        assert mock_post.call_args[1]["json"]["parse_mode"] == "HTML"


# ── send_scrape_report ───────────────────────────────────────────────────────


class TestSendScrapeReport:
    """Tests for the send_scrape_report function."""

    @patch("bot.notify.send_message")
    def test_scrape_report_basic(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        result = send_scrape_report(total=10, new=3, skipped=7)
        assert result is True
        msg = mock_send.call_args[0][0]
        assert "10" in msg
        assert "3" in msg
        assert "7" in msg

    @patch("bot.notify.send_message")
    def test_scrape_report_with_articles(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        articles = ["Article One", "Article Two"]
        send_scrape_report(total=5, new=2, skipped=3, articles=articles)
        msg = mock_send.call_args[0][0]
        assert "Article One" in msg
        assert "Article Two" in msg

    @patch("bot.notify.send_message")
    def test_scrape_report_custom_source(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        send_scrape_report(total=1, new=1, skipped=0, source="Dev.to")
        msg = mock_send.call_args[0][0]
        assert "Dev.to" in msg

    @patch("bot.notify.send_message")
    def test_scrape_report_truncates_many_articles(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        articles = [f"Article {i}" for i in range(20)]
        send_scrape_report(total=20, new=20, skipped=0, articles=articles)
        msg = mock_send.call_args[0][0]
        assert "...and 5 more" in msg

    @patch("bot.notify.send_message")
    def test_scrape_report_escapes_markdown(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        articles = ["Article *with* _special_ `chars`"]
        send_scrape_report(total=1, new=1, skipped=0, articles=articles)
        msg = mock_send.call_args[0][0]
        assert "\\*with\\*" in msg
        assert "\\_special\\_" in msg


# ── send_discover_report ─────────────────────────────────────────────────────


class TestSendDiscoverReport:
    """Tests for the send_discover_report function."""

    @patch("bot.notify.send_message")
    def test_discover_report_basic(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        result = send_discover_report(tag="ai-agents", found=15)
        assert result is True
        msg = mock_send.call_args[0][0]
        assert "ai-agents" in msg
        assert "15" in msg

    @patch("bot.notify.send_message")
    def test_discover_report_with_articles(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        articles = [
            {"title": "Cool Article", "url": "https://medium.com/cool"},
            {"title": "Another One"},
        ]
        send_discover_report(tag="llm", found=2, top_articles=articles)
        msg = mock_send.call_args[0][0]
        assert "Cool Article" in msg
        assert "https://medium.com/cool" in msg
        assert "Another One" in msg

    @patch("bot.notify.send_message")
    def test_discover_report_no_articles(self, mock_send: MagicMock) -> None:
        mock_send.return_value = True
        send_discover_report(tag="python", found=0)
        msg = mock_send.call_args[0][0]
        assert "python" in msg
        assert "0" in msg
