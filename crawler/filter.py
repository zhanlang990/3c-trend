"""Filtering and dedup utilities for news items."""
from datetime import datetime, timedelta
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import normalize_title  # local parser.py


def match_keywords(text, keywords):
    """Return list of matched keywords (case-insensitive)."""
    if not text:
        return []
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


def filter_by_keywords(items, keywords):
    """Keep items whose TITLE contains at least one keyword.
    Adds 'matched_keywords' field to each kept item.
    Only matches against title for higher relevance — avoids false positives
    from URL parameters or generic page content.
    Items already marked with matched_keywords (e.g. from Bing site: search)
    are kept without re-checking the title."""
    kept = []
    for it in items:
        # Already keyword-matched (e.g. Bing site: search pre-marked)
        if it.get("matched_keywords"):
            kept.append(it)
            continue
        title = it.get("title", "")
        hit = match_keywords(title, keywords)
        if hit:
            it["matched_keywords"] = hit
            kept.append(it)
    return kept


# Junk title patterns — these indicate navigation / ads / boilerplate, not real news
_JUNK_PATTERNS = [
    "登录", "注册", "首页", "下一页", "上一页", "更多", "返回", "顶部",
    "备案号", "ICP备", "公网安备", "版权所有", "Copyright", "All Rights Reserved",
    "Level-2", "Choice金融", "证券开户", "在线交易", "Level-2行情",
    "联系方式", "客服", "投诉", "广告", "推广", "赞助",
    "下载APP", "关注我们", "扫码", "二维码",
]


def filter_quality(items):
    """Filter out low-quality / irrelevant items based on title heuristics.

    Drops items whose title:
    - is too short (< 8 chars) or too long (> 100 chars)
    - matches known junk/navigation patterns
    - looks like a product listing (price-heavy) rather than news
    - has no Chinese characters (pure English/number spam)
    """
    import re
    kept = []
    for it in items:
        title = it.get("title", "").strip()
        # Length check
        if len(title) < 8 or len(title) > 100:
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