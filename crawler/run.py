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
from fetchers.generic_search import GenericSearchFetcher, DEFAULT_SEARCH_URLS
from fetchers.rss_fetcher import RSSFetcher
from fetchers.html_list_fetcher import HtmlListFetcher
from fetchers.sogou_weixin_fetcher import SogouWeixinFetcher
from filter import (
    filter_by_keywords, filter_recent, dedup_by_title,
    sort_by_date_desc, finalize_items, filter_quality,
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


# Load sources.json for enriched source configs (rss_url, list_url, fetch_mode etc.)
SOURCES_PATH = os.path.join(ROOT, "data", "sources.json")


def _load_source_lookup():
    """Load sources.json and return a dict keyed by source id."""
    if not os.path.exists(SOURCES_PATH):
        return {}
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["id"]: s for s in data.get("sources", []) if "id" in s}


def _enrich_source_config(sconf, source_lookup):
    """Merge category source config with full source config from sources.json.
    This adds rss_url, list_url, fetch_mode, url, group, focus etc.
    """
    src_id = sconf.get("id", "")
    if src_id in source_lookup:
        # sources.json config takes precedence for fetch-related fields,
        # but category-level overrides (enabled, type) are preserved
        full = {**source_lookup[src_id], **sconf}
        return full
    return sconf


# Extra financial / IPO sources to supplement admin-configured sources
FINANCIAL_SOURCE_TEMPLATES = [
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

    # Load enriched source configs from sources.json
    source_lookup = _load_source_lookup()
    log.info("Loaded %d source configs from sources.json", len(source_lookup))

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
        direct_fetch_ok = False  # Track if direct fetch got enough data
        for sconf_raw in sources:
            # Enrich source config with rss_url, list_url, fetch_mode from sources.json
            sconf = _enrich_source_config(sconf_raw, source_lookup)
            # --- Fetcher selection: RSS > HTML list > specific > Bing search ---
            # 1. If source has rss_url, use RSSFetcher (highest quality)
            # 2. If source has fetch_mode=html or list_url, use HtmlListFetcher
            # 3. If source has a specific fetcher in FETCHER_CLASSES, use it
            # 4. Fallback to GenericSearchFetcher (Bing search)
            src_id = sconf.get("id", "")
            fetch_mode = sconf.get("fetch_mode", "")
            rss_url = sconf.get("rss_url", "")
            list_url = sconf.get("list_url", "")

            if rss_url or fetch_mode == "rss":
                fetcher = RSSFetcher(sconf)
            elif list_url or fetch_mode == "html":
                fetcher = HtmlListFetcher(sconf)
            elif src_id in FETCHER_CLASSES:
                fetcher = FETCHER_CLASSES[src_id](sconf)
            else:
                fetcher = GenericSearchFetcher(sconf)

            items = fetcher.safe_fetch(keywords)
            if items:
                source_names_with_data.add(sconf["name"])
                # Mark items from admin-configured sources as priority
                if sconf_raw in cat.get("sources", []):
                    for it in items:
                        it["_priority"] = True
                # For RSS/HTML fetchers, items are pre-filtered by source domain
                # so they are keyword-relevant — mark them to bypass keyword filter
                if isinstance(fetcher, (RSSFetcher, HtmlListFetcher)):
                    for it in items:
                        it.setdefault("matched_keywords", [keywords[0]] if keywords else [])
                # For Bing site: search sources, the search URL already contains
                # the keyword, so results are pre-filtered by relevance.
                # Mark them as keyword-matched to bypass filter_by_keywords.
                search_url = sconf.get("search_url", "") or DEFAULT_SEARCH_URLS.get(src_id, "")
                if "site%" in search_url or "site:" in search_url:
                    for it in items:
                        it["matched_keywords"] = [keywords[0]] if keywords else []
            cat_items.extend(items)

        # --- Fallback: if direct fetch got too few items, supplement with Bing + Sogou Weixin ---
        # Direct fetchers (RSS/HTML/specific) produce higher quality data.
        # If they didn't produce enough, add search engine results as supplement.
        MIN_DIRECT_ITEMS = 5
        direct_items_count = len(cat_items)
        if direct_items_count < MIN_DIRECT_ITEMS:
            log.info("Category '%s': only %d items from direct fetch, adding search fallback",
                     cat_name, direct_items_count)

            # Fallback 1: Bing search with category keywords
            bing_conf = {"id": "bing", "name": "必应搜索", "type": "search",
                         "search_url": "https://cn.bing.com/search?q={keyword}"}
            bing_fetcher = GenericSearchFetcher(bing_conf)
            bing_items = bing_fetcher.safe_fetch(keywords)
            if bing_items:
                source_names_with_data.add("必应搜索")
                for it in bing_items:
                    it["_fallback"] = "bing"
                cat_items.extend(bing_items)
                log.info("Category '%s': added %d items from Bing fallback", cat_name, len(bing_items))

            # Fallback 2: Sogou WeChat search with category keywords
            sogou_conf = {"id": "sogou-weixin", "name": "搜狗微信", "type": "search"}
            sogou_fetcher = SogouWeixinFetcher(sogou_conf)
            sogou_items = sogou_fetcher.safe_fetch(keywords)
            if sogou_items:
                source_names_with_data.add("搜狗微信")
                for it in sogou_items:
                    it["_fallback"] = "sogou-weixin"
                cat_items.extend(sogou_items)
                log.info("Category '%s': added %d items from Sogou Weixin fallback", cat_name, len(sogou_items))

        log.info("Category '%s': %d raw items", cat_name, len(cat_items))

        # Pipeline for this category (with stage-by-stage diagnostics)
        n_raw = len(cat_items)
        cat_items = filter_by_keywords(cat_items, keywords)
        n_kw = len(cat_items)
        cat_items = filter_quality(cat_items)
        n_qual = len(cat_items)
        cat_items_recent = filter_recent(cat_items, days=7)
        # Fallback: if too few recent items (< 10), supplement with keyword-matched
        # items that have no date (they are still relevant, just undated)
        MIN_ITEMS_THRESHOLD = 10
        n_recent = len(cat_items_recent)
        if len(cat_items_recent) >= MIN_ITEMS_THRESHOLD:
            # Enough recent items — use them exclusively
            cat_items = cat_items_recent
        else:
            # Too few recent items — supplement with keyword-matched undated items
            kw_matched_undated = [
                it for it in cat_items
                if it.get("matched_keywords") and not it.get("_publish_dt")
            ]
            # Assign today's date to undated items so they can be displayed
            for it in kw_matched_undated:
                it["_publish_dt"] = datetime.now()
            # Merge: recent items first, then undated keyword-matched items
            seen_urls = {it.get("url") for it in cat_items_recent}
            supplement = [it for it in kw_matched_undated if it.get("url") not in seen_urls]
            cat_items = cat_items_recent + supplement
            if n_recent < MIN_ITEMS_THRESHOLD:
                log.warning("Category '%s': only %d recent items, supplemented with %d keyword-matched undated items",
                           cat_name, n_recent, len(supplement))
        cat_items = dedup_by_title(cat_items)
        n_dedup = len(cat_items)
        log.info("Category '%s' pipeline: raw=%d → keywords=%d → quality=%d → recent=%d → dedup=%d",
                 cat_name, n_raw, n_kw, n_qual, n_recent, n_dedup)

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

    # NOTE: No global dedup across categories — each category is already
    # deduplicated internally.  The same news may legitimately belong to
    # multiple categories (e.g. "AI手机" and "折叠屏手机"), so we keep them.
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