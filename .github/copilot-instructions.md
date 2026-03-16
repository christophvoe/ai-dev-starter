# Project — Copilot Instructions

> Customize this file for your specific project.
> GitHub Copilot reads this for every chat interaction in this workspace.

## Project Overview

**Type**: Python application  
**Language**: Python 3.11+  
**Architecture**: [Describe your architecture here]

## Environment Setup (REQUIRED)

```bash
# PYTHONPATH must be set before imports work
$env:PYTHONPATH = "src"     # PowerShell
set PYTHONPATH=src           # CMD
export PYTHONPATH=src        # bash/zsh
```

The `.vscode/settings.json` does this automatically in VS Code terminals.

## Module Organization

- `src/` — all Python code, imported as top-level packages
- Each subpackage has `__init__.py`
- `main()` functions in modules for standalone testing

## Code Conventions

### Testing
```bash
python -m pytest tests/ -v
# Or F5 → "Run Tests" in VS Code
```

### Async
Wrap async top-level calls with `asyncio.run()`. Never mix sync and async contexts.

### Error Handling
Validate at system boundaries (user input, external APIs). Trust internal code.

### Paths
Always use absolute paths from `__file__`:
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
```

### Environment Variables
Load via `python-dotenv`. Never hardcode API keys.  
All keys documented in `.env.example`.

## Common Pitfalls

1. **Import errors** → missing `PYTHONPATH=src`
2. **Async at top level** → wrap in `asyncio.run()`
3. **API keys missing** → check `.env` exists and keys are set
4. **Hardcoded relative paths** → use `Path(__file__).resolve().parent`

## Known Bugs (Keep Updated)

[List any active bugs here so Copilot doesn't duplicate the wrong pattern]

## File Reference

| Purpose | Location |
|---------|----------|
| Entry point | `src/main.py` |
| Tests | `tests/` |
| Environment | `.env` (from `.env.example`) |
| Data | `data/` |
