"""
Automated code review using LLM (Anthropic or OpenAI).

Runs `git diff` to find changes, sends them to an LLM for review,
and optionally notifies via Telegram.

Usage:
    python -m agents.reviewer                    # review uncommitted changes
    python -m agents.reviewer --branch feat/x    # review branch vs main
    python -m agents.reviewer --notify           # also send results to Telegram

Requires: ANTHROPIC_API_KEY or OPENAI_API_KEY in .env
"""

import argparse
import logging
import subprocess
import sys

from dotenv import load_dotenv

from agents.base import BaseAgent
from bot.notify import send_message

load_dotenv()

log = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """\
You are a senior code reviewer for a Python 3.12+ project.

Project standards:
- ruff (line-length 100), mypy strict on src/, pytest in tests/
- Absolute imports from src root (e.g., from agents.base import BaseAgent)
- snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants
- Double quotes, Path() for paths, secrets in .env only
- Functions under ~50 lines, mock all external calls in tests

Review the following git diff and report:
1. **Critical issues**: Security vulnerabilities, data loss risks, broken logic
2. **Major issues**: Missing tests, poor error handling, violations of project standards
3. **Minor issues**: Naming, style, readability improvements
4. **Verdict**: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION

Be concise. Focus on what matters. Skip praise.
"""

MAX_DIFF_CHARS = 30000


def get_diff(branch: str | None = None) -> str:
    """Get git diff for review."""
    cmd = ["git", "diff", f"main..{branch}"] if branch else ["git", "diff", "HEAD"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        # Fallback: diff against empty (for initial commits)
        result = subprocess.run(
            ["git", "diff", "--cached"], capture_output=True, text=True, check=False
        )

    diff = result.stdout.strip()
    if not diff:
        # Try unstaged only
        result = subprocess.run(["git", "diff"], capture_output=True, text=True, check=False)
        diff = result.stdout.strip()

    return diff


def review_diff(diff: str, model: str | None = None) -> str:
    """Send diff to LLM for review."""
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n... (truncated, diff too large)"

    agent = BaseAgent(
        model=model or "claude-haiku-4-5",
        max_tokens=2048,
    )
    agent.system_prompt = REVIEW_SYSTEM_PROMPT

    return agent.complete(f"```diff\n{diff}\n```")


def main() -> None:
    """CLI entry point for automated code review."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="AI-powered code review")
    parser.add_argument("--branch", help="Branch to review against main")
    parser.add_argument("--model", help="LLM model to use (default: claude-haiku-4-5)")
    parser.add_argument("--notify", action="store_true", help="Send review to Telegram")
    args = parser.parse_args()

    diff = get_diff(args.branch)
    if not diff:
        print("No changes to review.")
        sys.exit(0)

    print(f"Reviewing {len(diff)} chars of diff...")
    review = review_diff(diff, args.model)
    print("\n" + review)

    if args.notify:
        header = "*Code Review*"
        if args.branch:
            header += f" ({args.branch})"
        message = f"{header}\n\n{review}"
        if send_message(message):
            print("\nReview sent to Telegram.")
        else:
            print("\nFailed to send to Telegram (check TELEGRAM_BOT_TOKEN).")


if __name__ == "__main__":
    main()
