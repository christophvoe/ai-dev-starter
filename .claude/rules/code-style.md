## Python Code Style Rules

These rules apply when working with Python files in this project.

### Formatting & Linting
- ruff is the formatter and linter (line-length 100, configured in pyproject.toml)
- mypy strict mode is enforced on src/
- Run `make check` (ruff + mypy + pytest) before every commit

### Imports
- Absolute imports from src/ root: `from agents.base import BaseAgent`
- Never relative imports
- PYTHONPATH=src is set in .vscode/settings.json

### Naming
- snake_case for functions and variables
- PascalCase for classes
- UPPER_SNAKE_CASE for module-level constants
- Descriptive names: `fetch_article_content()` not `process()`

### Strings & Paths
- Double quotes preferred
- Paths: `Path(__file__).resolve().parent`, never hardcoded strings
- File I/O: Handle encoding explicitly (UTF-8)

### Functions
- Keep under ~50 lines; extract helpers when longer
- Single responsibility: each function does one thing
- DRY: if you repeat 3+ lines, extract a function

### Secrets
- Via python-dotenv + `.env`, NEVER hardcoded
- Never log secrets or credentials

### Async
- Wrap with `asyncio.run()` at entry point
- Never mix sync and async in the same call chain
