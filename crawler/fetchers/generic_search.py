"""Generic search-engine fetcher.

Strategy: query a search engine URL with the keyword, parse all <a> tags,
treat each anchor with reasonable text length as a candidate news item.
Date is parsed from surrounding text via parser.parse_date.

This is intentionally tolerant: many search portals frequently change DOM,
but anchors with absolute URLs and date-like neighbors remain stable signals.
"""
import re
import os
import sys

CURDIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(CURDIR)
sys.path.insert(0, PARENT)

from fetchers.base import BaseFetcher
from parser import parse_date, clean_text, absolute_url


_A_TAG = re.compile(
    r'<a\s+[^>]*href\s*=\s*"([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


# Default search URL templates for known source ids
# Updated 2026-06: Bing search no longer returns results via HTTP (JS-rendered).
# Switched to Sogou News search which reliably returns article titles via plain HTTP.
DEFAULT_SEARCH_URLS = {
    # --- Primary search engines (verified working 2026-06) ---
    "sogou-news": "https://news.sogou.com/news?query={keyword}",
    "sogou-weixin": "https://weixin.sogou.com/weixin?type=2&query={keyword}",
    # --- Direct search (verified working with dates 2026-06) ---
    "ifanr": "https://www.ifanr.com/?s={keyword}",
    # --- All other sources: use Sogou News search (plain keyword) ---
    # Sogou News aggregates articles from all major media, so domain-specific
    # search is unnecessary. Each source will contribute via Sogou's index.
    "bing": "https://news.sogou.com/news?query={keyword}",
    "bing-news": "https://news.sogou.com/news?query={keyword}",
    "ithome": "https://news.sogou.com/news?query={keyword}",
    "zol": "https://news.sogou.com/news?query={keyword}",
    "pconline": "https://news.sogou.com/news?query={keyword}",
    "cnbeta": "https://news.sogou.com/news?query={keyword}",
    "geekpark": "https://news.sogou.com/news?query={keyword}",
    "sohu": "https://news.sogou.com/news?query={keyword}",
    "sina": "https://news.sogou.com/news?query={keyword}",
   "36kr": "https://news.sogou.com/news?query={keyword}",
    "sspai": "https://news.sogou.com/news?query={keyword}",
    "chongdantou": "https://news.sogou.com/news?query={keyword}",
    "notebookcheck": "https://news.sogou.com/news?query={keyword}",
    "feng": "https://news.sogou.com/news?query={keyword}",
    "zealer": "https://news.sogou.com/news?query={keyword}",
    "leikeji": "https://news.sogou.com/news?query={keyword}",
    "theverge": "https://news.sogou.com/news?query={keyword}",
    "engadget": "https://news.sogou.com/news?query={keyword}",
    "cnet": "https://news.sogou.com/news?query={keyword}",
    "tomshardware": "https://news.sogou.com/news?query={keyword}",
    "androidauthority": "https://news.sogou.com/news?query={keyword}",
    "cls": "https://news.sogou.com/news?query={keyword}",
    "sina-finance": "https://news.sogou.com/news?query={keyword}",
    "netease": "https://news.sogou.com/news?query={keyword}",
    "netease-tech": "https://news.sogou.com/news?query={keyword}",
    "jiemian": "https://news.sogou.com/news?query={keyword}",
    "huxiu": "https://news.sogou.com/news?query={keyword}",
    "tmtpost": "https://news.sogou.com/news?query={keyword}",
    "pingwest": "https://news.sogou.com/news?query={keyword}",
    "dsb": "https://news.sogou.com/news?query={keyword}",
    "ebrun": "https://news.sogou.com/news?query={keyword}",
    "txws": "https://news.sogou.com/news?query={keyword}",
    "leiphone": "https://news.sogou.com/news?query={keyword}",
    "qbitai": "https://news.sogou.com/news?query={keyword}",
    "jiqizhixin": "https://news.sogou.com/news?query={keyword}",
    "aiera": "https://news.sogou.com/news?query={keyword}",
    "mydrivers": "https://news.sogou.com/news?query={keyword}",
    "pcpop": "https://news.sogou.com/news?query={keyword}",
    "dgtle": "https://news.sogou.com/news?query={keyword}",
    "laoyaoba": "https://news.sogou.com/news?query={keyword}",
    "semiinsights": "https://news.sogou.com/news?query={keyword}",
    "xinzhidx": "https://news.sogou.com/news?query={keyword}",
    "eefocus": "https://news.sogou.com/news?query={keyword}",
    "elecfans": "https://news.sogou.com/news?query={keyword}",
    "21ic": "https://news.sogou.com/news?query={keyword}",
    "eeworld": "https://news.sogou.com/news?query={keyword}",
    "eet-china": "https://news.sogou.com/news?query={keyword}",
    "ednchina": "https://news.sogou.com/news?query={keyword}",
    "ofweek-ee": "https://news.sogou.com/news?query={keyword}",
    "c114": "https://news.sogou.com/news?query={keyword}",
    "icsmart": "https://news.sogou.com/news?query={keyword}",
    "sina-tech": "https://news.sogou.com/news?query={keyword}",
    "sohu-tech": "https://news.sogou.com/news?query={keyword}",
    "arstechnica": "https://news.sogou.com/news?query={keyword}",
    "techcrunch": "https://news.sogou.com/news?query={keyword}",
    "wired": "https://news.sogou.com/news?query={keyword}",
    "verge-ai": "https://news.sogou.com/news?query={keyword}",
    "pchouse": "https://news.sogou.com/news?query={keyword}",
    "china": "https://news.sogou.com/news?query={keyword}",
    "aipu": "https://news.sogou.com/news?query={keyword}",
}


class GenericSearchFetcher(BaseFetcher):
    """Hits a search url for each keyword, parses anchor list heuristically."""

    def fetch(self, keywords):
        items = []
        seen_urls = set()
        tpl = self.config.get("search_url") or self.config.get("list_url")
        if not tpl:
            # Fallback to default search URL for known source ids
            src_id = self.config.get("id", "")
            tpl = DEFAULT_SEARCH_URLS.get(src_id, "")
        if not tpl:
            return items

        # Extract source domain for relevance filtering when using Bing search
        source_domain = ""
        src_url = self.config.get("url", "")
        if src_url:
            try:
                from urllib.parse import urlparse
                source_domain = urlparse(src_url).netloc.replace("www.", "")
            except Exception:
                pass

        url_targets = []
        if "{keyword}" in tpl:
            for kw in keywords[:5]:  # search up to 5 keywords
                url_targets.append((self.build_search_url(tpl, kw), kw))
        else:
            url_targets.append((tpl, ""))

        for target, search_kw in url_targets:
            try:
                html = self.http_get(target)
            except Exception:
                continue
            # Extra delay between keyword searches to avoid rate limiting
            import time
            time.sleep(1.0)
            # find anchors
            for m in _A_TAG.finditer(html):
                href, inner = m.group(1), m.group(2)
                title = clean_text(inner)
                if not title or len(title) < 8 or len(title) > 80:
                    continue
                full = absolute_url(href, target)
                # only keep http(s) urls; skip navigation/anchor/javascript
                if not full.startswith("http"):
                    continue
                if full in seen_urls:
                    continue
                # filter out junk (login, subscribe, etc.)
                if any(x in full for x in [
                    "login", "logout", "register", "javascript:",
                    "#comment", "mailto:", "/about", "/help",
                ]):
                    continue
                # heuristic: skip menu items by checking title content
                if title in ("首页", "登录", "注册", "更多", "下一页", "上一页"):
                    continue

                # try to find a date close to this anchor (within 500 chars)
                # Bing search results often have dates in the snippet text
                # further from the anchor tag
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
                    "source": self.config.get("name", ""),
                    "_publish_dt": dt,
                    "_search_keyword": search_kw,
                })

        # When using Bing keyword search, prioritize URLs from the source domain
        # and filter out irrelevant results (baidu baike, zhihu, etc.)
        if source_domain and "bing.com" in tpl:
            domain_items = [i for i in items if source_domain in i["url"]]
            other_items = [i for i in items if source_domain not in i["url"]]
            # Keep domain-matched items first, then a few relevant others with dates
            other_with_date = [i for i in other_items if i.get("_publish_dt") is not None]
            other_no_date = [i for i in other_items if i.get("_publish_dt") is None]
            items = domain_items + other_with_date[:3] + other_no_date[:2]

        return items


# Concrete per-source fetchers live in their own modules under
# crawler/fetchers/, and are aggregated in crawler/fetchers/__init__.py via
# FETCHER_CLASSES for use by run.py.