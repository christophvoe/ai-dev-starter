# AI Dev Starter Template

A batteries-included template for AI-assisted Python projects.

**What's included:**
- ✅ VS Code configured (venv auto-activation, Python, Copilot, MCPs)
- ✅ GitHub Copilot custom instructions (`.github/copilot-instructions.md`)
- ✅ Claude Code context file (`CLAUDE.md`)
- ✅ MCP servers for both Copilot and Claude Code
- ✅ F5 debug configs, recommended extensions
- ✅ `.gitignore` with Python + secrets protection
- ✅ `.env.example` with common API key templates

## Quick Start

```bash
# 1. Clone this template
git clone https://github.com/christophvoe/ai-dev-starter.git my-project
cd my-project

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in your API keys
copy .env.example .env
# Edit .env with your keys

# 5. Open in VS Code (settings auto-apply)
code .
```

## AI Tools Included

### GitHub Copilot (VS Code)
- **Inline autocomplete**: Tab to accept
- **Chat**: `Ctrl+Shift+I` → `@workspace What does X do?`
- **MCPs configured**: filesystem, github, sequential-thinking, brave-search
- **Custom instructions**: `.github/copilot-instructions.md`

### Claude Code (Terminal)
- **Start**: `cd project && claude`
- **Context file**: `CLAUDE.md` — read automatically at session start
- **MCPs configured**: same 4 servers via `.mcp.json`

### Cline (VS Code Extension — Install Separately)
- VS Code marketplace: search `Cline`
- Autonomous multi-step coding agent
- Uses same Claude/OpenAI API keys as Claude Code
- Best for: complex multi-file tasks without leaving VS Code
- See [WORKFLOW.md](WORKFLOW.md) for setup guide

## Project Structure

```
my-project/
├── .github/
│   └── copilot-instructions.md  ← Copilot context (edit for your project)
├── .vscode/
│   ├── settings.json            ← Python venv, PYTHONPATH, editor settings
│   ├── extensions.json          ← Recommended extensions
│   ├── launch.json              ← F5 debug configs
│   └── mcp.json                 ← MCP servers for Copilot Chat
├── src/                         ← Your Python package
│   └── __init__.py
├── tests/                       ← Pytest test suite
│   └── __init__.py
├── scripts/
│   └── setup.bat                ← One-time venv + deps setup (Windows)
├── .mcp.json                    ← MCP servers for Claude Code
├── .gitignore                   ← Python + secrets
├── .env.example                 ← API key template (safe to commit)
├── .env                         ← Your actual keys (NEVER commit)
├── CLAUDE.md                    ← Claude Code session context
├── WORKFLOW.md                  ← Complete tool usage guide
└── requirements.txt             ← Python dependencies
```

## Customization

1. Edit `.github/copilot-instructions.md` — tell Copilot about your project's conventions
2. Edit `CLAUDE.md` — tell Claude Code what the project does and its priorities
3. Add your `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` to `.env`
4. Add `BRAVE_API_KEY` to `.env` for live web search in AI tools (free tier: 2000/month)
5. Add `GITHUB_TOKEN` to `.env` for GitHub MCP (commits, history, blame)

## Included AI Tools Comparison

| Tool | Type | Cost | Best For |
|------|------|------|---------|
| GitHub Copilot | VS Code inline | ~€10/month | Day-to-day autocomplete |
| Copilot Chat | VS Code chat | Included | File-level Q&A, quick fixes |
| Claude Code | Terminal agent | Pay-per-use | Multi-file tasks, architecture |
| Cline | VS Code agent | Pay-per-use | Autonomous coding in IDE |
| Continue | VS Code | Free + local LLM option | Private/offline coding |
| Aider | Terminal | Free + API cost | Quick multi-file from terminal |
