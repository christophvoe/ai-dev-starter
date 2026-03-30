"""
MediumScraper — fetch Medium articles and save them to the local knowledge base.

Full content (incl. member-only) is extracted from Medium's embedded Apollo
GraphQL state (window.__APOLLO_STATE__), which contains the complete article
body when the request carries valid session cookies.  Cloudflare is bypassed
automatically via Chrome TLS impersonation (curl_cffi).

Authentication — one-time setup:
  1. Open medium.com in Chrome/Edge while logged in
  2. F12 → Application → Cookies → https://medium.com
  3. Copy the Value of "sid" and "uid"
  4. Add to .env:  MEDIUM_COOKIES=sid=VALUE; uid=VALUE
  After that, no --cookies flag is ever needed.

Usage (CLI):
    # Named list (the main use-case) — cookies auto-loaded from .env
    python -m knowledge.medium_scraper --list URL --max 20
    python -m knowledge.medium_scraper --list URL1 --list URL2 --max 20

    # Public RSS feeds (no credentials needed)
    python -m knowledge.medium_scraper --tag "ai-agents" --max 10
    python -m knowledge.medium_scraper --user towardsdatascience --max 10
    python -m knowledge.medium_scraper --url "https://medium.com/feed/tag/llm"

    # Single article
    python -m knowledge.medium_scraper --article https://medium.com/...

    # Medium data export (.zip from https://medium.com/me/export)
    python -m knowledge.medium_scraper --export-zip path/to/medium-export.zip

    # General bookmarks
    python -m knowledge.medium_scraper --bookmarks --max 20

Usage (Python):
    from knowledge.medium_scraper import MediumScraper
    scraper = MediumScraper(cookie_string="sid=...; uid=...")
    scraper.fetch_list("https://medium.com/@user/list/name-abc123", max_articles=20)
    scraper.fetch_tag("ai-agents", max_articles=10)
    scraper.fetch_article_by_url("https://medium.com/@author/title-abc123")
"""

import argparse
import hashlib
import json
import logging
import re
import time
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as cf_requests

    _CURL_AVAILABLE = True
except ImportError:
    _CURL_AVAILABLE = False

log = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"
RAW_DIR = KNOWLEDGE_DIR / "raw" / "medium"
META_DIR = KNOWLEDGE_DIR / "meta"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY = 1.5  # seconds between requests — be polite

# Medium article URLs: protocol + (sub)domain ending in medium.com + path with a hex-hash suffix
# Examples: https://medium.com/@author/title-a1b2c3d4e5f6
#           https://towardsdatascience.com/title-abc123456789
_MEDIUM_ARTICLE_RE = re.compile(
    r'(https?://(?:[a-z0-9-]+\.)*medium\.com/(?:[^"\'<>\s]+/)?[^"\'<>\s]+-[0-9a-f]{8,12})'
)

# ── Code language detection ──────────────────────────────────────────
_CODE_LANG_MAP = {
    "python": "python",
    "py": "python",
    "python3": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "yaml": "yaml",
    "yml": "yaml",
    "json": "json",
    "sql": "sql",
    "html": "html",
    "xml": "xml",
    "css": "css",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "java": "java",
    "kotlin": "kotlin",
    "go": "go",
    "golang": "go",
    "rust": "rust",
    "rs": "rust",
    "ruby": "ruby",
    "rb": "ruby",
    "r": "r",
    "toml": "toml",
    "ini": "ini",
    "dockerfile": "dockerfile",
    "docker": "dockerfile",
    "makefile": "makefile",
    "text": "text",
    "plaintext": "text",
}


def _guess_language_from_content(text: str) -> str:
    """Guess code language from the first few lines of content."""
    first_lines = text.strip().splitlines()[:10]
    joined = "\n".join(first_lines)

    # Shebang
    if first_lines and first_lines[0].startswith("#!"):
        if "python" in first_lines[0]:
            return "python"
        if "node" in first_lines[0]:
            return "javascript"
        return "bash"

    # Shell patterns
    if re.search(
        r"^\s*(\$|pip |pip3 |apt |brew |npm |conda |git |curl |wget |docker |mkdir |chmod )",
        joined,
        re.M,
    ):
        return "bash"
    if re.search(r"^\s*(export |source |alias |sudo |echo )", joined, re.M):
        return "bash"

    # Python patterns
    if re.search(r"^\s*(import |from \w+ import |def |class |async def |@\w+)", joined, re.M):
        return "python"
    if re.search(r"^\s*(print\(|if __name__)", joined, re.M):
        return "python"

    # JavaScript/TypeScript patterns
    if re.search(r"^\s*(const |let |var |function |=>|require\(|import .+ from )", joined, re.M):
        return "javascript"

    # YAML patterns
    if re.search(r"^\w[\w_-]*:\s*(\n|$)", joined, re.M) and ":" in joined:
        return "yaml"

    # JSON
    if joined.lstrip().startswith("{") or joined.lstrip().startswith("["):
        return "json"

    # SQL
    if re.search(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s", joined, re.M | re.I):
        return "sql"

    # HTML/XML
    if re.search(r"^\s*<(!DOCTYPE|html|div|span|head|body)", joined, re.M | re.I):
        return "html"

    # Dockerfile
    if re.search(r"^\s*(FROM |RUN |COPY |CMD |ENTRYPOINT )", joined, re.M):
        return "dockerfile"

    return "text"


@dataclass
class Article:
    title: str
    url: str
    author: str
    published: str
    tags: list[str]
    summary: str
    content_md: str
    source_feed: str
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now(UTC).isoformat()

    @property
    def slug(self) -> str:
        """Filesystem-safe filename stem."""
        safe = re.sub(r"[^\w\s-]", "", self.title.lower())
        safe = re.sub(r"[\s_-]+", "-", safe).strip("-")
        uid = hashlib.md5(self.url.encode()).hexdigest()[:6]
        return f"{safe[:60]}-{uid}"


@dataclass
class DiscoveredArticle:
    """A candidate article found during trend discovery, scored by relevance."""

    title: str
    url: str
    author: str
    claps: int = 0
    responses: int = 0
    reading_time: int = 0
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    relevance_score: float = 0.0
    source_tag: str = ""

    @property
    def engagement_score(self) -> float:
        """Simple engagement score from claps + responses."""
        return float(self.claps) + float(self.responses) * 10.0


class TrendDiscoverer:
    """
    Discover trending/hot articles from Medium tags and RSS feeds.

    Scores articles by engagement (claps, responses) and optionally filters
    by keyword relevance. Can use an LLM to assess article quality if an
    API key is available.

    Usage:
        discoverer = TrendDiscoverer(cookie_string="sid=...; uid=...")
        candidates = discoverer.discover_from_tags(
            tags=["ai-agents", "llm", "n8n", "automation"],
            keywords=["agent", "trading", "scraper", "Claude"],
            max_per_tag=15,
        )
        # candidates are sorted by relevance_score (highest first)
        for c in candidates[:10]:
            print(f"{c.relevance_score:.1f} | {c.title}")
    """

    def __init__(self, cookie_string: str = "") -> None:
        self._cookie_string = cookie_string
        self._headers = HEADERS

    def _get(self, url: str, timeout: int = 15) -> requests.Response:
        """GET with optional curl_cffi for Cloudflare bypass."""
        if self._cookie_string and _CURL_AVAILABLE:
            cookies_dict: dict[str, str] = {}
            for part in self._cookie_string.split(";"):
                k, _, v = part.strip().partition("=")
                if k:
                    cookies_dict[k.strip()] = v.strip()
            return cf_requests.get(
                url,
                headers=self._headers,
                cookies=cookies_dict,
                impersonate="chrome120",
                verify=False,
                timeout=timeout,
            )
        return requests.get(url, headers=self._headers, timeout=timeout)

    def discover_from_tags(
        self,
        tags: list[str],
        keywords: list[str] | None = None,
        max_per_tag: int = 15,
        min_score: float = 0.0,
    ) -> list[DiscoveredArticle]:
        """
        Discover trending articles from multiple Medium tags via RSS.

        Fetches RSS feeds for each tag, extracts metadata, scores by engagement
        and keyword relevance, deduplicates, and returns sorted candidates.
        """
        all_candidates: list[DiscoveredArticle] = []
        seen_urls: set[str] = set()

        for tag in tags:
            feed_url = f"https://medium.com/feed/tag/{tag}"
            log.info("Discovering from tag '%s'...", tag)
            try:
                feed = feedparser.parse(feed_url)
                entries = feed.entries[:max_per_tag]
            except Exception as e:
                log.warning("Failed to parse feed for tag '%s': %s", tag, e)
                continue

            for entry in entries:
                url = (entry.get("link") or "").split("?")[0].rstrip("/")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = entry.get("title", "")
                author = entry.get("author", "Unknown")
                entry_tags = [t.get("term", "") for t in entry.get("tags", [])]
                raw_summary = entry.get("summary", "")
                summary = BeautifulSoup(raw_summary, "lxml").get_text(strip=True)[:300]

                candidate = DiscoveredArticle(
                    title=title,
                    url=url,
                    author=author,
                    tags=entry_tags,
                    summary=summary,
                    source_tag=tag,
                )
                candidate.relevance_score = self._score_candidate(candidate, keywords)
                all_candidates.append(candidate)

            time.sleep(REQUEST_DELAY)

        # Sort by relevance (highest first), filter by min_score
        all_candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        if min_score > 0:
            all_candidates = [c for c in all_candidates if c.relevance_score >= min_score]

        log.info(
            "Discovered %d candidates from %d tags (after dedup)",
            len(all_candidates),
            len(tags),
        )
        return all_candidates

    def discover_from_page(
        self,
        page_url: str,
        keywords: list[str] | None = None,
    ) -> list[DiscoveredArticle]:
        """
        Discover articles from any Medium page (tag page, publication, etc.).

        Extracts article URLs from the HTML and scores them.
        """
        try:
            resp = self._get(page_url, timeout=15)
            if resp.status_code != 200:
                log.error("Page returned HTTP %d: %s", resp.status_code, page_url)
                return []
        except Exception as e:
            log.error("Failed to fetch %s: %s", page_url, e)
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        candidates: list[DiscoveredArticle] = []
        seen: set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/"):
                href = f"https://medium.com{href}"
            href = href.split("?")[0].rstrip("/")

            if not _MEDIUM_ARTICLE_RE.match(href):
                continue
            if href in seen or "/list/" in href or "/m/signin" in href:
                continue
            seen.add(href)

            title = a_tag.get_text(strip=True)
            if len(title) < 10:
                parent = a_tag.find_parent(["div", "article", "section"])
                if parent:
                    heading = parent.find(["h2", "h3", "h1"])
                    if heading:
                        title = heading.get_text(strip=True)

            candidate = DiscoveredArticle(title=title, url=href, author="")
            candidate.relevance_score = self._score_candidate(candidate, keywords)
            candidates.append(candidate)

        candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        log.info("Discovered %d articles from page %s", len(candidates), page_url)
        return candidates

    def enrich_with_metadata(
        self, candidates: list[DiscoveredArticle], max_enrich: int = 20
    ) -> list[DiscoveredArticle]:
        """
        Fetch each candidate's page to extract clap count, response count,
        and reading time. Re-scores after enrichment.
        """
        for candidate in candidates[:max_enrich]:
            try:
                resp = self._get(candidate.url, timeout=10)
                if resp.status_code != 200:
                    continue
                html = resp.text

                claps = self._extract_clap_count(html)
                responses = self._extract_response_count(html)
                reading_time = self._extract_reading_time(html)

                candidate.claps = claps
                candidate.responses = responses
                candidate.reading_time = reading_time

                engagement_bonus = min(candidate.engagement_score / 100.0, 5.0)
                candidate.relevance_score += engagement_bonus

                time.sleep(REQUEST_DELAY)
            except Exception as e:
                log.debug("Could not enrich %s: %s", candidate.url, e)

        candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        return candidates

    def _score_candidate(self, candidate: DiscoveredArticle, keywords: list[str] | None) -> float:
        """Score a candidate by keyword match in title, tags, and summary."""
        score = 1.0  # base score for appearing in an RSS feed

        if not keywords:
            return score

        title_lower = candidate.title.lower()
        summary_lower = candidate.summary.lower()
        tags_lower = " ".join(candidate.tags).lower()
        text = f"{title_lower} {summary_lower} {tags_lower}"

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                score += 3.0  # title match is strongest signal
            elif kw_lower in tags_lower:
                score += 2.0
            elif kw_lower in text:
                score += 1.0

        return score

    @staticmethod
    def _extract_clap_count(html: str) -> int:
        """Extract clap count from Medium page HTML or Apollo state."""
        match = re.search(r'"clapCount"\s*:\s*(\d+)', html)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+(?:\.\d+)?[KkMm]?)\s*claps?", html)
        if match:
            return _parse_count(match.group(1))
        return 0

    @staticmethod
    def _extract_response_count(html: str) -> int:
        """Extract response/comment count from page."""
        match = re.search(r'"postResponses"\s*:\s*\{[^}]*"count"\s*:\s*(\d+)', html)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+)\s*responses?", html)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _extract_reading_time(html: str) -> int:
        """Extract reading time in minutes."""
        match = re.search(r'"readingTime"\s*:\s*([\d.]+)', html)
        if match:
            return int(float(match.group(1)))
        match = re.search(r"(\d+)\s*min\s*read", html)
        if match:
            return int(match.group(1))
        return 0

    def print_report(self, candidates: list[DiscoveredArticle], top_n: int = 20) -> None:
        """Print a formatted report of discovered articles (Windows-safe UTF-8 output)."""
        import contextlib
        import sys

        out = sys.stdout
        # On Windows the default stdout may be cp1252 — reconfigure to UTF-8
        if hasattr(out, "reconfigure"):
            with contextlib.suppress(Exception):
                out.reconfigure(encoding="utf-8", errors="replace")

        out.write(f"\n{'=' * 80}\n")
        out.write(f"  TRENDING ARTICLES — Top {min(top_n, len(candidates))} of {len(candidates)}\n")
        out.write(f"{'=' * 80}\n\n")

        for i, c in enumerate(candidates[:top_n], 1):
            engagement = f"claps:{c.claps}" if c.claps else ""
            responses = f"replies:{c.responses}" if c.responses else ""
            reading = f"{c.reading_time}min" if c.reading_time else ""
            meta = "  ".join(filter(None, [engagement, responses, reading]))

            title = c.title.encode("utf-8", errors="replace").decode("utf-8")
            out.write(f"  {i:2d}. [{c.relevance_score:.1f}] {title}\n")
            out.write(f"      {c.url}\n")
            if meta:
                out.write(f"      {meta}\n")
            if c.tags:
                out.write(f"      Tags: {', '.join(c.tags[:5])}\n")
            out.write("\n")
        out.flush()


def _parse_count(raw: str) -> int:
    """Parse '1.2K' or '3M' into integer."""
    raw = raw.strip()
    multiplier = 1
    if raw.endswith(("K", "k")):
        multiplier = 1000
        raw = raw[:-1]
    elif raw.endswith(("M", "m")):
        multiplier = 1_000_000
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return 0


class MediumScraper:
    """
    Fetches Medium articles via RSS and saves them as Markdown + JSON metadata.
    """

    def __init__(
        self,
        cookie_string: str = "",
        output_dir: str | Path | None = None,
        dated: bool = False,
    ):
        base_dir = Path(output_dir).resolve() if output_dir else RAW_DIR

        if dated:
            date_stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
            base_dir = base_dir / date_stamp

        self._raw_dir = base_dir
        if output_dir:
            self._meta_dir = base_dir.parent / "meta"
        else:
            self._meta_dir = META_DIR

        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._meta_dir.mkdir(parents=True, exist_ok=True)
        self._cookie_string = cookie_string  # used for Cloudflare bypass via curl_cffi

    def _get(self, url: str, timeout: int = 15, allow_redirects: bool = True) -> requests.Response:
        """
        Make a GET request, using curl_cffi with Chrome impersonation when cookies
        are set (required to pass Cloudflare bot protection on Medium).
        Falls back to plain requests otherwise.
        """
        if self._cookie_string and _CURL_AVAILABLE:
            cookies_dict = {}
            for part in self._cookie_string.split(";"):
                k, _, v = part.strip().partition("=")
                if k:
                    cookies_dict[k.strip()] = v.strip()
            return cf_requests.get(
                url,
                headers=HEADERS,
                cookies=cookies_dict,
                impersonate="chrome120",
                verify=False,
                timeout=timeout,
                allow_redirects=allow_redirects,
            )
        return requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=allow_redirects)

    # ------------------------------------------------------------------
    # High-level convenience
    # ------------------------------------------------------------------

    def fetch_tag(self, tag: str, max_articles: int = 10) -> list[Article]:
        """Fetch articles for a Medium tag (e.g. 'ai-agents')."""
        feed_url = f"https://medium.com/feed/tag/{tag}"
        log.info("Fetching tag '%s' -> %s", tag, feed_url)
        return self._process_feed(feed_url, max_articles=max_articles)

    def fetch_user(self, username: str, max_articles: int = 10) -> list[Article]:
        """Fetch articles for a Medium user (e.g. 'towardsdatascience')."""
        username = username.lstrip("@")
        feed_url = f"https://medium.com/feed/@{username}"
        log.info("Fetching user '@%s' -> %s", username, feed_url)
        return self._process_feed(feed_url, max_articles=max_articles)

    def fetch_url(self, feed_url: str, max_articles: int = 10) -> list[Article]:
        """Fetch from any Medium RSS URL directly."""
        log.info("Fetching feed: %s", feed_url)
        return self._process_feed(feed_url, max_articles=max_articles)

    def fetch_list(
        self, list_url: str, max_articles: int = 10, cookie_string: str = ""
    ) -> list[Article]:
        """
        Fetch articles from a Medium named list by its URL.

        Fetches the list page HTML and extracts article URLs from it.
        For public lists, you still need cookies (cf_clearance) to pass Cloudflare.

        Get cookies: DevTools → Network tab → any medium.com request →
        Request Headers → copy the full 'cookie:' line.

        Example: --list https://medium.com/@username/list/coding-6c7978acb372 --cookies "sid=...; uid=..."
        """
        log.info("Fetching list page: %s", list_url)
        if cookie_string:
            self._cookie_string = cookie_string
        try:
            resp = self._get(list_url, timeout=15)
            status_code = resp.status_code
            resp_text = resp.text

            if status_code == 403:
                log.error(
                    "List page returned 403 (Cloudflare blocked).\n"
                    "  Run with --cookies to pass your Medium login cookies:\n"
                    '  --list URL --cookies "sid=YOUR_SID; uid=YOUR_UID"\n'
                    "  (Just sid and uid are enough -- get them once from DevTools Application > Cookies)"
                )
                return []
            if status_code != 200:
                log.error("List page returned HTTP %d for %s", status_code, list_url)
                return []
        except Exception as e:
            log.error("Could not fetch list page %s: %s", list_url, e)
            return []

        article_urls = self._extract_article_urls(resp_text)

        # Keep only real article URLs:
        # - Must end with Medium's hex article ID (8-12 hex chars after a dash)
        # - Must not be a list page, sign-in page, or the list URL itself
        _article_hash_re = re.compile(r"-[0-9a-f]{8,12}$")
        seen_norm: set[str] = set()
        filtered: list[str] = []
        for u in article_urls:
            if not _article_hash_re.search(u):
                continue  # publication homepage, profile, or sign-in page
            if "/list/" in u or "/m/signin" in u:
                continue
            # Normalise alirezarezvani.medium.com → medium.com/@alirezarezvani to deduplicate
            norm = re.sub(r"https?://([a-z0-9-]+)\.medium\.com/", r"https://medium.com/@\1/", u)
            if norm not in seen_norm:
                seen_norm.add(norm)
                filtered.append(u)
        article_urls = filtered

        if not article_urls:
            log.error(
                "No article URLs found on list page '%s'.\n"
                "  The list may be empty, or the page did not load correctly.",
                list_url,
            )
            return []

        log.info("Found %d article URLs in list page", len(article_urls))
        articles = []
        for article_url in article_urls[:max_articles]:
            try:
                article = self._fetch_article_by_url(article_url)
                if article:
                    self._save(article)
                    articles.append(article)
                    log.info("  [OK] Saved: %s", article.title[:80])
                    time.sleep(REQUEST_DELAY)
            except Exception as e:
                log.warning("  [FAIL] '%s': %s", article_url, e)

        log.info(
            "Done -- saved %d/%d articles from list",
            len(articles),
            len(article_urls[:max_articles]),
        )
        return articles

    def fetch_from_export_zip(
        self, zip_path: str, max_articles: int | None = None
    ) -> list[Article]:
        """
        Process a Medium data export .zip file and save all bookmarked articles.

        How to get your export:
          1. Go to https://medium.com/me/export
          2. Click "Export your data" — Medium emails you a .zip file within minutes
          3. Pass the path to the .zip here (no need to unzip first)

        The .zip contains full HTML of every article you have bookmarked.
        """
        with zipfile.ZipFile(zip_path, "r") as zf:
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                zf.extractall(tmpdir)
                return self.fetch_from_export(tmpdir, max_articles=max_articles)

    def fetch_from_export(self, export_dir: str, max_articles: int | None = None) -> list[Article]:
        """
        Process an unzipped Medium data export folder and save all bookmarked articles.

        The export folder structure Medium uses:
          export-{userid}-{date}/
            bookmarks/
              posts/
                {article-slug}.html   ← each bookmarked article as full HTML
            posts/                    ← your own published articles
              {slug}.html

        This method processes bookmarks/posts/ by default (your saved articles).
        If that folder doesn't exist, it falls back to processing all .html files
        in the export root.
        """
        base = Path(export_dir)

        # Medium export puts bookmarks in bookmarks/posts/ or directly in bookmarks/
        candidates = [
            base / "bookmarks" / "posts",
            base / "bookmarks",
        ]
        # Also check one level deeper (export zip may have a top-level folder)
        for child in base.iterdir():
            if child.is_dir():
                candidates += [child / "bookmarks" / "posts", child / "bookmarks"]

        html_files: list[Path] = []
        for folder in candidates:
            if folder.is_dir():
                html_files = sorted(folder.glob("*.html"))
                if html_files:
                    log.info("Found %d HTML files in %s", len(html_files), folder)
                    break

        if not html_files:
            log.warning(
                "No HTML files found in expected Medium export structure under %s. "
                "Looking for any .html files in the directory...",
                export_dir,
            )
            html_files = sorted(base.rglob("*.html"))

        if not html_files:
            log.error("No HTML files found anywhere in %s", export_dir)
            return []

        if max_articles is not None:
            html_files = html_files[:max_articles]

        log.info("Processing %d HTML files from Medium export", len(html_files))
        articles = []
        for html_path in html_files:
            try:
                article = self._parse_export_html(html_path)
                if article:
                    self._save(article)
                    articles.append(article)
                    log.info("  [OK] Saved: %s", article.title[:80])
            except Exception as e:
                log.warning("  [FAIL] '%s': %s", html_path.name, e)

        log.info("Done -- saved %d/%d articles from export", len(articles), len(html_files))
        return articles

    def _parse_export_html(self, html_path: Path) -> Article | None:
        """Parse a single HTML file from a Medium export and return an Article."""
        html = html_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        # Title
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else html_path.stem

        # Author (Medium export includes byline)
        author = ""
        byline = soup.find(class_=lambda c: c and "author" in c.lower()) if soup else None
        if byline:
            author = byline.get_text(strip=True)

        # Canonical URL from <link rel="canonical"> or og:url
        url = ""
        canonical = soup.find("link", rel="canonical")
        if canonical:
            url = canonical.get("href", "")
        if not url:
            og_url = soup.find("meta", property="og:url")
            if og_url:
                url = og_url.get("content", "")
        if not url:
            url = f"file://{html_path}"

        # Published date
        published = ""
        pub_meta = soup.find("meta", property="article:published_time")
        if pub_meta:
            published = pub_meta.get("content", "")
        if not published:
            time_tag = soup.find("time")
            if time_tag:
                published = time_tag.get("datetime", time_tag.get_text(strip=True))

        # Tags
        tags = [t.get("content", "") for t in soup.find_all("meta", property="article:tag")]

        # Full content — prefer <article>, fall back to <body>
        article_elem = soup.find("article") or soup.find("body")
        content_html = str(article_elem) if article_elem else html
        content_md = self._html_to_markdown(content_html)
        summary = content_md[:500]

        if not content_md.strip():
            return None

        return Article(
            title=title,
            url=url,
            author=author,
            published=published,
            tags=tags,
            summary=summary,
            content_md=content_md,
            source_feed="medium-export",
        )

    # ------------------------------------------------------------------
    # Reading list via cookies (Medium internal JSON API)
    # ------------------------------------------------------------------

    def check_cookies(self, cookie_string: str) -> None:
        """
        Diagnostic: verify your Medium cookies work and print what they can access.

        Pass the full cookie string from your browser's Network tab:
          DevTools → Network → click any medium.com request → Headers →
          scroll to "Request Headers" → copy the "cookie:" line value

        Or pass just:  sid=xxx; uid=xxx
        """
        self._cookie_string = cookie_string  # ensure _get() uses these cookies
        print("\n-- Medium Cookie Check -----------------------------------------")

        # 1. Check if we can reach a JSON profile endpoint (proves auth works)
        try:
            resp = self._get(
                "https://medium.com/me?format=json",
                timeout=10,
                allow_redirects=False,
            )
            # Medium JSON endpoints use an XSSI prefix "])}while(1);</x>"
            _xssi = "])}while(1);</x>"
            text = resp.text.strip()
            body = text[len(_xssi) :].strip() if text.startswith(_xssi) else text
            if resp.status_code == 200 and body.startswith("{"):
                data = json.loads(body)
                name = (
                    data.get("payload", {}).get("user", {}).get("name")
                    or data.get("payload", {}).get("user", {}).get("username")
                    or "unknown"
                )
                print(f"[OK] Authenticated as: {name}")
            elif resp.status_code in (301, 302):
                print("[!] Cookies invalid or expired -- server redirected (not logged in)")
            else:
                print(f"[!] Unexpected response: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[X] Request failed: {e}")

        # 2. Try reading bookmarks page
        bookmark_urls = self._fetch_bookmark_urls_from_html(cookie_string, limit=5)
        if bookmark_urls:
            print(f"[OK] Bookmarks page: found {len(bookmark_urls)} URLs")
            for u in bookmark_urls:
                print(f"   - {u}")
        else:
            print("[!] Bookmarks page returned 0 URLs -- cookies may be expired")

        print("----------------------------------------------------\n")

    def fetch_reading_list(self, cookie_string: str, max_articles: int = 20) -> list[Article]:
        """
        Fetch your private Medium bookmarks using session cookies.

        HOW TO GET YOUR COOKIE STRING (two options):

        Option A — Network tab (easiest, gets all cookies at once):
          1. Open medium.com in Chrome/Edge, make sure you're logged in
          2. Press F12 → Network tab
          3. Navigate to any page or just reload medium.com
          4. Click any request to medium.com in the list
          5. Scroll down in the Headers pane to "Request Headers"
          6. Find the line: cookie: sid=xxx; uid=xxx; ...
          7. Copy the ENTIRE value after "cookie: "
          8. Pass that whole string here

        Option B — Application tab (find individual cookies):
          1. Press F12 → Application tab
          2. Left sidebar: Storage → Cookies → https://medium.com
          3. Copy both "sid" and "uid" values
          4. Pass as:  "sid=VALUE; uid=VALUE"

        You need at minimum: sid=... and uid=...
        Store as MEDIUM_COOKIES in .env to avoid passing on command line.

        Args:
            cookie_string: Full cookie header value or "sid=X; uid=Y" string.
            max_articles:  Maximum articles to fetch and save.
        """
        # Try the JSON API first — this is what Medium's React app uses internally
        # Primary: scrape the bookmarks page HTML for article links
        article_urls = self._fetch_bookmark_urls_from_html(cookie_string, limit=max_articles)

        # Fallback: try the legacy JSON API (may be deprecated)
        if not article_urls:
            log.debug("HTML scrape returned 0 URLs, trying JSON API fallback...")
            article_urls = self._fetch_bookmark_urls_from_api(cookie_string, limit=max_articles)

        if not article_urls:
            log.error(
                "No bookmarks found.\n"
                "  Your cookies are likely expired or invalid.\n"
                "  Run --check-cookies to diagnose.\n"
                "  To refresh: DevTools -> Application -> Cookies -> medium.com\n"
                "  Copy 'sid' and 'uid' values, update MEDIUM_COOKIES in .env"
            )
            return []

        log.info("Found %d bookmark URLs", len(article_urls))
        articles = []
        for article_url in article_urls[:max_articles]:
            try:
                article = self._fetch_article_by_url(article_url)
                if article:
                    self._save(article)
                    articles.append(article)
                    log.info("  [OK] Saved: %s", article.title[:80])
                    time.sleep(REQUEST_DELAY)
            except Exception as e:
                log.warning("  [FAIL] '%s': %s", article_url, e)

        log.info(
            "Done -- saved %d/%d articles from reading list",
            len(articles),
            len(article_urls[:max_articles]),
        )
        return articles

    def fetch_article_by_url(self, url: str) -> Article | None:
        """
        Fetch a single Medium article by URL, save it, and return it.

        Useful for adding a specific article to your knowledge base without
        needing the full RSS flow.
        """
        article = self._fetch_article_by_url(url)
        if article:
            self._save(article)
            log.info("Saved: %s", article.title[:80])
        return article

    def _fetch_article_by_url(self, url: str) -> Article | None:
        """Fetch and parse a single Medium article page. Returns None on failure."""
        # Strip query params so we get the canonical article page
        clean_url = url.split("?")[0].rstrip("/")
        try:
            resp = self._get(clean_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            log.warning("Could not fetch %s: %s", clean_url, e)
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # --- Title ---
        title = ""
        og = soup.find("meta", property="og:title")
        if og:
            title = og.get("content", "").strip()
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "Untitled"

        # --- Author ---
        author = ""
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta:
            author = author_meta.get("content", "").strip()

        # --- Published date ---
        published = ""
        pub_meta = soup.find("meta", property="article:published_time")
        if pub_meta:
            published = pub_meta.get("content", "")

        # --- Tags ---
        tags = [t.get("content", "") for t in soup.find_all("meta", property="article:tag")]

        # --- Full content ---
        # Primary: extract from Medium's embedded Apollo GraphQL state.
        # The Apollo cache JSON (window.__APOLLO_STATE__) contains the COMPLETE
        # article body as Paragraph objects — even for member-only stories when
        # the request is authenticated (valid sid + cf_clearance cookies).
        content_md = self._extract_from_apollo_state(resp.text)

        if not content_md:
            # Fallback: parse the visible HTML (works for non-paywalled articles,
            # gives at least the preview for unauthenticated member-only pages).
            content_html = ""
            article_elem = soup.find("article")
            if article_elem:
                content_html = str(article_elem)
            else:
                main = soup.find("main") or soup.find("div", attrs={"role": "main"})
                if main:
                    content_html = str(main)
            content_md = self._html_to_markdown(content_html) if content_html else ""

        summary = content_md[:500] if content_md else ""

        return Article(
            title=title,
            url=clean_url,
            author=author,
            published=published,
            tags=tags,
            summary=summary,
            content_md=content_md,
            source_feed="direct",
        )

    def _fetch_bookmark_urls_from_html(self, cookie_string: str, limit: int = 100) -> list[str]:
        """
        Fallback: fetch bookmark URLs by scraping the reading-list HTML page.

        Navigates to https://medium.com/me/list/reading-list with session cookies
        and extracts article URLs from the rendered page.  More resilient than
        tracking Medium's internal JSON/GraphQL API changes.
        """
        if cookie_string:
            self._cookie_string = cookie_string
        try:
            resp = self._get("https://medium.com/me/list/reading-list", timeout=15)
            if resp.status_code in (301, 302, 401, 403):
                log.debug("Reading-list page returned HTTP %d", resp.status_code)
                return []
            if resp.status_code != 200:
                log.debug("Reading-list page returned HTTP %d", resp.status_code)
                return []
        except Exception as e:
            log.debug("Could not fetch reading-list page: %s", e)
            return []

        urls = self._extract_article_urls(resp.text)
        log.info("Reading-list HTML fallback found %d article URLs", len(urls))
        return urls[:limit]

    def _fetch_xsrf_token(self, cookie_string: str) -> str:
        """
        Fetch a valid XSRF token by visiting medium.com with session cookies.

        Medium sets the ``xsrf`` cookie on every page response.  We need its
        value in the ``X-Xsrf-Token`` header for any ``/_/api/`` call.
        """
        cookies_dict: dict[str, str] = {}
        for part in cookie_string.split(";"):
            k, _, v = part.strip().partition("=")
            if k:
                cookies_dict[k.strip()] = v.strip()

        try:
            if _CURL_AVAILABLE:
                resp = cf_requests.get(
                    "https://medium.com/",
                    headers=HEADERS,
                    cookies=cookies_dict,
                    impersonate="chrome120",
                    verify=False,
                    timeout=15,
                )
            else:
                resp = requests.get(
                    "https://medium.com/",
                    headers={**HEADERS, "Cookie": cookie_string},
                    timeout=15,
                )

            # Extract xsrf from Set-Cookie headers
            for cookie in resp.cookies:
                if cookie.name.lower() == "xsrf":
                    log.debug("Got XSRF token from medium.com response cookies")
                    return cookie.value

            # Also check raw Set-Cookie headers
            for header_val in (
                resp.headers.get_list("set-cookie")
                if hasattr(resp.headers, "get_list")
                else [resp.headers.get("set-cookie", "")]
            ):
                if "xsrf=" in header_val:
                    for part in header_val.split(";"):
                        k, _, v = part.strip().partition("=")
                        if k.strip().lower() == "xsrf":
                            return v.strip()

        except Exception as e:
            log.debug("Could not fetch XSRF token: %s", e)

        return ""

    def _fetch_bookmark_urls_from_api(self, cookie_string: str, limit: int = 100) -> list[str]:
        """
        Fetch bookmark URLs from Medium's internal JSON API.

        Medium's React app calls /_/api/me/bookmarks (paginated, returns JSON).
        The JSON envelope starts with ")]}while(1);</x>" as XSSI protection.
        We strip that prefix and parse the payload.

        Returns a list of article URLs, empty list on any failure.
        """
        # Extract xsrf token from cookie string, or fetch it from Medium
        xsrf_token = ""
        for part in cookie_string.split(";"):
            key, _, val = part.strip().partition("=")
            if key.strip().lower() == "xsrf":
                xsrf_token = val.strip()
                break

        if not xsrf_token:
            xsrf_token = self._fetch_xsrf_token(cookie_string)

        if not xsrf_token:
            xsrf_token = "1"  # last resort fallback

        # Build cookies dict for curl_cffi
        cookies_dict: dict[str, str] = {}
        for part in cookie_string.split(";"):
            k, _, v = part.strip().partition("=")
            if k:
                cookies_dict[k.strip()] = v.strip()

        urls: list[str] = []
        page_token: str | None = None
        page = 0

        while len(urls) < limit:
            params: dict = {"limit": min(25, limit - len(urls))}
            if page_token:
                params["to"] = page_token

            page += 1
            try:
                # Use curl_cffi with Chrome impersonation to bypass Cloudflare
                if _CURL_AVAILABLE:
                    resp = cf_requests.get(
                        "https://medium.com/_/api/me/bookmarks",
                        headers={
                            **HEADERS,
                            "Accept": "application/json",
                            "X-Xsrf-Token": xsrf_token,
                        },
                        cookies=cookies_dict,
                        params=params,
                        impersonate="chrome120",
                        verify=False,
                        timeout=15,
                    )
                else:
                    resp = requests.get(
                        "https://medium.com/_/api/me/bookmarks",
                        headers={
                            **HEADERS,
                            "Cookie": cookie_string,
                            "Accept": "application/json",
                            "X-Xsrf-Token": xsrf_token,
                        },
                        params=params,
                        timeout=15,
                    )
            except Exception as e:
                log.debug("Bookmarks API request failed (page %d): %s", page, e)
                break

            if resp.status_code in (401, 403, 404):
                log.debug(
                    "Bookmarks API returned HTTP %d (page %d) -- endpoint may be deprecated",
                    resp.status_code,
                    page,
                )
                break
            if not resp.ok:
                log.debug("Bookmarks API HTTP %d (page %d)", resp.status_code, page)
                break

            # Strip Medium's XSSI prefix before parsing JSON
            raw = resp.text
            for prefix in ("])}while(1);</x>", ")]}while(1);</x>", "])}while(1);<"):
                if raw.startswith(prefix):
                    raw = raw[len(prefix) :]
                    break

            try:
                data = json.loads(raw.strip())
            except json.JSONDecodeError as e:
                log.warning("Could not parse bookmarks JSON (page %d): %s", page, e)
                log.debug("Response body: %s", resp.text[:500])
                break

            # Extract post slugs/URLs from the payload
            # Medium's response structure: {"success": true, "payload": {"bookmarks": [...], "paging": {...}}}
            payload = data.get("payload", data)  # sometimes there's no outer "payload" key
            bookmarks = payload.get("bookmarks", [])

            if not bookmarks:
                log.debug("No bookmarks in page %d payload (keys: %s)", page, list(payload.keys()))
                break

            for b in bookmarks:
                post = b.get("post", b)
                slug = post.get("uniqueSlug") or post.get("slug", "")
                creator = (post.get("creator") or {}).get("username", "")
                if slug:
                    if creator:
                        url = f"https://medium.com/@{creator}/{slug}"
                    else:
                        url = f"https://medium.com/p/{slug}"
                    if url not in urls:
                        urls.append(url)

            # Pagination
            paging = payload.get("paging", {})
            next_page = paging.get("next", {})
            page_token = next_page.get("to") or next_page.get("pageToken")
            if not page_token or not bookmarks:
                break  # no more pages

        log.info("Bookmarks API returned %d URLs across %d page(s)", len(urls), page)
        return urls

    def _extract_article_urls(self, html: str) -> list[str]:
        """
        Extract unique Medium article URLs from arbitrary HTML.

        Uses two passes:
          1. Regex on raw HTML (catches URLs in script tags / JSON blobs).
          2. BeautifulSoup anchor tags (catches rendered links).
        """
        seen: set[str] = set()
        urls: list[str] = []

        # Pass 1 — regex over raw HTML catches URLs embedded in JSON/script
        for match in _MEDIUM_ARTICLE_RE.finditer(html):
            candidate = match.group(1).split("?")[0].rstrip("/")
            if candidate not in seen:
                seen.add(candidate)
                urls.append(candidate)

        # Pass 2 — BeautifulSoup for rendered anchor hrefs
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            if href.startswith("/"):
                href = f"https://medium.com{href}"
            # Only keep URLs that match the Medium article pattern
            if _MEDIUM_ARTICLE_RE.match(href):
                candidate = href.split("?")[0].rstrip("/")
                if candidate not in seen:
                    seen.add(candidate)
                    urls.append(candidate)

        return urls

    # ------------------------------------------------------------------
    # Core RSS processing
    # ------------------------------------------------------------------

    def _process_feed(self, feed_url: str, max_articles: int) -> list[Article]:
        entries = self._parse_feed(feed_url)
        if not entries:
            log.warning("No entries found in feed: %s", feed_url)
            return []

        articles = []
        for entry in entries[:max_articles]:
            try:
                article = self._entry_to_article(entry, feed_url)
                self._save(article)
                articles.append(article)
                log.info("  [OK] Saved: %s", article.title[:80])
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                log.warning("  [FAIL] '%s': %s", entry.get("title", "?"), e)

        log.info("Done -- saved %d/%d articles", len(articles), len(entries[:max_articles]))
        return articles

    def _parse_feed(self, feed_url: str) -> list:
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo:
                log.warning("Feed parse warning: %s", feed.bozo_exception)
            return feed.entries
        except Exception as e:
            log.error("Could not parse feed %s: %s", feed_url, e)
            return []

    def _entry_to_article(self, entry, feed_url: str) -> Article:
        title = entry.get("title", "Untitled")
        url = entry.get("link", "")
        author = entry.get("author", "Unknown")
        published = entry.get("published", "")

        tags = [t.get("term", "") for t in entry.get("tags", [])]

        # Summary from feed (may contain HTML)
        raw_summary = entry.get("summary", "")
        summary = self._html_to_text(raw_summary)[:500]

        # If we have a URL and cookies, try Apollo extraction (full content)
        if url and self._cookie_string:
            try:
                apollo_article = self._fetch_article_by_url(url)
                if apollo_article and len(apollo_article.content_md) > 200:
                    # Use Apollo content but keep RSS metadata
                    apollo_article.source_feed = feed_url
                    if not apollo_article.tags and tags:
                        apollo_article.tags = tags
                    return apollo_article
            except Exception as exc:
                log.debug("Apollo extraction failed for RSS entry %s: %s", url, exc)

        # Fallback: convert RSS HTML content
        content_html = ""
        for content in entry.get("content", []):
            if content.get("type") == "text/html":
                content_html = content.get("value", "")
                break

        if not content_html:
            content_html = raw_summary

        content_md = self._html_to_markdown(content_html)

        return Article(
            title=title,
            url=url,
            author=author,
            published=published,
            tags=tags,
            summary=summary,
            content_md=content_md,
            source_feed=feed_url,
        )

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _save(self, article: Article) -> None:
        slug = article.slug

        # Markdown file
        md_path = self._raw_dir / f"{slug}.md"
        md_content = (
            f"# {article.title}\n\n"
            f"**Author:** {article.author}  \n"
            f"**Published:** {article.published}  \n"
            f"**URL:** {article.url}  \n"
            f"**Tags:** {', '.join(article.tags)}  \n\n"
            f"---\n\n"
            f"## Summary\n\n{article.summary}\n\n"
            f"---\n\n"
            f"## Full Content\n\n{article.content_md}\n"
        )
        md_path.write_text(md_content, encoding="utf-8")

        # JSON metadata sidecar
        meta_path = self._meta_dir / f"{slug}.json"
        meta = asdict(article)
        meta.pop("content_md")  # keep meta small
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # HTML helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _html_to_text(html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator=" ", strip=True)

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """
        Best-effort HTML -> Markdown conversion without heavy dependencies.
        Handles headings, paragraphs, code blocks, bold/italic, links, lists.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove <code> elements that are direct children of <pre> so we
        # don't double-process them. We keep the <pre> and move <code>'s
        # text into it.
        for pre in soup.find_all("pre"):
            code_child = pre.find("code", recursive=False)
            if code_child:
                # Preserve the code text inside <pre>, remove the <code> wrapper
                code_child.unwrap()

        lines: list[str] = []
        seen: set[int] = set()  # track element ids to avoid duplicates

        for elem in soup.find_all(
            ["h1", "h2", "h3", "h4", "p", "pre", "ul", "ol", "li", "blockquote"]
        ):
            eid = id(elem)
            if eid in seen:
                continue
            seen.add(eid)

            # Skip elements that are children of a <pre> we already processed
            if elem.find_parent("pre"):
                continue

            tag = elem.name

            if tag == "pre":
                # Preserve newlines in code blocks
                text = elem.get_text(separator="\n").strip()
                if not text:
                    continue
                lang = MediumScraper._detect_code_language(text, elem)
                lines.append(f"```{lang}\n{text}\n```")
            elif tag.startswith("h"):
                text = elem.get_text(strip=True)
                if text:
                    level = tag[1]
                    lines.append(f"{'#' * int(level)} {text}")
            elif tag == "blockquote":
                text = elem.get_text(strip=True)
                if text:
                    lines.append(f"> {text}")
            elif tag == "li":
                text = elem.get_text(strip=True)
                if text:
                    lines.append(f"- {text}")
            elif tag == "p":
                text = elem.get_text(strip=True)
                if not text:
                    continue
                # Inline <code> inside paragraphs → wrap in backticks
                for code in elem.find_all("code"):
                    code_text = code.get_text()
                    code.replace_with(f"`{code_text}`")
                text = elem.get_text(strip=True)
                lines.append(text)
            else:
                text = elem.get_text(strip=True)
                if text:
                    lines.append(text)

        if not lines:
            # fallback: just strip all HTML
            lines = [soup.get_text(separator="\n", strip=True)]

        return "\n\n".join(lines)

    @staticmethod
    def _detect_code_language(text: str, elem=None) -> str:
        """
        Detect programming language from code content and/or HTML element classes.

        Checks the element's class attributes first (Medium and other platforms
        often use class="language-python" or class="lang-bash"), then falls
        back to content-based heuristics.
        """
        # Check element class attributes for language hints
        if elem is not None:
            classes = elem.get("class", []) or []
            # Also check child <code> classes
            code_child = elem.find("code") if hasattr(elem, "find") else None
            if code_child:
                classes = classes + (code_child.get("class", []) or [])
            for cls in classes:
                if isinstance(cls, str):
                    # Patterns: "language-python", "lang-python", "python"
                    m = re.match(r"(?:language-|lang-)?([\w+#]+)", cls)
                    if m:
                        lang = m.group(1).lower()
                        if lang in _CODE_LANG_MAP:
                            return _CODE_LANG_MAP[lang]

        return _guess_language_from_content(text)

    @staticmethod
    def _extract_from_apollo_state(html: str) -> str:
        """
        Extract full article body from Medium's embedded Apollo GraphQL state.

        Medium server-side-renders each page with a ``window.__APOLLO_STATE__``
        JSON blob in a <script> tag.  The blob is a normalised Apollo cache:
        every Post, Paragraph and Markup is stored as a top-level key such as
        ``"Post:abc123"`` / ``"Paragraph:p1"`` / ``"Markup:m1"``.

        When the HTTP request carries valid member cookies (sid + cf_clearance)
        the injected state contains the *complete* article body — including
        member-only paragraphs that are not present in the visible HTML.

        Returns Markdown, or an empty string if extraction fails.
        """
        soup = BeautifulSoup(html, "lxml")
        state: dict = {}

        for script in soup.find_all("script"):
            text = script.string or ""
            if "__APOLLO_STATE__" not in text:
                continue
            m = re.search(r"window\.__APOLLO_STATE__\s*=\s*", text)
            if not m:
                continue
            try:
                decoder = json.JSONDecoder()
                state, _ = decoder.raw_decode(text, m.end())
                break
            except json.JSONDecodeError:
                continue

        if not state:
            return ""

        # ── Dereference Apollo cache references ───────────────────────────────
        def resolve(obj: object) -> object:
            if isinstance(obj, dict) and "__ref" in obj:
                return state.get(obj["__ref"], {})
            return obj

        # ── Find the Post entry with the most paragraphs ──────────────────────
        best_paragraphs: list = []
        for value in state.values():
            if not isinstance(value, dict) or value.get("__typename") != "Post":
                continue
            content = resolve(value.get("content") or {})
            body = resolve(content.get("bodyModel") or {})
            paras = body.get("paragraphs") or []
            if len(paras) > len(best_paragraphs):
                best_paragraphs = paras

        if not best_paragraphs:
            return ""

        # ── Resolve paragraph and markup references ───────────────────────────
        resolved_paras: list[dict] = []
        for p in best_paragraphs:
            p = resolve(p)
            if not isinstance(p, dict):
                continue
            markups = [resolve(m) for m in (p.get("markups") or []) if isinstance(resolve(m), dict)]
            resolved_paras.append({**p, "markups": markups})

        return MediumScraper._paragraphs_to_markdown(resolved_paras)

    @staticmethod
    def _paragraphs_to_markdown(paragraphs: list[dict]) -> str:
        """Convert a list of Medium ContentKit Paragraph dicts to Markdown."""
        # Medium paragraph type → Markdown line prefix
        prefix_map: dict[str, str] = {
            "P": "",
            "H1": "# ",
            "H2": "## ",
            "H3": "### ",
            "H4": "#### ",
            "H5": "##### ",
            "H6": "###### ",
            "ULI": "- ",
            "OLI": "1. ",
            "BQ": "> ",
        }

        lines: list[str] = []
        for para in paragraphs:
            ptype = (para.get("type") or "P").upper()
            text = para.get("text") or ""
            markups = para.get("markups") or []

            if ptype == "PRE":
                lang = (para.get("codeBlockMetadata") or {}).get("lang") or ""
                if not lang:
                    lang = _guess_language_from_content(text)
                lines.append(f"```{lang}\n{text}\n```")
                continue

            if ptype == "IMG":
                meta = para.get("metadata") or {}
                img_id = meta.get("id") or meta.get("mediaId") or ""
                alt = text or "image"
                if img_id:
                    lines.append(f"![{alt}](https://miro.medium.com/v2/resize:fit:700/{img_id})")
                elif text:
                    lines.append(f"*{text}*")
                continue

            if ptype in ("MIXTAPE_EMBED", "IFRAME", "UNKNOWN"):
                if text:
                    lines.append(text)
                continue

            formatted = MediumScraper._apply_markups(text, markups)
            prefix = prefix_map.get(ptype, "")
            if formatted or prefix:
                lines.append(f"{prefix}{formatted}")

        return "\n\n".join(lines)

    @staticmethod
    def _apply_markups(text: str, markups: list[dict]) -> str:
        """
        Apply Medium inline markups (bold, italic, inline-code, link) to text.

        Medium stores markups as character-range annotations:
            {"type": "STRONG", "start": 0, "end": 5}
        We insert Markdown delimiters at the exact byte positions.

        Opening delimiters are processed outer-first (widest span), so closing
        delimiters are naturally innermost-first — correct Markdown nesting.
        """
        if not text or not markups:
            return text

        # Sort: outer spans first (longest), break ties by earlier start
        sorted_m = sorted(
            markups,
            key=lambda m: (m.get("start", 0), -(m.get("end", 0) - m.get("start", 0))),
        )

        opens: dict[int, list[str]] = {}
        closes: dict[int, list[str]] = {}

        for m in sorted_m:
            start = max(0, m.get("start", 0))
            end = min(len(text), m.get("end", 0))
            if end <= start:
                continue
            mtype = (m.get("type") or "").upper()

            if mtype == "STRONG":
                opens.setdefault(start, []).append("**")
                closes.setdefault(end, []).insert(0, "**")
            elif mtype == "EM":
                opens.setdefault(start, []).append("*")
                closes.setdefault(end, []).insert(0, "*")
            elif mtype == "CODE":
                opens.setdefault(start, []).append("`")
                closes.setdefault(end, []).insert(0, "`")
            elif mtype == "A":
                href = m.get("href") or ""
                if href.startswith("http"):
                    opens.setdefault(start, []).append("[")
                    closes.setdefault(end, []).insert(0, f"]({href})")

        # Rebuild: closes emit BEFORE the char at their position (end is exclusive)
        parts: list[str] = []
        for i, ch in enumerate(text):
            for ins in closes.get(i, []):
                parts.append(ins)
            for ins in opens.get(i, []):
                parts.append(ins)
            parts.append(ch)
        for ins in closes.get(len(text), []):
            parts.append(ins)

        return "".join(parts)


def _print_digest(max_articles: int = 10, output_dir: Path | None = None) -> None:
    """Print a digest of the most recent articles in the knowledge base."""
    kb_dir = Path(output_dir) if output_dir else RAW_DIR
    md_files = sorted(kb_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    total = len(md_files)
    shown = md_files[:max_articles]

    print(f"Knowledge base: {kb_dir}")
    print(f"Total articles: {total}")
    print()

    for f in shown:
        lines = f.read_text(encoding="utf-8", errors="replace").split("\n")
        title_line = next((line for line in lines if line.startswith("# ")), f.stem)
        title = title_line.lstrip("# ").strip() if title_line.startswith("# ") else title_line

        # Get first non-empty body lines as preview
        body_start = next((idx for idx, line in enumerate(lines) if line.startswith("# ")), 0) + 1
        body_lines = [line for line in lines[body_start:] if line.strip()]
        preview = "\n".join(body_lines[:6])[:400]

        print(f"--- {title} ---")
        print(preview)
        print()


def main():
    from dotenv import load_dotenv

    from utils.logger_config import setup_logging

    load_dotenv()  # loads .env so MEDIUM_COOKIES etc. are available via os.environ
    setup_logging("INFO")

    parser = argparse.ArgumentParser(description="Fetch Medium articles into the knowledge base")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tag",
        metavar="TAG",
        action="append",
        dest="tags",
        help="Medium tag (repeatable, e.g. --tag ai-agents --tag llm)",
    )
    group.add_argument(
        "--user", metavar="USERNAME", help="Medium username (e.g. towardsdatascience)"
    )
    group.add_argument(
        "--url",
        metavar="RSS_URL",
        help="Any Medium RSS feed URL (user, tag, publication, or public list)",
    )
    group.add_argument(
        "--list",
        metavar="LIST_URL",
        action="append",
        dest="lists",
        help=(
            "Fetch articles from a Medium named list (repeatable for multiple lists). "
            "Example: --list https://medium.com/@username/list/coding-abc123 "
            "--list https://medium.com/@username/list/other-xyz456"
        ),
    )
    group.add_argument(
        "--export",
        metavar="DIR",
        help=(
            "Process an unzipped Medium data export folder. "
            "Get your export at https://medium.com/me/export — "
            "Medium emails you a .zip. Unzip it and pass the folder here."
        ),
    )
    group.add_argument(
        "--export-zip",
        metavar="ZIP_FILE",
        help=(
            "Process a Medium data export .zip directly (no need to unzip). "
            "Get your export at https://medium.com/me/export."
        ),
    )
    group.add_argument(
        "--bookmarks",
        action="store_true",
        help=(
            "Fetch your private reading list (general bookmarks) using --cookies. "
            "Requires --cookies to also be passed."
        ),
    )
    group.add_argument(
        "--reading-list",
        metavar="SID_COOKIE",
        help=argparse.SUPPRESS,  # backwards compat: old --reading-list VALUE style
    )
    group.add_argument(
        "--check-cookies",
        metavar="COOKIE_STRING",
        help=(
            "Diagnostic: verify your Medium cookies and print what they can access. "
            "Does NOT save anything — just checks and reports."
        ),
    )
    group.add_argument(
        "--article",
        metavar="URL",
        help="Fetch a single article by full URL and add it to the knowledge base",
    )
    group.add_argument(
        "--summarize",
        action="store_true",
        help="Print a digest of the most recent articles in the knowledge base (no scraping)",
    )
    group.add_argument(
        "--discover",
        action="store_true",
        help=(
            "Discover trending/hot articles from Medium tags. "
            "Use with --discover-tags and --keywords to filter. "
            "Shows a ranked report. Add --scrape-top N to auto-scrape the top N."
        ),
    )
    # --cookies is NOT in the exclusive group — it can combine with --list or --bookmarks
    parser.add_argument(
        "--cookies",
        metavar="COOKIE_STRING",
        default="",
        help=(
            'Medium session cookies. Only sid and uid are needed: "sid=...; uid=...". '
            "Get them once from DevTools → Application → Cookies → medium.com. "
            "Or set MEDIUM_COOKIES=sid=...; uid=... in .env (then --cookies is never needed again)."
        ),
    )
    parser.add_argument(
        "--max", type=int, default=10, help="Maximum articles to fetch (default 10)"
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        default="",
        help="Save articles to this directory instead of the default knowledge base",
    )
    parser.add_argument(
        "--dated",
        action="store_true",
        help="Save into a YYYY-MM-DD subfolder (e.g. data/.../2026-03-25/)",
    )
    # Discovery options (used with --discover)
    parser.add_argument(
        "--discover-tags",
        metavar="TAGS",
        dest="discover_tags",
        help=(
            "Tags to search for trending articles (comma-separated). "
            "Example: --discover --discover-tags ai-agents,llm,automation"
        ),
    )
    parser.add_argument(
        "--keywords",
        metavar="KEYWORDS",
        dest="keywords",
        help=(
            "Keywords to score article relevance (comma-separated). "
            "Higher score if keyword appears in title/tags/summary. "
            "Example: --keywords agent,Claude,trading"
        ),
    )
    parser.add_argument(
        "--scrape-top",
        metavar="N",
        type=int,
        default=0,
        help="After discovery, automatically scrape the top N articles (default: 0 = report only)",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Fetch each discovered article's page to get clap/response counts (slower)",
    )
    parser.add_argument(
        "--curate",
        action="store_true",
        help=(
            "Use an LLM (Claude/GPT) to evaluate and select the best articles. "
            "Requires ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
        ),
    )
    parser.add_argument(
        "--curate-top",
        metavar="N",
        type=int,
        default=10,
        help="How many articles the LLM should select (default: 10)",
    )

    args = parser.parse_args()

    import os

    cookie_str = args.cookies or os.environ.get("MEDIUM_COOKIES", "")

    output_dir = args.output or None
    scraper = MediumScraper(cookie_string=cookie_str, output_dir=output_dir, dated=args.dated)

    if args.tags:
        for tag in args.tags:
            scraper.fetch_tag(tag, max_articles=args.max)
    elif args.user:
        scraper.fetch_user(args.user, max_articles=args.max)
    elif args.lists:
        for list_url in args.lists:
            scraper.fetch_list(list_url, max_articles=args.max, cookie_string=cookie_str)
    elif args.url:
        scraper.fetch_url(args.url, max_articles=args.max)
    elif args.export:
        scraper.fetch_from_export(args.export, max_articles=args.max)
    elif args.export_zip:
        scraper.fetch_from_export_zip(args.export_zip, max_articles=args.max)
    elif args.check_cookies:
        scraper.check_cookies(args.check_cookies)
        return  # don't print KB summary for diagnostic-only run
    elif args.bookmarks:
        if not cookie_str:
            print("ERROR: --bookmarks requires --cookies or MEDIUM_COOKIES in .env")
            return
        scraper.fetch_reading_list(cookie_string=cookie_str, max_articles=args.max)
    elif args.reading_list:
        # Old backwards-compat: --reading-list VALUE (cookie value as direct argument)
        scraper.fetch_reading_list(cookie_string=args.reading_list, max_articles=args.max)
    elif args.article:
        scraper.fetch_article_by_url(args.article)
    elif args.summarize:
        _print_digest(args.max, output_dir=output_dir)
        return
    elif args.discover:
        default_tags = [
            "ai-agents",
            "llm",
            "artificial-intelligence",
            "automation",
            "machine-learning",
            "python",
            "software-engineering",
        ]
        # Parse comma-separated tags/keywords
        discover_tags = (
            [t.strip() for t in args.discover_tags.split(",") if t.strip()]
            if args.discover_tags
            else default_tags
        )
        keywords = (
            [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else None
        )

        discoverer = TrendDiscoverer(cookie_string=cookie_str)

        candidates = discoverer.discover_from_tags(
            tags=discover_tags,
            keywords=keywords,
            max_per_tag=args.max,
        )

        if args.enrich and candidates:
            print(f"\nEnriching top {min(20, len(candidates))} articles with engagement data...")
            candidates = discoverer.enrich_with_metadata(candidates, max_enrich=20)

        # LLM-based curation: let an agent pick the best articles
        if args.curate and candidates:
            from knowledge.article_curator import ArticleCurator

            try:
                curator = ArticleCurator()
                curated = curator.curate(
                    candidates,
                    keywords=keywords or [],
                    top_n=args.curate_top,
                )
                if curated:
                    candidates = curated
                    print(f"\n  LLM selected {len(curated)} articles")
            except OSError as e:
                print(f"\n  Curation skipped (no API key): {e}")
                print("  Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env to enable curation.")

        discoverer.print_report(candidates, top_n=args.max)

        # Auto-scrape top N if requested
        if args.scrape_top > 0 and candidates:
            top = candidates[: args.scrape_top]
            print(f"\nScraping top {len(top)} articles...")
            for c in top:
                try:
                    article = scraper.fetch_article_by_url(c.url)
                    if article:
                        print(f"  [OK] {article.title[:70]}")
                    time.sleep(REQUEST_DELAY)
                except Exception as e:
                    print(f"  [FAIL] {c.url}: {e}")
            kb = scraper._raw_dir
            saved = sorted(kb.glob("*.md"))
            print(f"\nKnowledge base: {kb}")
            print(f"Total articles saved: {len(saved)}")

        return

    # List what we have
    kb = scraper._raw_dir
    saved = sorted(kb.glob("*.md"))
    print(f"\nKnowledge base: {kb}")
    print(f"Total articles saved: {len(saved)}")
    for p in saved[-5:]:
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
