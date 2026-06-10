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


class GenericSearchFetcher(BaseFetcher):
    """Hits a search url for each keyword, parses anchor list heuristically."""

    def fetch(self, keywords):
        items = []
        seen_urls = set()
        tpl = self.config.get("search_url") or self.config.get("list_url")
        if not tpl:
            return items

        url_targets = []
        if "{keyword}" in tpl:
            for kw in keywords[:3]:  # cap keywords to avoid heavy traffic
                url_targets.append(self.build_search_url(tpl, kw))
        else:
            url_targets.append(tpl)

        for target in url_targets:
            try:
                html = self.http_get(target)
            except Exception:
                continue
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

                # try to find a date close to this anchor (within 200 chars)
                ctx_start = max(0, m.start() - 80)
                ctx_end = min(len(html), m.end() + 200)
                ctx = html[ctx_start:ctx_end]
                ctx_text = clean_text(ctx)
                dt = parse_date(ctx_text)

                seen_urls.add(full)
                items.append({
                    "title": title,
                    "url": full,
                    "summary": "",
                    "_publish_dt": dt,
                })
        return items


# Concrete per-source fetchers live in their own modules under
# crawler/fetchers/, and are aggregated in crawler/fetchers/__init__.py via
# FETCHER_CLASSES for use by run.py.