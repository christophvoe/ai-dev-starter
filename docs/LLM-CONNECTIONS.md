# Adding LLM Connections

This project supports multiple LLM providers through `src/agents/base.py` (BaseAgent).
You need an API key only if you want LLM-powered features like article curation or
AI code review. **Medium scraping and Telegram notifications work without any API key.**

---

## What needs an API key vs. what doesn't

| Feature | API key needed? |
|---------|----------------|
| Medium scraping (`make scrape-tag`) | No |
| Article discovery (`make discover`) | No |
| Telegram bot (`make bot`) | No — only `TELEGRAM_BOT_TOKEN` |
| Article curation (`CURATE=1`) | Yes — Anthropic or OpenAI |
| AI code review (`make review`) | Yes — Anthropic |
| Orchestration state machine | No |

---

## Option 1 — Anthropic API (recommended)

Best quality for code review and article curation. Claude Haiku is the cheapest model
and works well for most tasks.

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Add to `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Cost estimate**: Haiku costs ~$0.25/million input tokens. A typical curation run
(50 articles) uses ~20k tokens → less than $0.01.

**Models available** (set in `src/agents/base.py` or override in calling code):

```python
agent = BaseAgent(model="claude-haiku-4-5-20251001")   # fast + cheap
agent = BaseAgent(model="claude-sonnet-4-6")           # balanced
agent = BaseAgent(model="claude-opus-4-6")             # most capable
```

---

## Option 2 — OpenAI API

Works as a drop-in alternative. GPT-4o-mini is the cheapest option.

1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Create an API key
3. Add to `.env`:

```bash
OPENAI_API_KEY=sk-...
```

4. Override the model when calling BaseAgent:

```python
agent = BaseAgent(provider="openai", model="gpt-4o-mini")
```

---

## Option 3 — Local models with Ollama (no API key, no cost)

Run models locally. Works offline. Requires enough RAM (8GB+ for small models).

### Install Ollama

```bash
# macOS / Linux
curl https://ollama.ai/install.sh | sh

# Windows — download from https://ollama.com/download
```

### Pull a model

```bash
ollama pull llama3.2        # 2GB — good for most tasks
ollama pull qwen2.5-coder   # optimized for code
ollama pull mistral         # strong general model
```

### Configure BaseAgent to use Ollama

Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1`.

In Python:

```python
from agents.base import BaseAgent

agent = BaseAgent(
    provider="openai",
    model="llama3.2",
    base_url="http://localhost:11434/v1",
    api_key="ollama",   # Ollama doesn't check the key, but a value is required
)
```

Or set in `.env` and adjust `BaseAgent.__init__` to pick them up:

```bash
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.2
```

**Note**: Local models are slower and less accurate than cloud models for complex
reasoning tasks, but work well for simple curation and summaries.

---

## Option 4 — OpenRouter (one key, many models)

OpenRouter proxies 100+ models (GPT-4o, Claude, Gemini, Llama, Mistral…) behind a
single OpenAI-compatible API. Useful if you want to compare models or use free-tier
models.

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Get an API key
3. Add to `.env`:

```bash
OPENROUTER_API_KEY=sk-or-...
```

4. Use with BaseAgent (OpenAI-compatible):

```python
agent = BaseAgent(
    provider="openai",
    model="anthropic/claude-haiku-4",       # or "meta-llama/llama-3.2-3b-instruct:free"
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

Free models available (check openrouter.ai/models?q=free for current list):

```
meta-llama/llama-3.2-3b-instruct:free
google/gemma-2-9b-it:free
mistralai/mistral-7b-instruct:free
```

---

## Option 5 — GitHub Models (free for Copilot subscribers)

If you have GitHub Copilot, you can use GitHub Models — a free preview of GPT-4o,
Llama, Mistral, and Phi models via the GitHub API.

```bash
GITHUB_TOKEN=ghp_...    # your personal access token with models:read scope
```

```python
agent = BaseAgent(
    provider="openai",
    model="gpt-4o-mini",
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
)
```

Check [github.com/marketplace/models](https://github.com/marketplace/models) for
available models.

---

## Summary

| Option | Cost | Quality | Offline? | Setup |
|--------|------|---------|----------|-------|
| Anthropic API | ~$0.01/run | Excellent | No | 2 min |
| OpenAI API | ~$0.01/run | Excellent | No | 2 min |
| Ollama (local) | Free | Good | Yes | 5 min + download |
| OpenRouter | Free tier + pay | Variable | No | 2 min |
| GitHub Models | Free (Copilot) | Good | No | 2 min |

For getting started quickly: **Anthropic API** with Claude Haiku. For zero cost: **Ollama**
with llama3.2. For no setup at all: just skip LLM features — scraping and Telegram work
without any key.
