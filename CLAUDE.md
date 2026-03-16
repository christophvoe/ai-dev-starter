# Project — Claude Code Context

> Auto-read by Claude Code at session start. Keep current.

---

## What This Project Is

[Describe your project here]

**Current state**: [Active development / Baseline complete / etc.]

---

## Quick Commands

```bash
cd C:\path\to\your-project
set PYTHONPATH=src
call venv\Scripts\activate.bat
python src/main.py

# Run tests
python -m pytest tests/ -v
```

---

## Current Priorities

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | [First priority] | 🔜 Next | [Details] |
| 2 | [Second priority] | 🔜 | [Details] |

**Start here**: [What Claude Code should tackle first]

---

## File Map

```
src/
  main.py              ← entry point
  [your modules here]

tests/
  [test files]

data/
  [data files]

scripts/
  setup.bat            ← one-time setup
```

---

## Key Conventions

### PYTHONPATH
Always set: `set PYTHONPATH=src`  
Import as top-level: `from module import thing` (not `from src.module...`)

### Paths
Always absolute:
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
```

### Environment Variables
All in `.env`. See `.env.example` for required keys.

---

## MCP Servers (Active)

| MCP | Status | Requires |
|-----|--------|---------|
| filesystem | ✅ Active | nothing |
| sequential-thinking | ✅ Active | nothing |
| github | 🔑 Needs token | `GITHUB_TOKEN` in `.env` |
| brave-search | 🔑 Needs key | `BRAVE_API_KEY` in `.env` |

---

## Common Pitfalls

1. **Import errors** → missing `PYTHONPATH=src`
2. **API keys missing** → check `.env`
3. **Async at top level** → wrap in `asyncio.run()`
4. **Hardcoded paths** → use `Path(__file__).resolve()`

---

## Known Bugs (Fix Before Adding Features)

[List active bugs here]
