"""
ArticleCurator — LLM-powered article selection agent.

Takes a list of discovered articles and uses Claude/GPT to evaluate which ones
are most worth reading. Returns a curated, ranked list with reasoning.

This is the project's first *real* agent usage — it demonstrates how to combine
the scraper's discovery pipeline with BaseAgent's LLM capabilities.

Usage (CLI — integrated into medium_scraper):
    # Discover + curate in one command
    python -m knowledge.medium_scraper --discover --curate
    python -m knowledge.medium_scraper --discover --curate --curate-top 5

    # With custom tags/keywords
    python -m knowledge.medium_scraper --discover \\
        --discover-tags "ai-agents,llm,automation" \\
        --keywords "agent,Claude,trading" \\
        --curate --curate-top 10

Usage (Python):
    from knowledge.article_curator import ArticleCurator
    from knowledge.medium_scraper import TrendDiscoverer

    discoverer = TrendDiscoverer()
    candidates = discoverer.discover_from_tags(["ai-agents", "llm"])

    curator = ArticleCurator()
    curated = curator.curate(candidates, keywords=["agent", "Claude"], top_n=10)
    for article in curated:
        print(f"  [{article.relevance_score:.1f}] {article.title}")
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from agents.base import BaseAgent, Model, Provider

if TYPE_CHECKING:
    from knowledge.medium_scraper import DiscoveredArticle

log = logging.getLogger(__name__)

# Minimum gap between candidates and top_n that makes LLM filtering worthwhile.
# E.g. if you want top 10 and only have 11 candidates, ranking 11 items is pointless.
_LLM_MIN_SURPLUS = 5
# Absolute minimum candidates before LLM is called at all.
_LLM_MIN_CANDIDATES = 8


def _should_use_llm(n_candidates: int, top_n: int) -> tuple[bool, str]:
    """
    Decide whether calling the LLM to curate is actually worthwhile.

    The LLM adds value when it has a meaningful filtering problem:
    enough candidates that manual ranking would surface different picks than
    just taking the top-scored ones.

    Returns:
        (use_llm, reason_string)
    """
    if n_candidates < _LLM_MIN_CANDIDATES:
        return (
            False,
            f"{n_candidates} candidates < min threshold ({_LLM_MIN_CANDIDATES}) — returning all by score",
        )
    surplus = n_candidates - top_n
    if surplus < _LLM_MIN_SURPLUS:
        return False, (
            f"only {surplus} articles to cut (need ≥ {_LLM_MIN_SURPLUS} surplus) — "
            "returning top-scored without LLM"
        )
    return True, f"filtering {n_candidates} → top {top_n} with LLM"


CURATOR_SYSTEM_PROMPT = """\
You are an expert AI/tech content curator. Your job is to evaluate a list of \
discovered Medium articles and select the most valuable ones for a developer \
who is building AI-powered projects.

Evaluation criteria (in order of importance):
1. **Practical value** — Does it teach something actionable? Code examples, \
architecture patterns, real-world experience?
2. **Relevance** — Does it match the user's interests (keywords provided)?
3. **Depth** — Is it likely a substantial article (not just a listicle or \
news summary)?
4. **Freshness** — Does the topic cover current tools/techniques?
5. **Engagement** — Higher claps/responses suggest community validation.

You will receive articles as a JSON array. Return a JSON array of the \
selected articles (by index, 0-based) with a brief reason for each selection.

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation outside JSON.
Format:
[
  {"index": 0, "reason": "Practical guide on agent architecture with code examples"},
  {"index": 3, "reason": "Deep dive into local RAG with ChromaDB — directly relevant"}
]
"""


class ArticleCurator(BaseAgent):
    """
    LLM-powered article curator that evaluates discovered articles.

    Subclasses BaseAgent to use Claude or GPT for content evaluation.
    Falls back gracefully if no API key is available.
    """

    name = "ArticleCurator"
    system_prompt = CURATOR_SYSTEM_PROMPT

    def __init__(self) -> None:
        # Auto-detect available provider
        provider, model = _detect_provider()
        super().__init__(model=model, provider=provider, max_tokens=2048)

    def curate(
        self,
        candidates: list[DiscoveredArticle],
        keywords: list[str] | None = None,
        top_n: int = 10,
    ) -> list[DiscoveredArticle]:
        """
        Evaluate candidates with an LLM and return the top picks.

        Args:
            candidates: Articles from TrendDiscoverer
            keywords: User's interest keywords (for context)
            top_n: How many articles the LLM should select

        Returns:
            Curated list of DiscoveredArticle, re-scored by the LLM's ranking.
            Returns empty list if curation fails (caller should fall back to
            the original candidates).
        """
        if not candidates:
            return []

        # Decide whether LLM curation is worth the API cost
        use_llm, reason = _should_use_llm(len(candidates), top_n)
        log.info("LLM curation: %s — %s", "enabled" if use_llm else "skipped", reason)
        if not use_llm:
            # Return top-n by existing relevance score without calling the LLM
            sorted_candidates = sorted(candidates, key=lambda c: c.relevance_score, reverse=True)
            return sorted_candidates[:top_n]

        # Prepare article summaries for the LLM (limit context)
        article_data = []
        for i, c in enumerate(candidates[:50]):  # cap at 50 to fit context
            entry: dict[str, object] = {
                "index": i,
                "title": c.title,
                "author": c.author,
                "tags": c.tags[:5],
                "summary": c.summary[:200],
            }
            if c.claps > 0:
                entry["claps"] = c.claps
            if c.responses > 0:
                entry["responses"] = c.responses
            if c.reading_time > 0:
                entry["reading_time_min"] = c.reading_time
            article_data.append(entry)

        prompt = f"""Here are {len(article_data)} discovered articles.
User's interests: {", ".join(keywords) if keywords else "general AI/tech development"}

Select the top {top_n} most valuable articles. Return ONLY a JSON array.

Articles:
{json.dumps(article_data, indent=2)}"""

        log.info("Curating %d candidates with %s...", len(article_data), self.model)
        try:
            response = self.complete(prompt)
            selections = _parse_selections(response)
        except Exception as e:
            log.error("LLM curation failed: %s", e)
            return []

        if not selections:
            log.warning("LLM returned no valid selections, falling back to original ranking")
            return []

        # Build curated list with LLM-assigned relevance scores
        curated: list[DiscoveredArticle] = []
        for rank, sel in enumerate(selections):
            idx = sel.get("index", -1)
            if not isinstance(idx, int) or idx < 0 or idx >= len(candidates):
                continue
            article = candidates[idx]
            # Boost score based on LLM ranking position (top pick gets highest boost)
            llm_boost = (top_n - rank) * 2.0
            article.relevance_score += llm_boost
            curated.append(article)

        # Print LLM reasoning
        print(f"\n{'=' * 80}")
        print(f"  LLM CURATION — {self.model} selected {len(curated)} articles")
        print(f"{'=' * 80}\n")
        for rank, sel in enumerate(selections, 1):
            idx = sel.get("index", -1)
            reason = str(sel.get("reason", ""))
            if isinstance(idx, int) and 0 <= idx < len(candidates):
                title = candidates[idx].title[:65]
                print(f"  {rank:2d}. {title}")
                if reason:
                    print(f"      → {reason}")
                print()

        curated.sort(key=lambda c: c.relevance_score, reverse=True)
        return curated


def _detect_provider() -> tuple[Provider, Model]:
    """Auto-detect which LLM provider is available from environment."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic", "claude-haiku-4-5"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", "gpt-4o-mini"
    raise OSError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env "
        "to enable LLM-powered article curation."
    )


def _parse_selections(response: str) -> list[dict[str, object]]:
    """Parse LLM response into a list of selection dicts."""
    # Strip markdown code fences if present
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last ``` lines
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines)

    # Find JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        log.warning("No JSON array found in LLM response")
        return []

    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError as e:
        log.warning("Failed to parse LLM JSON: %s", e)
    return []
