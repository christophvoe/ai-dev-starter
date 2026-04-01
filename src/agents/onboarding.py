"""
Interactive new-project onboarding agent.

Asks questions about the project and writes:
  - docs/PROJECT.md
  - Appends project context to CLAUDE.md (if Claude Code available)
  - Updates .github/copilot-instructions.md header (if Copilot available)
  - Updates .env.example with project-specific variables
  - Optionally kicks off a Medium scrape
  - Prints the first orchestrate-start command

Usage:
  make onboard
  uv run python -m agents.onboarding
"""

import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DOC = BASE_DIR / "docs" / "PROJECT.md"
ENV_EXAMPLE = BASE_DIR / ".env.example"
CLAUDE_MD = BASE_DIR / "CLAUDE.md"
COPILOT_INSTRUCTIONS = BASE_DIR / ".github" / "copilot-instructions.md"

QUESTIONS: list[tuple[str, str]] = [
    (
        "name",
        "1. Project name and one-sentence description?\n"
        "   (e.g., 'DataBot — scrapes and summarizes financial reports')\n> ",
    ),
    (
        "type",
        "2. Project type?\n"
        "   a) Python CLI tool\n"
        "   b) HTTP API / web service\n"
        "   c) Data pipeline / scraper\n"
        "   d) AI agent / LLM app\n"
        "   e) Other (describe)\n> ",
    ),
    (
        "services",
        "3. External services/APIs this project will use?\n"
        "   (e.g., 'Anthropic API, PostgreSQL, S3' — or 'none')\n> ",
    ),
    ("team", "4. Solo or team project?\n> "),
    (
        "tools",
        "5. Which AI tools do you have active?\n"
        "   a) Both GitHub Copilot + Claude Code\n"
        "   b) Claude Code only\n"
        "   c) GitHub Copilot only\n"
        "   d) Neither (use repo as plain Python template)\n> ",
    ),
    (
        "worktrees",
        "6. Enable git worktrees for parallel agent workspaces?\n"
        "   (Two agents work in parallel — one implements, one reviews)\n"
        "   a) Yes\n"
        "   b) No\n> ",
    ),
    (
        "telegram",
        "7. Telegram bot ready? (control + monitor from your phone)\n"
        "   a) Yes — credentials are in .env\n"
        "   b) No — skip for now\n> ",
    ),
    (
        "knowledge",
        "8. Pre-scrape Medium articles for this domain?\n"
        "   (Gives both AI tools a knowledge base to draw from)\n"
        "   a) Yes — I'll enter tags now\n"
        "   b) No\n> ",
    ),
]


def _parse_name(raw: str) -> tuple[str, str]:
    """Split 'Name — description' into (name, description)."""
    if "—" in raw:
        parts = raw.split("—", 1)
        return parts[0].strip(), parts[1].strip()
    if "-" in raw:
        parts = raw.split("-", 1)
        return parts[0].strip(), parts[1].strip()
    return raw.strip(), ""


def _has_claude() -> bool:
    """True when the Claude Code tool option includes claude."""
    return True  # checked via answers['tools']


def collect_answers() -> dict[str, str]:
    """Ask the onboarding questions interactively and return answers dict."""
    answers: dict[str, str] = {}
    print("\n Welcome to AI Dev Starter!\n")
    print("I'll ask you a few quick questions to configure this repo for your project.\n")
    for key, question in QUESTIONS:
        answer = input(question).strip()
        if not answer:
            answer = "skipped"
        answers[key] = answer
        print()

        # If they want to scrape, ask for tags right away
        if key == "knowledge" and answer.lower().startswith("a"):
            tags = input(
                "   Enter comma-separated tags to scrape (e.g., 'ai-agents, python, llm'):\n> "
            ).strip()
            answers["scrape_tags"] = tags or "ai-agents"
            print()

    return answers


def write_project_doc(answers: dict[str, str], out_path: Path = PROJECT_DOC) -> None:
    """Write docs/PROJECT.md from onboarding answers."""
    name, description = _parse_name(answers.get("name", "Unnamed project"))
    tools_raw = answers.get("tools", "d")
    tools_label = {
        "a": "GitHub Copilot + Claude Code",
        "b": "Claude Code",
        "c": "GitHub Copilot",
        "d": "None (plain template)",
    }.get(tools_raw[:1].lower(), tools_raw)

    content = (
        f"# {name}\n\n"
        f"## Goal\n{description or answers.get('name', 'Not specified')}\n\n"
        f"## Type\n{answers.get('type', 'Not specified')}\n\n"
        f"## External Services\n{answers.get('services', 'None specified')}\n\n"
        f"## Team\n{answers.get('team', 'Not specified')}\n\n"
        f"## AI Tools\n{tools_label}\n\n"
        f"## Stack\nPython 3.12, uv, ruff, mypy, pytest\n\n"
        f"## Notifications\n"
        f"Telegram: {'enabled' if answers.get('telegram', '').lower().startswith('a') else 'not configured'}\n\n"
        f"## Worktrees\n"
        f"Parallel agent workspaces: "
        f"{'enabled' if answers.get('worktrees', '').lower().startswith('a') else 'disabled'}\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    try:
        label = out_path.relative_to(BASE_DIR)
    except ValueError:
        label = out_path
    print(f"  Written: {label}")


def append_to_claude_md(answers: dict[str, str]) -> None:
    """Append project-specific context to CLAUDE.md (only if Claude Code is in use)."""
    tools = answers.get("tools", "d")
    if tools[:1].lower() not in ("a", "b"):
        return  # Claude Code not selected — skip
    name_raw = answers.get("name", "This project")
    section = (
        "\n---\n\n"
        "## 12. Project Context (generated by make onboard)\n\n"
        f"**Name**: {name_raw}\n"
        f"**Type**: {answers.get('type', '?')}\n"
        f"**External services**: {answers.get('services', 'none')}\n"
        f"**Team**: {answers.get('team', 'solo')}\n"
    )
    if CLAUDE_MD.exists():
        existing = CLAUDE_MD.read_text(encoding="utf-8")
        if "## 12. Project Context" not in existing:
            CLAUDE_MD.write_text(existing + section, encoding="utf-8")
            print("  Updated: CLAUDE.md")


def update_copilot_instructions(answers: dict[str, str]) -> None:
    """Update project name in copilot-instructions.md (only if Copilot is in use)."""
    tools = answers.get("tools", "d")
    if tools[:1].lower() not in ("a", "c"):
        return  # Copilot not selected — skip
    if not COPILOT_INSTRUCTIONS.exists():
        return
    name, _ = _parse_name(answers.get("name", "AI Dev Starter"))
    content = COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# ") and "Copilot Context" in line:
            lines[i] = f"# {name} — GitHub Copilot Context"
            break
    COPILOT_INSTRUCTIONS.write_text("\n".join(lines), encoding="utf-8")
    print("  Updated: .github/copilot-instructions.md")


def _split_services(raw: str) -> list[str]:
    """Split free-form service input into normalized service tokens."""
    if not raw:
        return []
    normalized = re.sub(r"\s+(and|&)\s+", ",", raw.strip(), flags=re.IGNORECASE)
    parts = [p.strip() for p in re.split(r"[,;\n]+", normalized) if p.strip()]
    return parts


def _infer_env_vars_from_services(raw_services: str) -> list[str]:
    """Infer likely env var names from external service names."""
    service_map: dict[str, list[str]] = {
        "anthropic": ["ANTHROPIC_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "github": ["GITHUB_TOKEN"],
        "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_USER_ID"],
        "postgres": ["DATABASE_URL"],
        "postgresql": ["DATABASE_URL"],
        "mysql": ["DATABASE_URL"],
        "mariadb": ["DATABASE_URL"],
        "sqlite": ["DATABASE_URL"],
        "redis": ["REDIS_URL"],
        "s3": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
        "aws": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
    }

    inferred: list[str] = []
    for service in _split_services(raw_services):
        lowered = service.lower()
        if lowered in {"none", "no", "n/a", "na", "skipped"}:
            continue

        matched = False
        for key, vars_for_key in service_map.items():
            if key in lowered:
                inferred.extend(vars_for_key)
                matched = True

        if matched:
            continue

        token = re.sub(r"[^A-Za-z0-9]+", "_", service).strip("_").upper()
        if token:
            inferred.append(f"{token}_API_KEY")

    seen: set[str] = set()
    unique_vars: list[str] = []
    for var in inferred:
        if var not in seen:
            seen.add(var)
            unique_vars.append(var)
    return unique_vars


def update_env_example(answers: dict[str, str], env_example_path: Path = ENV_EXAMPLE) -> None:
    """Append missing project-specific env vars to .env.example."""
    if not env_example_path.exists():
        return

    vars_to_add = _infer_env_vars_from_services(answers.get("services", ""))
    if answers.get("telegram", "").lower().startswith("a"):
        vars_to_add.extend(["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_USER_ID"])

    # De-duplicate while preserving order.
    seen: set[str] = set()
    ordered_vars: list[str] = []
    for var in vars_to_add:
        if var not in seen:
            seen.add(var)
            ordered_vars.append(var)

    if not ordered_vars:
        return

    content = env_example_path.read_text(encoding="utf-8")
    existing = set(re.findall(r"(?m)^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=", content))
    missing = [var for var in ordered_vars if var not in existing]
    if not missing:
        return

    section = "\n\n# -- Project-specific variables (generated by make onboard) --\n"
    lines = "\n".join(f"{var}=" for var in missing)
    env_example_path.write_text(content.rstrip() + section + lines + "\n", encoding="utf-8")
    print("  Updated: .env.example")


def run_scrape(tags: str) -> None:
    """Trigger medium scraper for given comma-separated tags."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    if not tag_list:
        return
    print(f"\n  Scraping {len(tag_list)} tag(s): {', '.join(tag_list)}")
    for tag in tag_list:
        print(f"    Scraping tag '{tag}'...")
        result = subprocess.run(
            ["uv", "run", "python", "-m", "knowledge.medium_scraper", "--tag", tag, "--max", "10"],
            cwd=str(BASE_DIR),
            env={**__import__("os").environ, "PYTHONPATH": str(BASE_DIR / "src")},
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            print(f"    Warning: scrape for '{tag}' exited with code {result.returncode}")


def print_next_steps(answers: dict[str, str]) -> None:
    """Print the first command to run."""
    name, desc = _parse_name(answers.get("name", "your project"))
    first_task = desc[:50] if desc else f"set up {name}"
    tools = answers.get("tools", "d")

    print("\n" + "=" * 60)
    print("Setup complete!\n")

    if tools[:1].lower() != "d":
        start_cmd = f'make orchestrate-start TASK="{first_task}"'
        if answers.get("worktrees", "").lower().startswith("a"):
            start_cmd += " WORKTREE=1"
        print("Your next step:")
        print(f"\n  {start_cmd}\n")

        if tools[:1].lower() in ("a", "b"):
            print("Then open Claude Code and say:")
            print(f'  "Implement: {first_task}"\n')
        if tools[:1].lower() in ("a", "c"):
            print("Or open Copilot Chat and type:")
            print(f"  @orchestrator Implement: {first_task}\n")
    else:
        print("You're set up as a plain Python project.")
        print("Run: make check\n")

    if answers.get("telegram", "").lower().startswith("b"):
        print("To enable Telegram notifications later:")
        print("  1. Create a bot via @BotFather on Telegram")
        print("  2. Add TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_USER_ID to .env")
        print("  3. Open Telegram, find your bot, send /start")
        print("  4. Run: make bot\n")

    print("Key commands:")
    print("  make check              # lint + typecheck + tests")
    print("  make orchestrate-status # show current phase")
    print("  make discover TAGS=...  # find trending articles")
    print("  make bot                # start Telegram bot")
    print("=" * 60)


def promote_to_repo(target: Path) -> None:
    """Copy AI tooling files from this repo into an existing target repo.

    Promotes:
      - .github/agents/*.agent.md       → TARGET/.github/agents/
      - .github/prompts/*.prompt.md     → TARGET/.github/prompts/
      - .github/instructions/           → TARGET/.github/instructions/
      - .github/copilot-instructions.md → TARGET/.github/copilot-instructions.md
                                          (creates if missing; skips if exists)
      - Appends ai-dev-starter section to TARGET/CLAUDE.md (if exists)

    Does NOT overwrite files that already exist in the target repo.
    """
    import shutil

    if not target.exists():
        print(f"  Error: target path does not exist: {target}")
        sys.exit(1)

    src_github = BASE_DIR / ".github"
    dst_github = target / ".github"

    # Directories to mirror wholesale (create if missing, copy files, skip existing)
    for subdir in ("agents", "prompts", "instructions"):
        src_dir = src_github / subdir
        dst_dir = dst_github / subdir
        if not src_dir.exists():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src_file in src_dir.glob("*"):
            dst_file = dst_dir / src_file.name
            if dst_file.exists():
                print(f"  Skipped (exists): .github/{subdir}/{src_file.name}")
            else:
                shutil.copy2(src_file, dst_file)
                print(f"  Copied: .github/{subdir}/{src_file.name}")

    # copilot-instructions.md — copy only if target doesn't have one
    src_ci = src_github / "copilot-instructions.md"
    dst_ci = dst_github / "copilot-instructions.md"
    if src_ci.exists():
        if dst_ci.exists():
            print("  Skipped (exists): .github/copilot-instructions.md")
            print("    → Manually merge AI Dev Starter sections if needed")
        else:
            dst_github.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_ci, dst_ci)
            print("  Copied: .github/copilot-instructions.md")

    # .vscode/mcp.json — copy MCP config so context7 + sequential-thinking work in target
    src_mcp = BASE_DIR / ".vscode" / "mcp.json"
    dst_vscode = target / ".vscode"
    dst_mcp = dst_vscode / "mcp.json"
    if src_mcp.exists():
        if dst_mcp.exists():
            print("  Skipped (exists): .vscode/mcp.json")
        else:
            dst_vscode.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_mcp, dst_mcp)
            print("  Copied: .vscode/mcp.json (context7 + sequential-thinking MCPs)")

    # CLAUDE.md — append a pointer section if CLAUDE.md exists in target
    dst_claude = target / "CLAUDE.md"
    if dst_claude.exists():
        existing = dst_claude.read_text(encoding="utf-8")
        marker = "## AI Dev Starter tooling"
        if marker not in existing:
            section = (
                "\n---\n\n"
                "## AI Dev Starter tooling\n\n"
                "This repo uses AI Dev Starter for Medium scraping, Telegram notifications,\n"
                "and multi-agent orchestration. Tooling lives in the `ai-dev-starter/` folder\n"
                "(gitignored). Run commands from there:\n\n"
                "```bash\n"
                "cd ai-dev-starter\n"
                "make scrape-tag TAG='python'          # scrape articles\n"
                "make orchestrate-start TASK='...'     # start a task\n"
                "make bot                              # Telegram bot\n"
                "```\n"
            )
            dst_claude.write_text(existing + section, encoding="utf-8")
            print("  Updated: CLAUDE.md (appended ai-dev-starter section)")
    else:
        print("  Note: no CLAUDE.md found in target repo — skipping")

    print(f"\nPromotion complete → {target}")
    print("Review the copied files and adjust descriptions for your project.")


def make_workspace(target: Path) -> None:
    """Generate a .code-workspace file in target repo for multi-root VS Code / Copilot indexing.

    Creates TARGET/<repo-name>.code-workspace that adds both the target repo and the
    ai-dev-starter subfolder as roots. This makes @workspace in Copilot Chat and
    Claude Code index BOTH codebases — so AI assistants can see the orchestrator,
    scraper, and other ai-dev-starter code while you work in your own repo.
    """
    import json

    if not target.exists():
        print(f"  Error: target path does not exist: {target}")
        sys.exit(1)

    # Derive relative path from target to ai-dev-starter
    try:
        rel_path = BASE_DIR.relative_to(target)
        rel_str = str(rel_path).replace("\\", "/")
    except ValueError:
        rel_str = str(BASE_DIR).replace("\\", "/")

    repo_name = target.resolve().name or "project"
    workspace_file = target / f"{repo_name}.code-workspace"

    workspace = {
        "folders": [
            {"path": ".", "name": repo_name},
            {"path": rel_str, "name": "AI Dev Starter (tooling)"},
        ],
        "settings": {
            "search.exclude": {
                f"{rel_str}/.venv/**": True,
                f"{rel_str}/data/**": True,
                f"{rel_str}/__pycache__/**": True,
                f"{rel_str}/.mypy_cache/**": True,
                f"{rel_str}/.ruff_cache/**": True,
            }
        },
    }

    workspace_file.write_text(json.dumps(workspace, indent=2) + "\n", encoding="utf-8")
    print(f"  Created: {workspace_file.name}")
    print("\nOpen this file in VS Code to enable multi-root indexing:")
    print(f'  code "{workspace_file}"')
    print("\nNow @workspace in Copilot Chat will see both your code AND ai-dev-starter.")
    print("Add the .code-workspace file to your .gitignore if you don't want to commit it.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="AI Dev Starter onboarding")
    parser.add_argument(
        "--promote-to",
        metavar="PATH",
        help="Promote AI tooling files into an existing repo at PATH",
    )
    parser.add_argument(
        "--make-workspace",
        metavar="PATH",
        help="Generate a .code-workspace file in PATH for multi-root Copilot indexing",
    )
    args = parser.parse_args()

    if args.promote_to:
        promote_to_repo(Path(args.promote_to).resolve())
        return

    if args.make_workspace:
        make_workspace(Path(args.make_workspace).resolve())
        return

    try:
        answers = collect_answers()
        print("\nWriting configuration files...")
        write_project_doc(answers)
        append_to_claude_md(answers)
        update_copilot_instructions(answers)
        update_env_example(answers)

        if answers.get("knowledge", "").lower().startswith("a"):
            tags = answers.get("scrape_tags", "ai-agents")
            run_scrape(tags)

        print_next_steps(answers)
    except KeyboardInterrupt:
        print("\n\nOnboarding cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
