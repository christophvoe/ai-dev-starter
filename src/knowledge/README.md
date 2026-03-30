# Medium Scraper + Trend Discovery + LLM Curation

> Automated pipeline: **Discover** trending articles → **Curate** with AI → **Scrape** the best ones.

---

## Quick Start

```bash
# Discover trending articles (no API key needed)
make discover

# Discover with specific topics
make discover TAGS="ai-agents,llm,automation" KEYWORDS="agent,Claude,trading"

# Let an LLM pick the best articles (needs ANTHROPIC_API_KEY or OPENAI_API_KEY in .env)
make discover TAGS="ai-agents,llm" KEYWORDS="agent,Claude" CURATE=1

# Discover + auto-scrape the top 10
make discover-scrape TAGS="ai-agents,llm" KEYWORDS="agent,Claude"
```

Or run the Python CLI directly:

```bash
uv run python -m knowledge.medium_scraper --discover \
    --discover-tags "ai-agents,llm,automation" \
    --keywords "agent,Claude,trading"
```

---

## The Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  DISCOVER    │ →  │  ENRICH      │ →  │  CURATE      │ →  │  SCRAPE     │
│  RSS feeds   │    │  Claps/      │    │  LLM picks   │    │  Full       │
│  by tag      │    │  responses   │    │  the best    │    │  article    │
│              │    │  read time   │    │  articles    │    │  Markdown   │
└─────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
   No API key        --enrich            --curate          --scrape-top N
   needed            (slower)          (needs API key)     (saves to disk)
```

### Step 1: Discover (free, no keys)

Fetches RSS feeds from Medium tags and scores articles by keyword relevance.

```bash
make discover TAGS="ai-agents,llm" KEYWORDS="agent,Claude"
```

Output: ranked list of ~50-100 candidate articles with scores.

### Step 2: Enrich (optional, slower)

Fetches each article's page to get real engagement data (claps, responses, reading time).

```bash
# Via direct CLI (enrich is auto-included in discover-scrape)
uv run python -m knowledge.medium_scraper --discover --discover-tags "ai-agents,llm" --enrich
```

### Step 3: Curate with LLM (optional, needs API key)

Sends the candidate list to Claude or GPT to evaluate article quality, depth, and practical value. The LLM returns its top picks with reasoning.

```bash
make discover TAGS="ai-agents,llm" KEYWORDS="agent,Claude" CURATE=1
```

Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in `.env`. Uses the cheapest model by default (Claude Haiku / GPT-4o-mini).

### Step 4: Scrape the best

Auto-scrape the top N articles into your knowledge base as Markdown.

```bash
make discover-scrape TAGS="ai-agents,llm" CURATE=1
```

---

## All Scraping Commands

### Scrape a curated Medium list

```bash
make scrape-list URL="https://medium.com/@voeltzke.christoph/list/coding-6c7978acb372"

# Save to custom directory
make scrape-list URL="..." OUTPUT="data/knowledge/raw/medium/coding"

# Save with date subfolder (YYYY-MM-DD)
make scrape-list URL="..." DATED=1
```

### Scrape by tag (public, no cookies needed)

```bash
make scrape-tag TAG="ai-agents"
```

### Scrape a single article

```bash
make scrape-article URL="https://medium.com/@author/article-title-abc123"
```

### Scrape bookmarks (needs cookies in .env)

```bash
make scrape-bookmarks
```

### Browse saved articles

```bash
make summarize          # Show digest of recent articles
```

---

## Setup: Cookies for Member-Only Content

Tag scraping and discovery work without credentials. For member-only articles and bookmarks:

1. Open `medium.com` in Chrome while logged in
2. F12 → Application → Cookies → `https://medium.com`
3. Copy the values for `sid` and `uid`
4. Add to `.env`:
   ```
   MEDIUM_COOKIES=sid=YOUR_SID; uid=YOUR_UID
   ```

That's it — cookies are auto-loaded from `.env` for every command.

---

## Setup: LLM Curation

Add one of these to your `.env`:

```env
# Option A: Anthropic (recommended — uses Claude Haiku, ~$0.001 per curation)
ANTHROPIC_API_KEY=sk-ant-...

# Option B: OpenAI (uses GPT-4o-mini)
OPENAI_API_KEY=sk-...
```

The curator auto-detects which key is available. Cost is negligible (~$0.001 per run with Haiku).

---

## Python API

```python
from knowledge.medium_scraper import TrendDiscoverer, MediumScraper
from knowledge.article_curator import ArticleCurator

# 1. Discover candidates
discoverer = TrendDiscoverer()
candidates = discoverer.discover_from_tags(
    tags=["ai-agents", "llm", "automation"],
    keywords=["agent", "Claude", "trading"],
    max_per_tag=15,
)

# 2. Enrich with engagement data (optional)
candidates = discoverer.enrich_with_metadata(candidates, max_enrich=20)

# 3. Curate with LLM (optional — needs API key in env)
curator = ArticleCurator()
curated = curator.curate(candidates, keywords=["agent", "Claude"], top_n=10)

# 4. Scrape the best ones
scraper = MediumScraper(output_dir="data/knowledge/raw/medium/trending")
for article_info in curated[:5]:
    scraper.fetch_article_by_url(article_info.url)
```

---

## Architecture

```
src/knowledge/
├── medium_scraper.py      # MediumScraper (scraping) + TrendDiscoverer (discovery)
├── article_curator.py     # ArticleCurator (LLM evaluation) — extends BaseAgent
├── README.md              # This file
└── __init__.py
```

---

## Complete Makefile Reference

| Command | What It Does |
|---------|-------------|
| `make scrape` | Scrape default coding list |
| `make scrape-list URL="..."` | Scrape any Medium list |
| `make scrape-tag TAG="..."` | Scrape by tag |
| `make scrape-article URL="..."` | Single article |
| `make scrape-bookmarks` | Your bookmarks (needs cookies) |
| `make summarize` | Show article digest |
| `make discover` | Discover trending articles |
| `make discover TAGS="..." KEYWORDS="..."` | Filter discovery |
| `make discover CURATE=1` | LLM-curated selection |
| `make discover-scrape` | Discover + auto-scrape top 10 |
| `make discover-scrape CURATE=1` | Discover + curate + scrape |

### Extra flags (combinable)

| Flag | Example | Effect |
|------|---------|--------|
| `OUTPUT="path"` | `make scrape OUTPUT="../other-repo"` | Save to custom directory |
| `DATED=1` | `make scrape DATED=1` | Add YYYY-MM-DD subfolder |
| `TAGS="a,b,c"` | `make discover TAGS="ai-agents,llm"` | Comma-separated tags |
| `KEYWORDS="x,y"` | `make discover KEYWORDS="agent,Claude"` | Comma-separated keywords |
| `CURATE=1` | `make discover CURATE=1` | Enable LLM curation |

---

## How the LLM Curator Works

1. Takes up to 50 candidate articles (title, author, tags, summary, engagement)
2. Sends them to Claude Haiku (or GPT-4o-mini) with evaluation criteria
3. LLM returns a ranked JSON array with reasoning for each pick
4. Curator re-scores candidates based on LLM ranking
5. Falls back gracefully if no API key → uses keyword scoring only

### Scoring System

| Signal | Points | Source |
|--------|--------|--------|
| Keyword in title | +3 | TrendDiscoverer |
| Keyword in tags | +2 | TrendDiscoverer |
| Keyword in summary | +1 | TrendDiscoverer |
| Engagement (claps/responses) | +0-5 | enrich step |
| LLM ranking position | +2-20 | ArticleCurator |

---

## Tips

- **Start simple**: Run `make discover` first — no setup needed
- **Add keywords gradually**: Start broad, then narrow to what's useful
- **Curate when ready**: Only costs ~$0.001 per run, but needs an API key
- **Scrape selectively**: Don't scrape everything — let the LLM filter first
- **Review the output**: Check `data/knowledge/raw/medium/` for saved articles
- **Iterate on tags**: Good starting tags: `ai-agents`, `llm`, `python`, `automation`, `n8n`
