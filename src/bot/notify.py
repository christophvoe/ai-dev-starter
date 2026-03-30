"""
Standalone Telegram notification module.

Send messages to Telegram without running the full bot.
Used for scrape reports, monitoring alerts, and CLI notifications.

Requires: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

Usage:
    python -m bot.notify "Your message here"
    make notify MSG="Scrape complete: 5 new articles"
"""

import logging
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

MAX_MESSAGE_LENGTH = 4096


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """Send a message to the configured Telegram chat.

    Returns True if sent successfully, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping notification")
        return False

    if not text.strip():
        log.warning("Empty message — skipping notification")
        return False

    # Telegram has a 4096 char limit
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 20] + "\n\n_(truncated)_"

    url = TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            log.info("Telegram notification sent")
            return True
        log.error("Telegram API error %s: %s", resp.status_code, resp.text[:200])
        return False
    except requests.RequestException as exc:
        log.error("Failed to send Telegram notification: %s", exc)
        return False


def send_scrape_report(
    total: int,
    new: int,
    skipped: int,
    source: str = "Medium",
    articles: list[str] | None = None,
) -> bool:
    """Send a formatted scrape report to Telegram."""
    lines = [
        f"*{source} Scrape Report*",
        f"Total: {total} | New: {new} | Skipped: {skipped}",
    ]
    if articles:
        lines.append("")
        lines.append("*New articles:*")
        for title in articles[:15]:
            # Escape markdown special chars in titles
            safe_title = title.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            lines.append(f"  • {safe_title}")
        if len(articles) > 15:
            lines.append(f"  _...and {len(articles) - 15} more_")

    return send_message("\n".join(lines))


def send_discover_report(
    tag: str,
    found: int,
    top_articles: list[dict[str, str]] | None = None,
) -> bool:
    """Send a discovery report to Telegram.

    top_articles: list of dicts with 'title' and optionally 'url' keys.
    """
    lines = [
        f"*Discovery Report: #{tag}*",
        f"Found {found} trending articles",
    ]
    if top_articles:
        lines.append("")
        for art in top_articles[:10]:
            title = art.get("title", "Untitled")
            safe_title = title.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            url = art.get("url", "")
            if url:
                lines.append(f"  • [{safe_title}]({url})")
            else:
                lines.append(f"  • {safe_title}")

    return send_message("\n".join(lines))


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
        f"*Session: {task}*",
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
        f"*Session BLOCKED*\n"
        f"Task: {task}\n"
        f"Phase: `{phase}` | Agent: `{agent}`\n"
        f"Reason: {reason}\n\n"
        f"Reply with guidance or run: `make orchestrate-resume`"
    )
    return send_message(text)


def main() -> None:
    """CLI entry point: python -m bot.notify 'message'"""
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m bot.notify 'Your message here'")
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        sys.exit(1)

    if send_message(message):
        print(f"Sent: {message[:80]}...")
    else:
        print("Failed to send notification")
        sys.exit(1)


if __name__ == "__main__":
    main()
