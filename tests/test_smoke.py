"""
Smoke tests — verify the project structure and imports work correctly.
No API calls are made here; all tests run offline.
"""

import importlib
import os
import sys
from pathlib import Path

# Ensure src/ is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ── Core ──────────────────────────────────────────────────────────────────────


def test_main_importable():
    mod = importlib.import_module("main")
    assert hasattr(mod, "main")


def test_main_runs_without_args(monkeypatch):
    """main() with no --demo flag must not raise and must not call any API."""
    monkeypatch.setattr("sys.argv", ["main.py"])
    from main import main

    main()  # should just print usage and return


# ── Utils ─────────────────────────────────────────────────────────────────────


def test_setup_logging():
    import logging

    from utils.logger_config import setup_logging

    logger = setup_logging("DEBUG")
    assert isinstance(logger, logging.Logger)


# ── Agents ────────────────────────────────────────────────────────────────────


def test_base_agent_requires_api_key(monkeypatch):
    """BaseAgent must raise EnvironmentError if the provider's API key is absent."""
    import pytest

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from agents.base import BaseAgent

    with pytest.raises(OSError):
        BaseAgent(provider="anthropic")
    with pytest.raises(OSError):
        BaseAgent(model="gpt-4o-mini", provider="openai")


# ── Knowledge / Scraper ───────────────────────────────────────────────────────


def test_scraper_importable():
    from knowledge.medium_scraper import MediumScraper

    assert callable(MediumScraper)


def test_article_slug_is_safe():
    from knowledge.medium_scraper import Article

    a = Article(
        title="Hello! World & Things: A Guide (2024)",
        url="https://medium.com/test",
        author="Test",
        published="",
        tags=[],
        summary="",
        content_md="",
        source_feed="",
    )
    slug = a.slug
    assert " " not in slug
    assert "!" not in slug
    assert len(slug) <= 70


def test_html_to_markdown():
    from knowledge.medium_scraper import MediumScraper

    html = "<h2>Title</h2><p>Hello <b>world</b></p><ul><li>Item 1</li></ul>"
    md = MediumScraper._html_to_markdown(html)
    assert "## Title" in md
    assert "- Item 1" in md


def test_html_to_markdown_pre_preserves_newlines():
    """<pre> blocks must preserve internal newlines."""
    from knowledge.medium_scraper import MediumScraper

    html = "<pre>line1\nline2\nline3</pre>"
    md = MediumScraper._html_to_markdown(html)
    assert "line1\nline2\nline3" in md
    assert md.startswith("```")


def test_html_to_markdown_pre_code_no_double_processing():
    """<code> inside <pre> must not create duplicate code blocks."""
    from knowledge.medium_scraper import MediumScraper

    html = '<pre><code class="language-python">import os\nprint(os.getcwd())</code></pre>'
    md = MediumScraper._html_to_markdown(html)
    # Should have exactly one fenced code block
    assert md.count("```") == 2  # opening + closing
    assert "import os" in md
    assert "print(os.getcwd())" in md


def test_html_to_markdown_inline_code():
    """Standalone <code> in a paragraph must render as inline backticks, not a fenced block."""
    from knowledge.medium_scraper import MediumScraper

    html = "<p>Use <code>pip install</code> to install packages.</p>"
    md = MediumScraper._html_to_markdown(html)
    assert "`pip install`" in md
    # Must NOT be a fenced code block
    assert "```" not in md


def test_html_to_markdown_language_detection_from_class():
    """Language class on <pre> or <code> element should be detected."""
    from knowledge.medium_scraper import MediumScraper

    html = '<pre class="language-python">import os</pre>'
    md = MediumScraper._html_to_markdown(html)
    assert "```python" in md


def test_html_to_markdown_language_detection_from_content():
    """Code blocks without a class should get language guessed from content."""
    from knowledge.medium_scraper import MediumScraper

    html = "<pre>pip install requests\ncurl https://example.com</pre>"
    md = MediumScraper._html_to_markdown(html)
    assert "```bash" in md


def test_guess_language_from_content():
    """Test the language guessing heuristic directly."""
    from knowledge.medium_scraper import _guess_language_from_content

    assert _guess_language_from_content("import os\nprint('hello')") == "python"
    assert _guess_language_from_content("pip install requests") == "bash"
    assert _guess_language_from_content("const x = 42;\nfunction foo() {}") == "javascript"
    assert _guess_language_from_content('{"key": "value"}') == "json"
    assert _guess_language_from_content("SELECT * FROM users") == "sql"


def test_paragraphs_to_markdown_language_guess():
    """Apollo PRE paragraphs with no explicit lang should get heuristic-detected language."""
    from knowledge.medium_scraper import MediumScraper

    paragraphs = [
        {"type": "PRE", "text": "import torch\nmodel = torch.nn.Linear(10, 5)"},
    ]
    md = MediumScraper._paragraphs_to_markdown(paragraphs)
    assert "```python" in md


def test_scraper_saves_to_tempdir(monkeypatch, tmp_path):
    """MediumScraper._save() writes .md and .json files."""
    import knowledge.medium_scraper as sc_mod

    monkeypatch.setattr(sc_mod, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(sc_mod, "META_DIR", tmp_path / "meta")

    from knowledge.medium_scraper import Article, MediumScraper

    scraper = MediumScraper()
    article = Article(
        title="Test Article About AI",
        url="https://medium.com/test/abc",
        author="Alice",
        published="2024-01-01",
        tags=["ai", "agents"],
        summary="A test summary.",
        content_md="## Intro\n\nHello world.",
        source_feed="https://medium.com/feed/tag/ai",
    )
    scraper._save(article)

    md_files = list((tmp_path / "raw").glob("*.md"))
    json_files = list((tmp_path / "meta").glob("*.json"))
    assert len(md_files) == 1
    assert len(json_files) == 1
    assert "Test Article About AI" in md_files[0].read_text(encoding="utf-8")


def test_scraper_dated_creates_subfolder(monkeypatch, tmp_path):
    """MediumScraper(dated=True) saves into a YYYY-MM-DD subfolder."""
    import knowledge.medium_scraper as sc_mod

    monkeypatch.setattr(sc_mod, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(sc_mod, "META_DIR", tmp_path / "meta")

    from knowledge.medium_scraper import Article, MediumScraper

    scraper = MediumScraper(dated=True)
    article = Article(
        title="Dated Article",
        url="https://medium.com/test/dated",
        author="Bob",
        published="2025-06-15",
        tags=["test"],
        summary="Testing dated output.",
        content_md="## Content\n\nDated content.",
        source_feed="https://medium.com/feed/tag/test",
    )
    scraper._save(article)

    # Should have a date subfolder under raw/
    subdirs = [d for d in (tmp_path / "raw").iterdir() if d.is_dir()]
    assert len(subdirs) == 1
    # Subfolder name should be a valid date (YYYY-MM-DD)
    assert len(subdirs[0].name) == 10  # e.g. "2026-03-25"
    assert subdirs[0].name[4] == "-" and subdirs[0].name[7] == "-"

    md_files = list(subdirs[0].glob("*.md"))
    assert len(md_files) == 1
    assert "Dated Article" in md_files[0].read_text(encoding="utf-8")


def test_scraper_output_dir_creates_dedicated_folder(tmp_path):
    """MediumScraper(output_dir=path) saves into that custom directory."""
    from knowledge.medium_scraper import Article, MediumScraper

    custom_dir = tmp_path / "custom" / "mylist"
    scraper = MediumScraper(output_dir=str(custom_dir))
    article = Article(
        title="Custom Folder Article",
        url="https://medium.com/test/custom",
        author="Eve",
        published="2026-01-01",
        tags=["custom"],
        summary="Testing custom output dir.",
        content_md="## Custom\n\nCustom content.",
        source_feed="direct",
    )
    scraper._save(article)

    md_files = list(custom_dir.glob("*.md"))
    assert len(md_files) == 1
    assert "Custom Folder Article" in md_files[0].read_text(encoding="utf-8")

    # Meta dir should be sibling of custom dir
    meta_dir = custom_dir.parent / "meta"
    json_files = list(meta_dir.glob("*.json"))
    assert len(json_files) == 1


# ── TrendDiscoverer / Discovery ───────────────────────────────────────────────


def test_discovered_article_engagement_score():
    from knowledge.medium_scraper import DiscoveredArticle

    article = DiscoveredArticle(title="Test", url="https://medium.com/a", author="A")
    assert article.engagement_score == 0.0

    article.claps = 100
    article.responses = 5
    assert article.engagement_score == 150.0  # 100 + 5*10


def test_discovered_article_defaults():
    from knowledge.medium_scraper import DiscoveredArticle

    article = DiscoveredArticle(title="T", url="u", author="A")
    assert article.claps == 0
    assert article.responses == 0
    assert article.reading_time == 0
    assert article.tags == []
    assert article.summary == ""
    assert article.relevance_score == 0.0
    assert article.source_tag == ""


def test_parse_count_plain_numbers():
    from knowledge.medium_scraper import _parse_count

    assert _parse_count("42") == 42
    assert _parse_count("0") == 0
    assert _parse_count("1000") == 1000


def test_parse_count_k_suffix():
    from knowledge.medium_scraper import _parse_count

    assert _parse_count("1.2K") == 1200
    assert _parse_count("5k") == 5000
    assert _parse_count("0.5K") == 500


def test_parse_count_m_suffix():
    from knowledge.medium_scraper import _parse_count

    assert _parse_count("1M") == 1_000_000
    assert _parse_count("2.5m") == 2_500_000


def test_parse_count_invalid():
    from knowledge.medium_scraper import _parse_count

    assert _parse_count("abc") == 0
    assert _parse_count("") == 0


def test_score_candidate_no_keywords():
    from knowledge.medium_scraper import DiscoveredArticle, TrendDiscoverer

    td = TrendDiscoverer()
    candidate = DiscoveredArticle(title="AI Agents", url="u", author="A")
    assert td._score_candidate(candidate, None) == 1.0
    assert td._score_candidate(candidate, []) == 1.0


def test_score_candidate_title_match():
    from knowledge.medium_scraper import DiscoveredArticle, TrendDiscoverer

    td = TrendDiscoverer()
    candidate = DiscoveredArticle(
        title="Building AI Agents with Python",
        url="u",
        author="A",
        tags=["coding"],
        summary="A tutorial.",
    )
    score = td._score_candidate(candidate, ["AI", "Python"])
    # base 1.0 + "ai" in title +3 + "python" in title +3 = 7.0
    assert score == 7.0


def test_score_candidate_tag_match():
    from knowledge.medium_scraper import DiscoveredArticle, TrendDiscoverer

    td = TrendDiscoverer()
    candidate = DiscoveredArticle(
        title="Something Unrelated",
        url="u",
        author="A",
        tags=["ai-agents", "llm"],
        summary="No keywords here.",
    )
    score = td._score_candidate(candidate, ["agents"])
    # base 1.0 + "agents" in tags_lower +2 = 3.0
    assert score == 3.0


def test_score_candidate_summary_match():
    from knowledge.medium_scraper import DiscoveredArticle, TrendDiscoverer

    td = TrendDiscoverer()
    candidate = DiscoveredArticle(
        title="Boring Title",
        url="u",
        author="A",
        tags=["other"],
        summary="This is about scraping Medium articles.",
    )
    score = td._score_candidate(candidate, ["scraping"])
    # base 1.0 + "scraping" in combined text +1 = 2.0
    assert score == 2.0


def test_extract_clap_count_apollo():
    from knowledge.medium_scraper import TrendDiscoverer

    html = '{"data":{"clapCount":42,"otherField":"x"}}'
    assert TrendDiscoverer._extract_clap_count(html) == 42


def test_extract_clap_count_text():
    from knowledge.medium_scraper import TrendDiscoverer

    html = "<span>1.2K claps</span>"
    assert TrendDiscoverer._extract_clap_count(html) == 1200


def test_extract_clap_count_none():
    from knowledge.medium_scraper import TrendDiscoverer

    assert TrendDiscoverer._extract_clap_count("<p>no data</p>") == 0


def test_extract_response_count():
    from knowledge.medium_scraper import TrendDiscoverer

    html = '"postResponses":{"count":7}'
    assert TrendDiscoverer._extract_response_count(html) == 7

    html2 = "<span>3 responses</span>"
    assert TrendDiscoverer._extract_response_count(html2) == 3

    assert TrendDiscoverer._extract_response_count("<p>nothing</p>") == 0


def test_extract_reading_time():
    from knowledge.medium_scraper import TrendDiscoverer

    html = '"readingTime":8.5'
    assert TrendDiscoverer._extract_reading_time(html) == 8

    html2 = "<span>12 min read</span>"
    assert TrendDiscoverer._extract_reading_time(html2) == 12

    assert TrendDiscoverer._extract_reading_time("<p>nothing</p>") == 0


def test_trend_discoverer_importable():
    from knowledge.medium_scraper import TrendDiscoverer

    td = TrendDiscoverer()
    assert callable(td.discover_from_tags)
    assert callable(td.discover_from_page)
    assert callable(td.enrich_with_metadata)


# ── ArticleCurator ────────────────────────────────────────────────────────────


def test_article_curator_importable():
    from knowledge.article_curator import ArticleCurator

    assert callable(ArticleCurator)


def test_article_curator_requires_api_key(monkeypatch):
    """ArticleCurator must raise OSError when no API keys are set."""
    import pytest

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from knowledge.article_curator import ArticleCurator

    with pytest.raises(OSError, match="No LLM API key found"):
        ArticleCurator()


def test_detect_provider_anthropic(monkeypatch):
    """Should detect Anthropic when ANTHROPIC_API_KEY is set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from knowledge.article_curator import _detect_provider

    provider, model = _detect_provider()
    assert provider == "anthropic"
    assert "claude" in model


def test_detect_provider_openai(monkeypatch):
    """Should detect OpenAI when only OPENAI_API_KEY is set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    from knowledge.article_curator import _detect_provider

    provider, model = _detect_provider()
    assert provider == "openai"
    assert "gpt" in model


def test_parse_selections_valid_json():
    from knowledge.article_curator import _parse_selections

    response = '[{"index": 0, "reason": "Good article"}, {"index": 3, "reason": "Relevant"}]'
    result = _parse_selections(response)
    assert len(result) == 2
    assert result[0]["index"] == 0
    assert result[1]["index"] == 3


def test_parse_selections_with_markdown_fences():
    from knowledge.article_curator import _parse_selections

    response = '```json\n[{"index": 1, "reason": "Best pick"}]\n```'
    result = _parse_selections(response)
    assert len(result) == 1
    assert result[0]["index"] == 1


def test_parse_selections_with_surrounding_text():
    from knowledge.article_curator import _parse_selections

    response = 'Here are my picks:\n[{"index": 2, "reason": "Great"}]\nHope this helps!'
    result = _parse_selections(response)
    assert len(result) == 1
    assert result[0]["index"] == 2


def test_parse_selections_invalid_json():
    from knowledge.article_curator import _parse_selections

    assert _parse_selections("not json at all") == []
    assert _parse_selections("") == []
    assert _parse_selections("{}") == []  # not an array


def test_curate_empty_candidates(monkeypatch):
    """curate() with empty list should return empty list without calling LLM."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    from unittest.mock import patch

    from knowledge.article_curator import ArticleCurator

    with patch("knowledge.article_curator.BaseAgent.__init__"):
        curator = ArticleCurator.__new__(ArticleCurator)
        result = curator.curate([], keywords=["test"])
        assert result == []


def test_curate_with_mocked_llm(monkeypatch):
    """Full curate flow with mocked LLM response.
    Uses 15 candidates so the smart threshold allows the LLM to run.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    from unittest.mock import MagicMock, patch

    from knowledge.article_curator import ArticleCurator
    from knowledge.medium_scraper import DiscoveredArticle

    # Need enough candidates (> _LLM_MIN_CANDIDATES=8) with enough surplus
    # (> _LLM_MIN_SURPLUS=5) over top_n=2  →  15 candidates satisfies both
    base_candidates = [
        DiscoveredArticle(title=f"Generic Article {i}", url=f"https://medium.com/x{i}", author="X")
        for i in range(12)
    ]
    key_candidates = [
        DiscoveredArticle(
            title="Building AI Agents with Python",
            url="https://medium.com/a",
            author="Alice",
            tags=["ai-agents"],
            summary="How to build agents",
        ),
        DiscoveredArticle(
            title="Cooking Tips for Beginners",
            url="https://medium.com/b",
            author="Bob",
            tags=["cooking"],
            summary="How to cook pasta",
        ),
        DiscoveredArticle(
            title="Local RAG with ChromaDB",
            url="https://medium.com/c",
            author="Charlie",
            tags=["rag", "llm"],
            summary="Semantic search on local docs",
        ),
    ]
    # key candidates are at indices 12, 13, 14
    candidates = base_candidates + key_candidates

    mock_response = '[{"index": 12, "reason": "Directly about agents"}, {"index": 14, "reason": "RAG is relevant"}]'

    with patch.object(ArticleCurator, "__init__", lambda self: None):
        curator = ArticleCurator.__new__(ArticleCurator)
        curator.model = "test-model"
        curator.complete = MagicMock(return_value=mock_response)

        curated = curator.curate(candidates, keywords=["agent", "RAG"], top_n=2)

    assert len(curated) == 2
    # The agent article should be included
    urls = {a.url for a in curated}
    assert "https://medium.com/a" in urls
    assert "https://medium.com/c" in urls
    # Cooking article should NOT be included
    assert "https://medium.com/b" not in urls


# ── Data dirs ─────────────────────────────────────────────────────────────────


def test_knowledge_dirs_exist():
    base = Path(__file__).resolve().parent.parent / "data" / "knowledge"
    assert (base / "raw" / "medium").exists(), "Run setup.bat to create data dirs"
    assert (base / "meta").exists()
