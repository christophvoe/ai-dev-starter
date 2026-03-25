---
description: "Use when writing or editing Python code. Covers code style, imports, typing, and naming for this project."
applyTo: "**/*.py"
---
# Python Code Standards

- ruff enforced: line-length 100, double quotes, trailing commas
- Absolute imports from src/: `from agents.base import BaseAgent`
- snake_case functions/variables, PascalCase classes, UPPER_SNAKE_CASE constants
- Type hints on all function signatures
- Paths: `Path(__file__).resolve().parent`, never hardcoded strings
- Secrets via `os.getenv()` + python-dotenv, NEVER hardcoded
- Functions under ~50 lines; extract helpers when longer
- Specific exceptions, not bare `except:`
- Log with context: `logger.error("Failed to fetch %s: %s", url, e)`
