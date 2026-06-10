"""Crawler entrypoint.

Pipeline:
  1) load categories.json (multi-category config)
  2) load user feedback → adjust source/keyword priorities
  3) for each category, run safe_fetch() with category-specific keywords & sources
  4) keyword filter -> recent (7d) filter -> dedup -> sort
  5) generate procurement_insight
  6) write data/news.json with category_id field
"""
import json
import logging
import os
import sys
from datetime import datetime

CURDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CURDIR)
sys.path.insert(0, CURDIR)

from fetchers import FETCHER_CLASSES
from fetchers.generic_search import GenericSearchFetcher
from filter import (
    filter_by_keywords, filter_recent, dedup_by_title,
    sort_by_date_desc, finalize_items,
)
import insight as insight_mod
import feedback as feedback_mod


LOG_PATH = os.path.join(CURDIR, "run.log")
DATA_PATH = os.path.join(ROOT, "data", "news.json")
SAMPLE_PATH = os.path.join(ROOT, "data", "news.sample.json")
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_categories():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Extra financial / IPO sources to supplement admin-configured sources
FINANCIAL_SOURCE_TEMPLATES = [
    {"id": "eastmoney", "name": "东方财富", "type": "search",
     "search_url": "https://so.eastmoney.com/news/s?keyword={keyword}", "enabled": True},
    {"id": "cls", "name": "财联社", "type": "search",
     "search_url": "https://www.cls.cn/search?keyword={keyword}", "enabled": True},
    {"id": "sina-finance", "name": "新浪财经", "type": "search",
     "search_url": "https://search.sina.com.cn/?q={keyword}&c=news&ie=utf-8", "enabled": True},
]


def _get_financial_sources(cat_name, keywords):
    """Return extra financial/IPO sources for a category.
    Uses category name + top keyword as search terms."""
    return FINANCIAL_SOURCE_TEMPLATES


def run():
    setup_logging()
    log = logging.getLogger("run")

    cat_cfg = load_categories()
    categories = cat_cfg.get("categories", [])
    log.info("Loaded %d categories from categories.json", len(categories))

    # --- Apply user feedback weights ---
    fb_result = feedback_mod.analyse()
    fb_stats = fb_result.get("stats", {})
    if fb_stats.get("total_feedback", 0) > 0:
        log.info(
            "Feedback applied: %d good, %d bad → adjusting priorities",
            fb_stats.get("good_count", 0),
            fb_stats.get("bad_count", 0),
        )

    all_items = []
    source_names_with_data = set()

    for cat in categories:
        cat_id = cat.get("id", "")
        cat_name = cat.get("name", "")
        keywords = cat.get("keywords", [])
        sources = [s for s in cat.get("sources", []) if s.get("enabled", True)]

        if not keywords or not sources:
            log.info("Skipping category '%s' (no keywords or sources)", cat_name)
            continue

        log.info("=== Crawling category: %s (%s) ===", cat_name, cat_id)

        # Append extra financial report / IPO sources for each category
        extra_sources = _get_financial_sources(cat_name, keywords)
        sources = sources + extra_sources

        # Apply feedback weights per category
        if fb_stats.get("total_feedback", 0) > 0:
            sources = feedback_mod.apply_source_weights(sources, fb_result["source_weights"])
            keywords = feedback_mod.apply_keyword_weights(keywords, fb_result["keyword_weights"])

        cat_items = []
        for sconf in sources:
            klass = FETCHER_CLASSES.get(sconf["id"], GenericSearchFetcher)
            fetcher = klass(sconf)
            items = fetcher.safe_fetch(keywords)
            if items:
                source_names_with_data.add(sconf["name"])
                # Mark items from admin-configured sources as priority
                if sconf in cat.get("sources", []):
                    for it in items:
                        it["_priority"] = True
            cat_items.extend(items)

        log.info("Category '%s': %d raw items", cat_name, len(cat_items))

        # Pipeline for this category
        cat_items = filter_by_keywords(cat_items, keywords)
        cat_items = filter_recent(cat_items, days=7)
        cat_items = dedup_by_title(cat_items)

        # Tag each item with category_id
        for item in cat_items:
            item["category_id"] = cat_id
            # Assign info type if not present
            if "category" not in item:
                item["category"] = "媒体新闻"

        insight_mod.enrich(cat_items)
        # Sort: admin-source items first, then by date desc
        cat_items.sort(key=lambda x: (0 if x.get("_priority") else 1, x.get("_publish_dt") or datetime.min))
        all_items.extend(cat_items)

        log.info("Category '%s': %d items after pipeline", cat_name, len(cat_items))

    log.info("Total items across all categories: %d", len(all_items))

    # Global dedup across categories (by title)
    all_items = dedup_by_title(all_items)
    final_items = finalize_items(all_items)

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(final_items),
        "source_count": len(source_names_with_data),
        "items": final_items,
    }

    # fallback to sample if empty
    if not final_items and os.path.exists(SAMPLE_PATH):
        log.warning("No items fetched; falling back to news.sample.json")
        with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
            sample = json.load(f)
        sample["generated_at"] = output["generated_at"]
        output = sample

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Also sync news.data.js for file:// access
    sync_data_js(output)

    log.info(
        "Wrote %s: %d items from %d sources",
        DATA_PATH, output.get("total", 0), output.get("source_count", 0),
    )


def sync_data_js(data):
    """Generate news.data.js from news.json for file:// access."""
    js_path = os.path.join(ROOT, "data", "news.data.js")
    js = "/* Auto-loaded by index.html so the page works under file:// without a server. */\n"
    js += "window.__NEWS_DATA__ = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js)
    logging.getLogger("run").info("Synced %s", js_path)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.exception("crawler fatal: %s", e)
        sys.exit(1)