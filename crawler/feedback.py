"""Feedback analysis module.

Reads user feedback (good/bad) from data/feedback.json, computes
boost/penalty weights per source and keyword so the crawler can
prioritise well-received content and deprioritise irrelevant items.

Feedback JSON format (written by the frontend):
{
  "https://example.com/news1": "good",
  "https://example.com/news2": "bad",
  ...
}

The crawler cross-references feedback URLs with news.json items
to map feedback back to sources and keywords.
"""
import json
import os
from collections import defaultdict

CURDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CURDIR)
FEEDBACK_PATH = os.path.join(ROOT, "data", "feedback.json")
NEWS_PATH = os.path.join(ROOT, "data", "news.json")

# Weight multipliers
GOOD_BOOST = 1.5   # good feedback → 1.5× weight
BAD_PENALTY = 0.5  # bad feedback → 0.5× weight
DEFAULT_WEIGHT = 1.0


def load_feedback(path=None):
    """Load feedback.json, return dict {url: "good"|"bad"}."""
    path = path or FEEDBACK_PATH
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def load_current_news(path=None):
    """Load news.json, return items list."""
    path = path or NEWS_PATH
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except (json.JSONDecodeError, IOError):
        return []


def analyse(feedback=None, items=None):
    """Analyse feedback against news items.

    Returns dict:
    {
      "source_weights": {source_name: weight, ...},
      "keyword_weights": {keyword: weight, ...},
      "stats": {"good_count": N, "bad_count": N, "total_feedback": N}
    }
    """
    if feedback is None:
        feedback = load_feedback()
    if items is None:
        items = load_current_news()

    # Build URL → item lookup
    url_map = {}
    for it in items:
        url = it.get("url", "")
        if url:
            url_map[url] = it

    # Accumulate scores per source and keyword
    source_scores = defaultdict(lambda: {"good": 0, "bad": 0})
    keyword_scores = defaultdict(lambda: {"good": 0, "bad": 0})

    good_count = 0
    bad_count = 0

    for url, vote in feedback.items():
        if vote not in ("good", "bad"):
            continue
        if vote == "good":
            good_count += 1
        else:
            bad_count += 1

        item = url_map.get(url)
        if not item:
            continue

        # Map to sources
        sources = item.get("sources", [])
        if not sources and item.get("source"):
            sources = [item["source"]]
        for src in sources:
            source_scores[src][vote] += 1

        # Map to keywords
        for kw in item.get("matched_keywords", []):
            keyword_scores[kw][vote] += 1

    # Convert counts to weights
    source_weights = {}
    for src, counts in source_scores.items():
        w = DEFAULT_WEIGHT
        if counts["good"] > counts["bad"]:
            w = GOOD_BOOST
        elif counts["bad"] > counts["good"]:
            w = BAD_PENALTY
        source_weights[src] = w

    keyword_weights = {}
    for kw, counts in keyword_scores.items():
        w = DEFAULT_WEIGHT
        if counts["good"] > counts["bad"]:
            w = GOOD_BOOST
        elif counts["bad"] > counts["good"]:
            w = BAD_PENALTY
        keyword_weights[kw] = w

    return {
        "source_weights": source_weights,
        "keyword_weights": keyword_weights,
        "stats": {
            "good_count": good_count,
            "bad_count": bad_count,
            "total_feedback": good_count + bad_count,
        },
    }


def apply_source_weights(sources_config, source_weights):
    """Reorder sources_config: boost good sources to front, push bad to back.

    sources_config: list of source dicts from sources.json
    source_weights: dict from analyse()
    Returns: reordered copy of sources_config
    """
    def sort_key(sconf):
        name = sconf.get("name", "")
        w = source_weights.get(name, DEFAULT_WEIGHT)
        # Higher weight first; within same weight, keep original order
        return -w

    return sorted(sources_config, key=sort_key)


def apply_keyword_weights(keywords, keyword_weights):
    """Boost good keywords to front, demote bad ones.

    keywords: list of keyword strings from sources.json
    keyword_weights: dict from analyse()
    Returns: reordered copy of keywords
    """
    def sort_key(kw):
        w = keyword_weights.get(kw, DEFAULT_WEIGHT)
        return -w

    return sorted(keywords, key=sort_key)