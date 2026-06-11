"""HTML list page fetcher.

Directly fetches articles from a source's HTML list page (homepage or news section).
Parses the HTML to extract article links, titles, and dates.

This is used for sources that don't have RSS feeds but have accessible
HTML pages with article listings.

Uses only stdlib — no external dependencies.
"""
import re
import logging
from datetime import datetime

from fetchers.base import BaseFetcher
from parser import parse_date, clean_text, absolute_url

log = logging.getLogger("fetcher")

# Common patterns for article links in HTML list pages
# Matches <a> tags with href and text content
_A_TAG = re.compile(
    r'<a\s+[^>]*href\s*=\s*"([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Patterns that indicate navigation/non-article links
_NAV_PATTERNS = [
    "login", "logout", "register", "javascript:", "#comment",
    "mailto:", "/about", "/help", "/contact", "/privacy",
    "/terms", "/search", "weixin://", "tel:",
]

# Patterns that indicate article URLs (positive signals)
_ARTICLE_URL_PATTERNS = [
    r'/\d{4}/\d{2}/\d{2}/',       # /2026/06/15/...
    r'/\d{4}-\d{2}-\d{2}',        # /2026-06-15-...
    r'/\d{6,}/',                   # /12345678.html (article ID)
    r'/article/', r'/news/', r'/post/', r'/p/',  # common article paths
    r'/detail/', r'/content/', r'/story/',
    r'\.html$', r'\.htm$',         # .html/.htm endings
]

# Title length bounds for article-like content
MIN_TITLE_LEN = 8
MAX_TITLE_LEN = 100


class HtmlListFetcher(BaseFetcher):
    """Fetch articles from a source's HTML list page.

    Source config should include:
      - url: The base URL of the source (required)
      - list_url: Specific list page URL (optional, defaults to url)
      - max_items: Max items to return (default 50)
      - article_pattern: Regex for article URL paths (optional)
    """

    def fetch(self, keywords):
        list_url = self.config.get("list_url", "") or self.config.get("url", "")
        if not list_url:
            log.warning("[%s] No list_url configured", self.name)
            return []

        max_items = self.config.get("max_items", 50)
        article_pattern = self.config.get("article_pattern", "")

        try:
            html = self.http_get(list_url)
        except Exception as e:
            log.warning("[%s] HTML list fetch failed: %s", self.name, e)
            return []

        items = []
        seen_urls = set()

        # Extract source domain for URL filtering
        from urllib.parse import urlparse
        source_domain = urlparse(list_url).netloc.replace("www.", "")

        # Find all <a> tags
        for m in _A_TAG.finditer(html):
            href, inner = m.group(1), m.group(2)
            title = clean_text(inner)

            # Basic title quality checks
            if not title or len(title) < MIN_TITLE_LEN or len(title) > MAX_TITLE_LEN:
                continue

            # Skip navigation/junk titles
            if title in ("首页", "登录", "注册", "更多", "下一页", "上一页",
                         "返回", "顶部", "联系我们", "关于我们"):
                continue

            # Build full URL
            full_url = absolute_url(href, list_url)
            if not full_url.startswith("http"):
                continue

            # Skip duplicate URLs
            if full_url in seen_urls:
                continue

            # Skip navigation/junk URLs
            if any(nav in full_url.lower() for nav in _NAV_PATTERNS):
                continue

            # URL quality filtering
            # Prefer URLs that look like articles
            is_article_url = False

            # Check custom article pattern
            if article_pattern and re.search(article_pattern, full_url):
                is_article_url = True

            # Check standard article URL patterns
            if not is_article_url:
                for pat in _ARTICLE_URL_PATTERNS:
                    if re.search(pat, full_url):
                        is_article_url = True
                        break

            # For same-domain links, be more lenient
            # (they're likely internal article links even without article patterns)
            is_same_domain = source_domain in full_url

            if not is_article_url and not is_same_domain:
                # Skip cross-domain links that don't look like articles
                continue

            # Extract date from surrounding context
            ctx_start = max(0, m.start() - 100)
            ctx_end = min(len(html), m.end() + 300)
            ctx = html[ctx_start:ctx_end]
            ctx_text = clean_text(ctx)
            dt = parse_date(ctx_text)

            seen_urls.add(full_url)
            items.append({
                "title": title,
                "url": full_url,
                "summary": "",
                "_publish_dt": dt,
            })

            if len(items) >= max_items:
                break

        log.info("[%s] HTML list parsed %d items from %s", self.name, len(items), list_url)
        return items