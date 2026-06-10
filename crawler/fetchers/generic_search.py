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
# Updated 2026-06: verified all sources, use bing site: fallback for JS-rendered sites
DEFAULT_SEARCH_URLS = {
    # --- General search engines (high reliability) ---
    "bing": "https://cn.bing.com/search?q={keyword}",
    "bing-news": "https://cn.bing.com/news/search?q={keyword}",
    "sogou-news": "https://news.sogou.com/news?query={keyword}",
    "sogou-weixin": "https://weixin.sogou.com/weixin?type=2&query={keyword}",
    # --- Bing site: fallback for sites without working search (verified 2026-06) ---
    "ithome": "https://cn.bing.com/search?q=site%3Aithome.com+{keyword}",
    "zol": "https://cn.bing.com/search?q=site%3Azol.com.cn+{keyword}",
    "pconline": "https://cn.bing.com/search?q=site%3Apconline.com.cn+{keyword}",
    "cnbeta": "https://cn.bing.com/search?q=site%3Acnbeta.com+{keyword}",
    "geekpark": "https://cn.bing.com/search?q=site%3Ageekpark.net+{keyword}",
    "sohu": "https://cn.bing.com/search?q=site%3Asohu.com+{keyword}",
    "sina": "https://cn.bing.com/search?q=site%3Asina.com.cn+{keyword}",
    "36kr": "https://cn.bing.com/search?q=site%3A36kr.com+{keyword}",
    "sspai": "https://cn.bing.com/search?q=site%3Asspai.com+{keyword}",
    "chongdantou": "https://cn.bing.com/search?q=site%3Achongdantou.com+{keyword}",
    "notebookcheck": "https://cn.bing.com/search?q=site%3Anotebookcheck.net+{keyword}",
    "feng": "https://cn.bing.com/search?q=site%3Afeng.com+{keyword}",
    "zealer": "https://cn.bing.com/search?q=site%3Azealer.com+{keyword}",
    # --- Direct search (verified working 2026-06) ---
    "ifanr": "https://www.ifanr.com/?s={keyword}",
    "leikeji": "https://www.leikeji.com/?s={keyword}",
    "theverge": "https://www.theverge.com/search?q={keyword}",
    "engadget": "https://www.engadget.com/search?q={keyword}",
    "cnet": "https://www.cnet.com/search?q={keyword}",
    "tomshardware": "https://www.tomshardware.com/search?searchTerm={keyword}",
    "androidauthority": "https://www.androidauthority.com/?s={keyword}",
    # --- Legacy financial sources ---
    "cls": "https://www.cls.cn/search?keyword={keyword}",
    "sina-finance": "https://search.sina.com.cn/?q={keyword}&c=news&ie=utf-8",
    "netease": "https://www.163.com/search?keyword={keyword}",
    # --- Disabled (removed eastmoney - returns nav links, chinairn - returns ads) ---
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

        url_targets = []
        if "{keyword}" in tpl:
            for kw in keywords[:3]:  # cap keywords to avoid heavy traffic
                url_targets.append((self.build_search_url(tpl, kw), kw))
        else:
            url_targets.append((tpl, ""))

        for target, search_kw in url_targets:
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
        return items


# Concrete per-source fetchers live in their own modules under
# crawler/fetchers/, and are aggregated in crawler/fetchers/__init__.py via
# FETCHER_CLASSES for use by run.py.