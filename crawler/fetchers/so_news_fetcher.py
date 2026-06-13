"""360 News (news.so.com) search fetcher.

Extracts articles from 360 News search results.
360 News uses server-rendered HTML with h3 > a structure for article titles,
providing stable and reliable results via plain HTTP.

Key features:
- Parses h3 > a links (primary article results)
- Extracts dates from surrounding text context
- Consistent 6+ results per keyword search
- No rate limiting observed in normal use
"""
import re
import logging
import time
from fetchers.base import BaseFetcher
from parser import parse_date, clean_text, absolute_url

log = logging.getLogger("fetcher")

# 360 News search URL template
SO_NEWS_URL = "https://news.so.com/ns?q={keyword}"

# Pattern to match h3 article links (primary results)
_H3_LINK_RE = re.compile(
    r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Also catch general a tags for supplementary results
_A_TAG = re.compile(
    r'<a\s+[^>]*href\s*=\s*"([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Filter out junk
_JUNK_URLS = {"login", "logout", "register", "javascript:", "#comment", "mailto:", "/about", "/help"}
_JUNK_TITLES = {"首页", "登录", "注册", "更多", "下一页", "上一页", "全部", "新闻", "视频", "图片"}


class SoNewsFetcher(BaseFetcher):
    """Fetch news articles via 360 News search (news.so.com).

    360 News aggregates articles from multiple media sources.
    Results are rendered server-side in h3 >a tags.
    """

    def fetch(self, keywords):
        items = []
        seen_urls = set()

        for kw in keywords[:5]:
            url = self.build_search_url(SO_NEWS_URL, kw)
            try:
                html = self.http_get(url, referer="https://www.so.com/")
            except Exception as e:
                log.debug("[360news] http_get failed for %s: %s", kw, e)
                continue

            # Delay between keyword searches
            time.sleep(1.0)

            # Parse h3 links first (primary results, most relevant)
            for m in _H3_LINK_RE.finditer(html):
                href, inner = m.group(1), m.group(2)
                title = clean_text(inner)

                if not title or len(title) < 8 or len(title) > 80:
                    continue
                if title in _JUNK_TITLES:
                    continue

                full = absolute_url(href, url)
                if not full.startswith("http"):
                    continue
                if full in seen_urls:
                    continue
                if any(x in full for x in _JUNK_URLS):
                    continue

                # Try to find date from context
                ctx_start = max(0, m.start() - 80)
                ctx_end = min(len(html), m.end() + 500)
                ctx = html[ctx_start:ctx_end]
                ctx_text = clean_text(ctx)
                dt = parse_date(ctx_text)

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