"""
Minimal self-hosted Telegram bot.

Requires:
  uv add python-telegram-bot
  TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID in .env

The bot accepts two commands:
  /status  → runs `python src/main.py` and returns output
  /scrape  → triggers the Medium scraper for your account
  /ask <question> → queries your knowledge base

Security: all messages from unknown users are silently ignored.
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add src/ to path when running from project root
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))


def _run(cmd: list[str], timeout: int = 60) -> str:
    """Run a subprocess and return its stdout/stderr, truncated to 3000 chars."""
    env = {**os.environ, "PYTHONPATH": str(BASE_DIR / "src")}
    try:
        result = subprocess.run(
            ["uv", "run", *cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR),
            env=env,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:3000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "⚠ Command timed out."
    except Exception as exc:
        return f"⚠ Error: {exc}"


async def start_bot() -> None:
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
    except ImportError:
        print("Run: uv add python-telegram-bot")
        sys.exit(1)

    if not BOT_TOKEN:
        print("Set TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    def _guard(func):
        """Decorator: silently ignore messages from anyone but ALLOWED_USER_ID."""

        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.effective_user and update.effective_user.id != ALLOWED_USER_ID:
                log.warning("Rejected message from user %s", update.effective_user.id)
                return
            await func(update, context)

        return wrapper

    @_guard
    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Running status check...")
        output = _run(["python", "src/main.py"])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

    @_guard
    async def cmd_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Scraping Medium articles...")
        output = _run(["python", "src/main.py", "--scrape"], timeout=120)
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

    @_guard
    async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
        question = " ".join(context.args) if context.args else ""
        if not question:
            await update.message.reply_text("Usage: /ask <your question>")
            return
        # Simple knowledge-base search: list matching article titles
        kb_dir = BASE_DIR / "data" / "knowledge" / "raw" / "medium"
        matches = []
        if kb_dir.exists():
            q_lower = question.lower()
            for md_file in sorted(kb_dir.glob("*.md")):
                if q_lower in md_file.stem.lower():
                    matches.append(md_file.stem)
        if matches:
            reply = f"Articles matching '{question}':\n" + "\n".join(
                f"  • {m}" for m in matches[:10]
            )
        else:
            reply = (
                f"No articles found matching '{question}'.\n"
                f"Run /scrape to fetch articles, then try again.\n"
                f"Or use Copilot Chat in VS Code for deeper questions."
            )
        await update.message.reply_text(reply)

    @_guard
    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/status — project status\n"
            "/scrape — fetch Medium articles\n"
            "/ask <question> — query knowledge base\n"
            "/help — this message"
        )

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("scrape", cmd_scrape))
    app.add_handler(CommandHandler("ask", cmd_ask))

    print(f"Bot started. Send /help to your bot on Telegram (user ID: {ALLOWED_USER_ID}).")
    await app.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_bot())
