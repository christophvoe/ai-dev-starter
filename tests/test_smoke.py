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


# ── Data dirs ─────────────────────────────────────────────────────────────────


def test_knowledge_dirs_exist():
    base = Path(__file__).resolve().parent.parent / "data" / "knowledge"
    assert (base / "raw" / "medium").exists(), "Run setup.bat to create data dirs"
    assert (base / "meta").exists()
