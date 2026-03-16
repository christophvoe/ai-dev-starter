# AI Development Workflow Guide

> How to use GitHub Copilot, Claude Code, Cline, MCPs, and n8n together.

---

## Daily Session Start (2 min)

```bash
# VS Code does this automatically — just open the project folder
cd my-project
code .
# Terminal auto-activates venv and sets PYTHONPATH
```

---

## Tool Selection Guide

| Task | Best Tool | Why |
|------|-----------|-----|
| Typing a new function | Copilot inline (Tab) | Fastest, no context switch |
| "What does this code do?" | Copilot Chat (`Ctrl+Shift+I`) | File-level context |
| Fix a single bug | Copilot inline chat (`Ctrl+I`) | In-place, minimal friction |
| Implement a full new module | Claude Code or Cline | Understands whole repo |
| Cross-file refactor | Claude Code | Multi-file reasoning |
| Architecture decisions | Claude Code | Sequential thinking MCP |
| Private/offline work | Continue + Ollama | No API calls, local only |
| Quick terminal-based edit | Aider | Git-integrated, fast |

---

## GitHub Copilot

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Tab` | Accept suggestion |
| `Alt+\` | Trigger suggestion |
| `Ctrl+Shift+I` | Open Copilot Chat panel |
| `Ctrl+I` | Inline chat on selection |
| `Alt+]` / `Alt+[` | Next / previous suggestion |

### Power Chat Commands
```
@workspace /fix              ← fix errors in current file
@workspace /tests            ← generate tests for selection
@workspace /doc              ← write docstring for function
@workspace /explain          ← explain selected code
@workspace What does X do?   ← Q&A about your codebase
```

### MCPs in Copilot Chat
The `.vscode/mcp.json` gives Copilot extra tools:
```
"Search for all places we compute RSI" → filesystem MCP reads codebase
"What changed in the last 3 commits?"  → github MCP reads git log
"What does the yfinance API return for invalid symbols?"  → brave-search
```

---

## Claude Code

### Session start
```bash
cd my-project
call venv\Scripts\activate         # Windows
claude                              # starts session, reads CLAUDE.md
```

### Key commands
```
/help          list commands
/status        current context + cost
/model         switch models (sonnet=cheap, opus=smart)
/compact       summarize history (saves tokens)
/memory        persistent notes across sessions
/clear         reset conversation
```

### Resume previous session
```bash
claude --resume <session-id>
# Session ID shown when you exit: "Session saved: abc123..."
```

### Optimal prompts
```
# Start fresh each session:
"Read CLAUDE.md, then tell me the current state and top priority."

# Feature implementation:
"Implement [feature] as described in [doc file].
 Use [existing module] for [X]. Write tests in tests/."

# Multi-file refactor:
"Find all hardcoded paths in src/ and replace with
 BASE_DIR = Path(__file__).resolve().parent.parent"

# Knowledge base query:
"Read all .md files in data/knowledge/raw/ and summarize
 what they say about [topic]."
```

### MCPs in Claude Code
Configured in `.mcp.json`. Claude Code auto-loads them.
- `filesystem` — list dirs, batch-read files
- `sequential-thinking` — step-by-step reasoning
- `github` — add `GITHUB_TOKEN` to `.env`
- `brave-search` — add `BRAVE_API_KEY` to `.env`

---

## Cline — VS Code Autonomous Agent

### Install
`Ctrl+Shift+X` → search **Cline** → install

### Configure
- Click Cline icon in sidebar → API Settings
- Provider: Anthropic, Model: claude-3-5-sonnet-20241022
- Or: OpenAI, Model: gpt-4o
- Or: Configure Ollama for free local use

### What Cline can do that Copilot can't
- Browse the web, read documentation pages
- Run shell commands in your project
- Edit multiple files in one operation
- Ask you clarifying questions mid-task
- Show a diff before applying changes

### Example tasks for Cline
```
"Implement the backtesting module using the spec in Contributing.md.
Create src/backtesting/engine.py and tests/test_backtest.py."

"Refactor all modules in src/data_collection/ to use absolute paths."

"Read the error in the terminal and fix it."
```

### Cline vs Claude Code
| | Cline | Claude Code |
|-|-------|------------|
| Interface | VS Code sidebar | Terminal |
| File editing | Diff view + approval | Direct edit |
| Terminal access | ✅ Yes | ✅ Yes |
| Cost | Same API rates | Same API rates |
| Best for | Staying in VS Code | Large multi-session tasks |

---

## Continue — Local/Private AI

### Install
`Ctrl+Shift+X` → search **Continue** → install

### Configure for local LLMs (free, private)
```bash
# Install Ollama
winget install Ollama.Ollama

# Download a model (~4-9GB)
ollama pull qwen2.5-coder:7b   # best for code
ollama pull llama3.2:3b        # fast, lightweight

# Continue detects Ollama automatically
```

### When to use
- Sensitive code you don't want sent to cloud APIs
- When offline or API costs are a concern
- Repetitive tasks (docstrings, tests) where Opus-level quality isn't needed

---

## Aider — Terminal-Based Multi-File Editing

### Install
```bash
pip install aider-chat
```

### Usage
```bash
# Edit specific files with instructions
aider src/backtesting/engine.py --message "implement the backtest engine"

# Multi-file
aider src/indicators/ --message "add MACD indicator to technical.py"

# Reads your git history for context automatically
```

### Why use Aider (vs Claude Code)
- Faster for targeted single-file or small multi-file changes
- Shows clean git diffs before committing
- Can commit automatically with `--auto-commit`

---

## n8n — Automation Pipelines

### Start n8n
```cmd
scripts\start_n8n.bat    # if you have started it
# OR
n8n start
```

### Navigate to: http://localhost:5678

### Useful flows for AI dev projects
1. **Daily knowledge scrape** → pulls articles, saves as .md for AI context
2. **Weekly status summary** → git log → LLM → WEEKLY_STATUS.md
3. **Scheduled data pipeline** → fetch data, run strategy, log results
4. **Error alerts** → run tests scheduled, notify on Telegram if failing

### Build a Telegram bot in n8n
1. New workflow → Trigger: Telegram
2. Node: AI Agent (GPT-4o or Claude)
3. Use the chat to ask: "Run the backtesting strategy and tell me the result"
4. n8n executes Python script → returns result to Telegram

---

## Ollama — Local LLMs (Zero Cost)

```bash
# Install
winget install Ollama.Ollama

# Best models for coding (run after install)
ollama pull qwen2.5-coder:7b       # 4.7GB — best coding model
ollama pull phi4:14b               # 9GB  — great reasoning
ollama pull nomic-embed-text       # 274MB — embeddings

# Check what's running
ollama list
ollama ps

# Test
ollama run qwen2.5-coder:7b "Write a Python function to compute RSI"
```

**Connect to VS Code tools:**
- Continue extension: auto-detects Ollama
- Aider: `aider --model ollama/qwen2.5-coder:7b`
- Cline: API Settings → Provider: Ollama → Model: qwen2.5-coder:7b

---

## Adding MCPs to Claude Code Globally

```bash
# Web automation
claude mcp add playwright -- npx -y @playwright/mcp@latest

# Database queries
claude mcp add sqlite -- npx -y @modelcontextprotocol/server-sqlite --db-path data/app.db

# Persistent memory
claude mcp add memory -- npx -y @modelcontextprotocol/server-memory
```
