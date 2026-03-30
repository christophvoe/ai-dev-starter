"""
Minimal self-hosted Telegram bot.

Requires:
  uv add python-telegram-bot
  TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID in .env

Commands:
  /status   → runs `python src/main.py` and returns output
  /scrape   → triggers the Medium scraper + sends notification
  /discover → discover trending articles by tag
  /review   → AI code review of uncommitted changes or a branch
  /check    → run make check (lint + types + tests)
  /ask      → queries your knowledge base
  /help     → list commands

Security: all messages from unknown users are silently ignored.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Repository root for command execution and docs/orchestration files.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))

ORCHESTRATION_DIR = REPO_ROOT / "docs" / "orchestration"
SESSION_FILE = ORCHESTRATION_DIR / "session.json"
HUMAN_INPUT_FILE = ORCHESTRATION_DIR / "human_input.md"


def _run(cmd: list[str], timeout: int = 60) -> str:
    """Run a subprocess and return its stdout/stderr, truncated to 3000 chars."""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    try:
        result = subprocess.run(
            ["uv", "run", *cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
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
    async def cmd_discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
        tags = " ".join(context.args) if context.args else "ai-agents"
        await update.message.reply_text(f"Discovering trending articles for: {tags}")
        output = _run(
            [
                "python",
                "-m",
                "knowledge.medium_scraper",
                "--discover",
                "--discover-tags",
                tags,
                "--max",
                "10",
            ],
            timeout=120,
        )
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

    @_guard
    async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
        question = " ".join(context.args) if context.args else ""
        if not question:
            await update.message.reply_text("Usage: /ask <your question>")
            return
        # Simple knowledge-base search: list matching article titles
        kb_dir = REPO_ROOT / "data" / "knowledge" / "raw" / "medium"
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
    async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
        branch = context.args[0] if context.args else None
        label = f"branch {branch}" if branch else "uncommitted changes"
        await update.message.reply_text(f"Running AI code review on {label}...")
        cmd = ["python", "-m", "agents.reviewer"]
        if branch:
            cmd += ["--branch", branch]
        output = _run(cmd, timeout=120)
        # Split long output into chunks
        for i in range(0, len(output), 3000):
            chunk = output[i : i + 3000]
            await update.message.reply_text(chunk)

    @_guard
    async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Running quality gate (lint + types + tests)...")
        output = _run(["python", "-m", "pytest", "tests/", "-v"], timeout=120)
        lint = _run(["python", "-m", "ruff", "check", "src/", "tests/"], timeout=30)
        types = _run(["python", "-m", "mypy", "src/"], timeout=60)
        report = f"*Lint:* {lint[:500]}\n\n*Types:* {types[:500]}\n\n*Tests:* {output[:1500]}"
        await update.message.reply_text(report[:3000], parse_mode="Markdown")

    @_guard
    async def cmd_orchestrate_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SESSION_FILE.exists():
            await update.message.reply_text("No active session.")
            return
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        summary = (
            f"*Session:* {data.get('task', '?')}\n"
            f"Phase: `{data.get('phase', '?')}` | Agent: `{data.get('agent', '?')}`\n"
            f"Status: `{data.get('status', '?')}`\n"
            f"Fix cycles: {data.get('iterations', 0)}/3 | "
            f"Failed checks: {data.get('failed_checks', 0)}/2\n\n"
            "/pause  /stop  /skip  /resume"
        )
        await update.message.reply_text(summary, parse_mode="Markdown")

    @_guard
    async def cmd_orchestrate_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SESSION_FILE.exists():
            await update.message.reply_text("No active session.")
            return
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        data["status"] = "STOPPED"
        SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        await update.message.reply_text(
            f"Session STOPPED: {data.get('task', '?')}\n"
            "No further automatic handoffs. Run /resume to continue."
        )

    @_guard
    async def cmd_orchestrate_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SESSION_FILE.exists():
            await update.message.reply_text("No active session.")
            return
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        data["status"] = "PAUSED"
        SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        await update.message.reply_text(
            f"Session PAUSED: {data.get('task', '?')}\nRun /resume to continue."
        )

    @_guard
    async def cmd_orchestrate_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
        output = _run(["python", "-m", "agents.orchestrator", "resume"])
        await update.message.reply_text(output)

    @_guard
    async def cmd_orchestrate_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
        output = _run(["python", "-m", "agents.orchestrator", "next"])
        await update.message.reply_text(output)

    @_guard
    async def handle_human_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save any non-command text as human input for the next agent pickup."""
        text = update.message.text or ""
        if not text.strip():
            return
        ORCHESTRATION_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        entry = f"\n<!-- {timestamp} -->\n{text}\n"
        existing = HUMAN_INPUT_FILE.read_text(encoding="utf-8") if HUMAN_INPUT_FILE.exists() else ""
        HUMAN_INPUT_FILE.write_text(existing + entry, encoding="utf-8")
        await update.message.reply_text("Input saved. Agent will incorporate it on next pickup.")

    @_guard
    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Orchestration:*\n"
            "/status — session state\n"
            "/stop — stop session\n"
            "/pause — pause session\n"
            "/resume — resume paused/blocked session\n"
            "/skip — skip current phase\n\n"
            "*Development:*\n"
            "/scrape — fetch Medium articles\n"
            "/discover [tags] — discover trending articles\n"
            "/review [branch] — AI code review\n"
            "/check — run quality gate\n"
            "/ask <question> — query knowledge base\n\n"
            "_Any other text is saved as agent input_",
            parse_mode="Markdown",
        )

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_human_input))

    print(f"Bot started. Send /help to your bot on Telegram (user ID: {ALLOWED_USER_ID}).")
    await app.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_bot())
