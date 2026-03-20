# Project — Claude Code Context

> Auto-read by Claude Code at session start. Keep current.
> This is the AI-dev-starter template — update for each project.

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

# Install NanoBot personal assistant
pip install nanobot-ai
nanobot onboard
nanobot gateway   # start Telegram/Discord bot

# Install Deep Agents (autonomous coding agent)
pip install deepagents

# Install CrewAI (multi-agent teams)
pip install crewai

# Fix Docker/WSL if needed — run as Admin:
# wsl --install --no-distribution && restart && enable BIOS virtualization
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
  agents/              ← agent implementations (CrewAI/PydanticAI)

tests/

data/
  cache/               ← runtime data (do not commit)
  knowledge/
    raw/medium/        ← scraped Medium articles (.md + .json)
    n8n_workflows/     ← importable n8n JSON workflows

scripts/
  setup.bat            ← one-time env setup
  fix_wsl.bat          ← enables WSL2 + Docker
```

---

## Key Conventions

### PYTHONPATH
Always set: `set PYTHONPATH=src`
Import as top-level: `from module import thing` (not `from src.module...`)

### Absolute Paths
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
```

### Environment Variables
All in `.env`. See `.env.example` for required keys.

---

## MCP Servers (Active)

| MCP | Status | Purpose | Requires |
|-----|--------|---------|---------|
| filesystem | ✅ Active | Read/write project files | — |
| sequential-thinking | ✅ Active | Step-by-step reasoning | — |
| context7 | ✅ Active | Live docs for any library | Optional: CONTEXT7_API_KEY |
| github | 🔑 Needs token | GitHub API | GITHUB_TOKEN |
| brave-search | 🔑 Needs key | Live web search | BRAVE_API_KEY |

### Context7 Usage (prevents hallucinated APIs)
In any Claude Code prompt, add `use context7`:
```
Implement a CrewAI supervisor pattern. use context7
Set up pydantic-ai with streaming. use context7
```

### Knowledge Base (via filesystem MCP)
```
Read all .md files in data/knowledge/raw/medium/ and tell me what's relevant to the backtesting module.
```

---

## Multi-Agent Stack (Update as Built)

```
n8n (triggers/schedules) → CrewAI (agent teams) → NanoBot (Telegram UI)
```

### Agent Roles (define per project)
- **[Role 1]**: [Responsibility, input, output]
- **[Role 2]**: [Responsibility, input, output]

### Agent Communication
- **Shared files**: write to `data/cache/`, next agent reads on start
- **n8n webhooks**: `requests.post("http://localhost:5678/webhook/...", json=result)`
- **CrewAI process**: `Process.sequential` or `Process.hierarchical`
- **NanoBot MCP**: reads files + runs shell commands on behalf of user

### NanoBot Config
`~/.nanobot/config.json` — set `agents.defaults.workspace` to this project dir.
See `.github/copilot-instructions.md` for full config template.

---

## n8n Flows (Conceptual)

Running Python from n8n Execute Command node:
```json
{ "command": "C:\\path\\to\\venv\\Scripts\\python.exe src/your_script.py" }
```

**What you need for flows to work:**
- n8n running locally (or cloud)
- Python venv with all deps installed
- Telegram bot token (from @BotFather)
- API keys in `.env` loaded by scripts

---

## Common Pitfalls

1. **Import errors** → missing `PYTHONPATH=src`
2. **API keys missing** → check `.env`
3. **Async at top level** → wrap in `asyncio.run()`
4. **Hardcoded paths** → use `Path(__file__).resolve()`
5. **Agent loops** → set `max_iter` or timeout
6. **LLM cost** → `claude-haiku` / `gpt-4o-mini` for routine tasks

---

## Known Bugs (Fix Before Adding Features)

[List active bugs here with file + line number]

---

## Docker/WSL (if needed)

WSL2 requires BIOS virtualization:
```bash
# Step 1 — Run as Administrator in PowerShell:
wsl --install --no-distribution
# Step 2 — Restart PC
# Step 3 — Enable in BIOS: VT-x (Intel) or AMD-V (AMD)
# Step 4 — Install Ubuntu:
wsl --install -d Ubuntu
# Step 5 — Docker Desktop will now start
```
