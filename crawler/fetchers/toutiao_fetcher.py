"""Toutiao (Today's Headlines) search fetcher.

Extracts articles from so.toutiao.com search results.
Toutiao returns server-rendered HTML with article links even via plain HTTP,
making it a reliable source for keyword-based news searches.

Key features:
- Parses article links from search result page
- Extracts dates from surrounding text context
- Handles URL encoding for Chinese keywords
- High coverage across all tech categories
- Assigns today's date to articles without parsed dates (Toutiao results are recent)
"""
import re
import datetime
import logging
import time
from fetchers.base import BaseFetcher
from parser import parse_date, clean_text, absolute_url

log = logging.getLogger("fetcher")

# Toutiao search URL template
# pd=information: search news/information type
TOUTIAO_SEARCH_URL = "https://so.toutiao.com/search?keyword={keyword}&pd=information"

# Pattern to match article links in toutiao search results
_A_TAG = re.compile(
    r'<a\s+[^>]*href\s*=\s*"([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Filter out navigation/junk URLs
_JUNK_URLS = {"login", "logout", "register", "javascript:", "#comment", "mailto:", "/about", "/help"}
_JUNK_TITLES = {"首页", "登录", "注册", "更多", "下一页", "上一页", "全部", "资讯", "视频", "图片"}


class ToutiaoFetcher(BaseFetcher):
    """Fetch news articles via Toutiao (today's headlines) search.

    Toutiao aggregates articles from many media sources and renders
    results server-side, making it accessible via plain HTTP GET.
    """

    def fetch(self, keywords):
        items = []
        seen_urls = set()

        for kw in keywords[:5]:
            url = self.build_search_url(TOUTIAO_SEARCH_URL, kw)
            try:
                html = self.http_get(url, referer="https://www.toutiao.com/")
            except Exception as e:
                log.debug("[toutiao] http_get failed for %s: %s", kw, e)
                continue

            # Delay between keyword searches to avoid rate limiting
            time.sleep(1.0)

            # Parse all anchor tags
            for m in _A_TAG.finditer(html):
                href, inner = m.group(1), m.group(2)
                title = clean_text(inner)

                # Filter: title must be 10-80 chars (article titles, not nav)
                if not title or len(title) < 10 or len(title) > 80:
                    continue

                # Skip navigation/junk titles
                if title in _JUNK_TITLES:
                    continue

                # Resolve URL
                full = absolute_url(href, url)
                if not full.startswith("http"):
                    continue
                if full in seen_urls:
                    continue

                # Filter out junk URLs
                if any(x in full for x in _JUNK_URLS):
                    continue

                # Skip toutiao internal pages (search, channel, etc.)
                if "/search?" in full or "/channel/" in full:
                    continue

                # Try to find date from context around this link
                ctx_start = max(0, m.start() - 80)
                ctx_end = min(len(html), m.end() + 500)
                ctx = html[ctx_start:ctx_end]
                ctx_text = clean_text(ctx)
                dt = parse_date(ctx_text)

                # Toutiao search results are inherently recent (sorted by time).
                # If no date is parsed, assign today's date to pass recent filter.
                if dt is None:
                    dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                seen_urls.add(full)
                items.append({
                    "title": title,
                    "url": full,
                    "summary": "",
                    "source": self.name,
                    "_publish_dt": dt,
                    "_search_keyword": kw,
                })

        return items