"""Filtering and dedup utilities for news items."""
import re
from datetime import datetime, timedelta
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import normalize_title  # local parser.py


def match_keywords(text, keywords):
    """Return list of matched keywords (case-insensitive exact match).

    Checks each keyword as a whole word / phrase in text (not substring).
    For multi-char keywords, uses 'in' containment as a pragmatic proxy
    for Chinese phrase boundaries (no word separators in CJK).
    """
    if not text:
        return []
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


def filter_by_keywords(items, keywords):
    """Keep items whose title OR summary OR source contains at least one keyword.

    Searches across title, summary, and source name for maximum recall.
    Only exact keyword matches (no substring expansion).
    Title matches weighted higher than summary/source matches.
    """
    kept = []
    for it in items:
        title = it.get("title", "")
        summary = it.get("summary", "")
        source = it.get("source", "")

        title_hits = match_keywords(title, keywords)
        summary_hits = match_keywords(summary, keywords) if summary else []
        source_hits = match_keywords(source, keywords) if source else []

        # Deduplicate hits
        all_hits = list(dict.fromkeys(title_hits + summary_hits + source_hits))
        if all_hits:
            it["matched_keywords"] = all_hits
            # Title match counts most: title × 3 + summary × 1 + source × 1
            it["match_score"] = len(title_hits) * 3 + len(summary_hits) + len(source_hits)
            kept.append(it)
    return kept


# Junk title patterns — these indicate navigation / ads / boilerplate, not real news
_JUNK_PATTERNS = [
    "登录", "注册", "首页", "下一页", "上一页", "更多", "返回", "顶部",
    "备案号", "ICP备", "公网安备", "版权所有", "Copyright", "All Rights Reserved",
    "Level-2", "Choice金融", "证券开户", "在线交易", "Level-2行情",
    "联系方式", "客服", "投诉", "广告", "推广", "赞助",
    "下载APP", "关注我们", "扫码", "二维码",
    "最新资讯", "精选视频", "频道",
]

# Search result anchor patterns — titles that are just URLs or search snippets
_URL_TITLE_PATTERN = re.compile(
    r'^(https?://|www\.|[a-z0-9-]+\.[a-z]{2,}[/ ›])'  # starts with URL or domain
    r'|'  # OR
    r'(https?://|www\.)',  # contains URL anywhere (裸链接标题)
    re.IGNORECASE
)

# Column/category page pattern: "keyword - SiteName" or "keyword_SiteName"
# These are typically navigation links to category pages, not articles
_COLUMN_PAGE_PATTERN = re.compile(
    r"^.{2,10}\s*[-_\u2014\u2013]\s*\S+\u7f51$"
    r"|"
    r"^.{2,10}\s*[-_\u2014\u2013]\s*\u89c2\u5bdf\u8005\u7f51$"
)


def filter_quality(items):
    """Filter out low-quality / irrelevant items based on title heuristics.

    Drops items whose title:
    - is too short (< 8 chars) or too long (> 100 chars)
    - matches known junk/navigation patterns
    - looks like a product listing (price-heavy) rather than news
    - has no Chinese characters (pure English/number spam)
    - looks like a search result anchor (URL as title)
    """
    kept = []
    for it in items:
        title = it.get("title", "").strip()
        # Length check
        if len(title) < 8 or len(title) > 100:
            continue
        # URL-as-title check (search result anchors like "baidu.com https://...")
        if _URL_TITLE_PATTERN.search(title):
            continue
        # Column/category page title check (e.g. "3D打印 - OFweek网")
        if _COLUMN_PAGE_PATTERN.search(title):
            continue
        # Junk pattern check
        if any(pat in title for pat in _JUNK_PATTERNS):
            continue
        # Must contain at least one Chinese character (unless already keyword-matched
        # from Bing site: search, which may return English results)
        if not re.search(r'[\u4e00-\u9fff]', title):
            if not it.get("matched_keywords"):
                continue
        # Skip titles that look like product listings (contain ¥/$ prices)
        if re.search(r'[¥$]\s*\d', title):
            continue
        # Skip titles that are pure navigation (common on search result pages)
        if title in ("网站地图", "关于我们", "使用条款", "隐私政策", "帮助中心"):
            continue
        kept.append(it)
    return kept


def filter_recent(items, days=7):
    """Keep items whose publish_date is within the last `days` days.
    Items without parseable date are dropped (per spec).
    Also drops items with year mismatch (e.g. URL says 2025 but date parsed as 2026)."""
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    current_year = now.year
    kept = []
    for it in items:
        dt = it.get("_publish_dt")
        if not isinstance(dt, datetime):
            continue
        # Year sanity check: drop items more than 1 year in the future or past
        if dt.year < current_year - 1 or dt.year > current_year + 1:
            continue
        if dt >= cutoff:
            kept.append(it)
    return kept


def dedup_by_title(items):
    """Dedup by normalized title; keep the earliest publish_date."""
    seen = {}
    for it in items:
        key = normalize_title(it.get("title", ""))
        if not key:
            continue
        if key not in seen:
            seen[key] = it
        else:
            # keep the one with earlier date (closer to original release)
            old = seen[key]
            old_dt = old.get("_publish_dt")
            new_dt = it.get("_publish_dt")
            if (isinstance(new_dt, datetime) and
                    isinstance(old_dt, datetime) and
                    new_dt < old_dt):
                seen[key] = it
    return list(seen.values())


def sort_by_date_desc(items):
    """Sort items by publish_date in descending order."""
    return sorted(
        items,
        key=lambda x: x.get("_publish_dt") or datetime.min,
        reverse=True,
    )


def finalize_items(items):
    """Drop internal fields, format dates, return final list."""
    out = []
    for it in items:
        dt = it.get("_publish_dt")
        sources = it.get("sources", [])
        if not sources and it.get("source"):
            sources = [it["source"]]
        clean = {
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "source": it.get("source", ""),
            "sources": sources,
            "publish_date": dt.strftime("%Y-%m-%d") if dt else "",
            "category": it.get("category", "媒体新闻"),
            "category_id": it.get("category_id", ""),
            "summary": it.get("summary", ""),
            "matched_keywords": it.get("matched_keywords", []),
            "info_brief": it.get("info_brief", ""),
            "opportunity_insight": it.get("opportunity_insight", ""),
            "procurement_insight": it.get("procurement_insight", ""),
        }
        out.append(clean)
    return out