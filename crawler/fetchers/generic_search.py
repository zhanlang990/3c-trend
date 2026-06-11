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
    # --- Direct search (verified working with dates 2026-06) ---
    "ifanr": "https://www.ifanr.com/?s={keyword}",
    # --- Bing keyword search fallback (site: operator ignored by Bing in programmatic requests, verified 2026-06) ---
    # Using "domain+keyword" format instead of "site:domain+keyword"
    "ithome": "https://cn.bing.com/search?q=ithome.com+{keyword}",
    "zol": "https://cn.bing.com/search?q=zol.com.cn+{keyword}",
    "pconline": "https://cn.bing.com/search?q=pconline.com.cn+{keyword}",
    "cnbeta": "https://cn.bing.com/search?q=cnbeta.com+{keyword}",
    "geekpark": "https://cn.bing.com/search?q=geekpark.net+{keyword}",
    "sohu": "https://cn.bing.com/search?q=sohu.com+{keyword}",
    "sina": "https://cn.bing.com/search?q=sina.com.cn+{keyword}",
    "36kr": "https://cn.bing.com/search?q=36kr.com+{keyword}",
    "sspai": "https://cn.bing.com/search?q=sspai.com+{keyword}",
    "chongdantou": "https://cn.bing.com/search?q=chongdantou.com+{keyword}",
    "notebookcheck": "https://cn.bing.com/search?q=notebookcheck.net+{keyword}",
    "feng": "https://cn.bing.com/search?q=feng.com+{keyword}",
    "zealer": "https://cn.bing.com/search?q=zealer.com+{keyword}",
    # --- Direct-search sites without dates on search page → Bing keyword fallback ---
    # Use domain name with TLD for better precision
    "leikeji": "https://cn.bing.com/search?q=雷科技+leikeji.com+{keyword}",
    "theverge": "https://cn.bing.com/search?q=theverge.com+{keyword}",
    "engadget": "https://cn.bing.com/search?q=engadget.com+{keyword}",
    "cnet": "https://cn.bing.com/search?q=cnet.com+{keyword}",
    "tomshardware": "https://cn.bing.com/search?q=tomshardware.com+{keyword}",
    "androidauthority": "https://cn.bing.com/search?q=androidauthority.com+{keyword}",
    # --- Legacy financial sources (Bing keyword fallback) ---
    "cls": "https://cn.bing.com/search?q=cls.cn+{keyword}",
    "sina-finance": "https://cn.bing.com/search?q=sina.com.cn+finance+{keyword}",
    "netease": "https://cn.bing.com/search?q=163.com+{keyword}",
    # --- Bing keyword fallback for sources without direct search ---
    "netease-tech": "https://cn.bing.com/search?q=163.com+tech+{keyword}",
    "jiemian": "https://cn.bing.com/search?q=jiemian.com+{keyword}",
    "huxiu": "https://cn.bing.com/search?q=huxiu.com+{keyword}",
    "tmtpost": "https://cn.bing.com/search?q=tmtpost.com+{keyword}",
    "pingwest": "https://cn.bing.com/search?q=pingwest.com+{keyword}",
    "dsb": "https://cn.bing.com/search?q=dsb.cn+{keyword}",
    "ebrun": "https://cn.bing.com/search?q=ebrun.com+{keyword}",
    "txws": "https://cn.bing.com/search?q=tianxiawangshang.com+{keyword}",
    "leiphone": "https://cn.bing.com/search?q=leiphone.com+{keyword}",
    "qbitai": "https://cn.bing.com/search?q=qbitai.com+{keyword}",
    "jiqizhixin": "https://cn.bing.com/search?q=机器之心+jiqizhixin.com+{keyword}",
    "aiera": "https://cn.bing.com/search?q=aiera.com.cn+{keyword}",
    "mydrivers": "https://cn.bing.com/search?q=mydrivers.com+{keyword}",
    "pcpop": "https://cn.bing.com/search?q=pcpop.com+{keyword}",
    "dgtle": "https://cn.bing.com/search?q=dgtle.com+{keyword}",
    "laoyaoba": "https://cn.bing.com/search?q=laoyaoba.com+{keyword}",
    "semiinsights": "https://cn.bing.com/search?q=semiinsights.com+{keyword}",
    "xinzhidx": "https://cn.bing.com/search?q=xinzhidx.com+{keyword}",
    "eefocus": "https://cn.bing.com/search?q=eefocus.com+{keyword}",
    "elecfans": "https://cn.bing.com/search?q=elecfans.com+{keyword}",
    "21ic": "https://cn.bing.com/search?q=21ic.com+{keyword}",
    "eeworld": "https://cn.bing.com/search?q=eeworld.com.cn+{keyword}",
    "eet-china": "https://cn.bing.com/search?q=eet-china.com+{keyword}",
    "ednchina": "https://cn.bing.com/search?q=ednchina.com+{keyword}",
    "ofweek-ee": "https://cn.bing.com/search?q=ofweek.com+{keyword}",
    "c114": "https://cn.bing.com/search?q=c114.com.cn+{keyword}",
    "icsmart": "https://cn.bing.com/search?q=icsmart.cn+{keyword}",
    "sina-tech": "https://cn.bing.com/search?q=sina.com.cn+tech+{keyword}",
    "sohu-tech": "https://cn.bing.com/search?q=sohu.com+tech+{keyword}",
    # --- Overseas sources (Bing keyword fallback) ---
    "arstechnica": "https://cn.bing.com/search?q=arstechnica.com+{keyword}",
    "techcrunch": "https://cn.bing.com/search?q=techcrunch.com+{keyword}",
    "wired": "https://cn.bing.com/search?q=wired.com+{keyword}",
    "verge-ai": "https://cn.bing.com/search?q=theverge.com+AI+{keyword}",
    # --- Additional Bing keyword fallback ---
    "pchouse": "https://cn.bing.com/search?q=pchouse.com.cn+{keyword}",
    "china": "https://cn.bing.com/search?q=chinanews.com.cn+{keyword}",
    "aipu": "https://cn.bing.com/search?q=aipu.com+{keyword}",
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
            # Combine all keywords with OR for a single search (much faster than per-keyword)
            # e.g. "3D打印 OR 3D打印机 OR 增材制造"
            combined_kw = " OR ".join(keywords)
            url_targets.append((self.build_search_url(tpl, combined_kw), combined_kw))
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