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
    """Keep items whose title or summary contains at least one keyword.
    Adds 'matched_keywords' field to each kept item."""
    kept = []
    for it in items:
        haystack = (it.get("title", "") + " " + it.get("summary", ""))
        hit = match_keywords(haystack, keywords)
        if hit:
            it["matched_keywords"] = hit
            kept.append(it)
    return kept


def filter_recent(items, days=7):
    """Keep items whose publish_date is within the last `days` days.
    Items without parseable date are dropped (per spec)."""
    cutoff = datetime.now() - timedelta(days=days)
    kept = []
    for it in items:
        dt = it.get("_publish_dt")
        if not isinstance(dt, datetime):
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
        clean = {
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "source": it.get("source", ""),
            "publish_date": dt.strftime("%Y-%m-%d") if dt else "",
            "summary": it.get("summary", ""),
            "matched_keywords": it.get("matched_keywords", []),
            "procurement_insight": it.get("procurement_insight", ""),
        }
        out.append(clean)
    return out