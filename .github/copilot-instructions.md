# AI Dev Starter — Copilot Instructions

> This is the base template for AI-assisted Python development.
> Update the "Project Overview" section for each new project.
> GitHub Copilot reads this for every chat interaction in this workspace.

---

## Project Overview

**Type**: Python application  
**Language**: Python 3.11+  
**Architecture**: [Describe your architecture here]

---

## Environment Setup (REQUIRED)

```bash
# PYTHONPATH must be set before imports work
$env:PYTHONPATH = "src"     # PowerShell — VS Code terminals do this automatically
set PYTHONPATH=src           # CMD
export PYTHONPATH=src        # bash/zsh
```

The `.vscode/settings.json` injects `PYTHONPATH=src` into every new terminal automatically.

---

## Module Organization

- `src/` — all Python code, imported as top-level packages (e.g., `from my_module import thing`)
- Each subpackage has `__init__.py` (can be empty)
- `main()` functions in every module for standalone testing
- Logging via `utils/logger_config.py` — call `setup_logging()` once at startup

---

## Code Conventions

### Absolute Paths (always)
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
```

### Environment Variables
Load via `python-dotenv`. Never hardcode API keys. All keys in `.env.example`.

### Async
Wrap async calls at top level with `asyncio.run()`. Never mix sync/async contexts.

### Error Handling
Validate at system boundaries (user input, external APIs). Trust internal code.

### Testing
```bash
python -m pytest tests/ -v   # or F5 → "Run Tests"
```

---

## MCP Servers in This Workspace

| Server | Purpose | Setup |
|--------|---------|-------|
| **filesystem** | Read/write project files | Auto |
| **sequential-thinking** | Step-by-step reasoning on hard problems | Auto |
| **context7** | Live up-to-date docs for ANY library | Optional: CONTEXT7_API_KEY |
| **github** | Browse commits, PRs, issues | `GITHUB_TOKEN` in `.env` |
| **brave-search** | Live web search while coding | `BRAVE_API_KEY` in `.env` |

### Using Context7 (Critical — Prevents Hallucinated APIs)
Add `use context7` to any prompt to get current docs pulled directly into the response:
```
How do I configure a LangGraph supervisor? use context7
Set up pydantic-ai with Claude. use context7
What is the yfinance download() API signature? use context7
CrewAI Flows with conditional routing. use context7
```
Context7 fetches live, version-specific documentation and code examples from the source.

### Using Knowledge Base via Filesystem MCP
The filesystem MCP serves your scraped article knowledge base:
```
Read all .md files in data/knowledge/raw/medium/ and summarize insights relevant to backtesting.
What do the saved articles say about multi-agent trading systems?
```

---

## AI Framework Selection Guide

| Framework | Best For | Stars | Notes |
|-----------|---------|-------|-------|
| **Deep Agents** | Batteries-included single agent (plan+files+shell+subagents) | 15.7k | `pip install deepagents` — inspired by Claude Code |
| **LangGraph** | Complex stateful multi-agent graphs with checkpointing | 27k | `pip install langgraph` — foundation for Deep Agents |
| **CrewAI** | Role-based autonomous agent teams | 46.6k | `pip install crewai` — independent of LangChain, 5x faster |
| **Pydantic AI** | Type-safe production agents, A2A protocol, streaming | 15.6k | `pip install pydantic-ai` — best for production grade code |
| **NanoBot** | Personal assistant via Telegram/WhatsApp/Discord | 34k | `pip install nanobot-ai` — 2min deploy |
| **Haystack** | RAG pipelines + document processing | 20k+ | Best for knowledge retrieval workflows |

### The Recommended Multi-Agent Stack

```
Layer 1 — TRIGGERS:    n8n (schedule, RSS, webhooks)
                           ▼
Layer 2 — AGENTS:      CrewAI Crew (Market Analyst + News Researcher + Strategist)
                       Pydantic AI (individual typed agent implementations)
                           ▼
Layer 3 — RUNTIME:     LangGraph (state, checkpointing, retries)
                           ▼
Layer 4 — KNOWLEDGE:   filesystem MCP + context7 (your data + live docs)
                           ▼
Layer 5 — UI:          NanoBot (Telegram interface for you)
```

---

## How Agents Communicate (3 Patterns)

### Pattern A: Shared State (Simplest)
- Agents write outputs to `data/cache/`; next agent reads on startup
- n8n uses Execute Command node to run each step sequentially
- Best for: ETL pipelines, data that must persist across restarts

### Pattern B: Event-Driven via n8n Webhooks
```
Agent A completes → POST to n8n webhook → n8n triggers Agent B
```
- Agent A: `requests.post("http://localhost:5678/webhook/agent-b", json=result)`
- n8n: Webhook node → Execute Command node → Telegram notification
- Best for: decoupled services, adding human review step between agents

### Pattern C: Direct Orchestration (CrewAI/LangGraph)
- Agents share a `State` object; CrewAI manager agent delegates tasks
- Use `Process.hierarchical` in CrewAI for manager→worker pattern
- Best for: tight reasoning loops, tasks that need real-time coordination

---

## NanoBot — Personal Agent via Telegram

### Setup (15 minutes)
1. Get Telegram bot token: message `@BotFather` → `/newbot`
2. Get your Telegram user ID: message `@userinfobot`
3. Configure `~/.nanobot/config.json` (see template below)
4. Run: `nanobot gateway`

### Minimal Config Template
```json
{
  "providers": { "anthropic": { "apiKey": "YOUR_ANTHROPIC_KEY" } },
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-5",
      "workspace": "C:/path/to/your/project"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_TELEGRAM_USER_ID"]
    }
  },
  "tools": {
    "exec": { "enabled": true },
    "web": { "search": { "provider": "brave", "apiKey": "YOUR_BRAVE_KEY" } },
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/path/to/project"],
        "enabledTools": ["read_file", "list_directory", "search_files"]
      }
    }
  }
}
```

### What NanoBot Can Do for You
- Message bot: "What's the trading signal for AAPL?" → runs your Python strategy, reads cache, replies
- "Summarize today's news sentiment" → reads `data/cache/sentiment/*.json`, LLM synthesis
- "Run the backtest for TSLA" → executes your backtest script, returns result
- "What did I save about momentum trading?" → reads `data/knowledge/raw/medium/*.md`

---

## n8n Automation Flows (Conceptual)

### Flow Patterns That Work Well

| Flow | Trigger | Steps | Needs |
|------|---------|-------|-------|
| Daily market scan | Schedule 6am | Fetch data → Run signals → Telegram summary | Python venv, Telegram bot |
| Breaking news alert | RSS feed | Parse headline → FinBERT → IF negative → Alert | Python venv, RSS node |
| Weekly research digest | Monday 8am | Scrape reading list → LLM summarize → Email/Telegram | Python venv, email node |
| Portfolio EOD report | Schedule 4:30pm | Fetch prices → Compare signals → Log → Notify | Python venv |
| Agent output review | Webhook | Receive result → Human review UI → Approve → Continue | HTTP node |

### Running Python from n8n
```json
// Execute Command node
{
  "command": "C:\\path\\to\\venv\\Scripts\\python.exe src/your_script.py"
}
```

### n8n as Orchestrator vs Agent Framework

| Use n8n when... | Use CrewAI/LangGraph when... |
|-----------------|-----------------------------|
| Scheduling (time-based) | Complex reasoning between agents |
| Connecting external services | Tight agent-to-agent delegation |
| Human review step needed | State must persist across tool calls |
| Visual workflow is useful | Agents need to iterate until done |
| Input is well-defined | Task requires dynamic planning |

---

## AI Tool Decision Matrix

| Task | Best Tool |
|------|-----------|
| Inline code completions | Copilot (automatic) |
| Multi-file refactor / new feature | Copilot Chat agent mode (`@workspace`) |
| Large autonomous task ("build X") | Claude Code (terminal) |
| 24/7 background autonomous coding | Deep Agents |
| Personal assistant via Telegram | NanoBot |
| Scheduled data pipelines | n8n |
| Multi-agent team (researcher + coder + reviewer) | CrewAI |
| Type-safe agent code for production | Pydantic AI |
| Complex stateful agent graphs | LangGraph |
| Any library documentation in prompt | Context7 MCP (`use context7`) |
| Your saved articles / knowledge base | filesystem MCP |

---

## Common Pitfalls

1. **Import errors** → missing `PYTHONPATH=src`
2. **Async at top level** → wrap in `asyncio.run()`
3. **API keys missing** → check `.env` exists with all required keys
4. **Hardcoded relative paths** → use `Path(__file__).resolve().parent`
5. **Agent infinite loops** → always set `max_iter` or timeout
6. **LLM cost overruns** → use `claude-haiku` / `gpt-4o-mini` for simple tasks
7. **Context7 not working** → add `use context7` explicitly in the prompt

---

## File Reference

| Purpose | Location |
|---------|----------|
| Entry point | `src/main.py` |
| Tests | `tests/` |
| Environment | `.env` (from `.env.example`) |
| Data / cache | `data/` |
| NanoBot config | `~/.nanobot/config.json` |
| n8n workflows | `data/knowledge/n8n_workflows/` |
| Medium articles | `data/knowledge/raw/medium/` |
| Agent implementations | `src/agents/` |
