"""Crawler entrypoint.

Pipeline:
  1) load sources.json
  2) for each enabled source, run safe_fetch()
  3) keyword filter -> recent (7d) filter -> dedup -> sort
  4) generate procurement_insight
  5) write data/news.json (fallback to sample data if empty)
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


LOG_PATH = os.path.join(CURDIR, "run.log")
DATA_PATH = os.path.join(ROOT, "data", "news.json")
SAMPLE_PATH = os.path.join(ROOT, "data", "news.sample.json")
SOURCES_PATH = os.path.join(CURDIR, "sources.json")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config():
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run():
    setup_logging()
    log = logging.getLogger("run")
    cfg = load_config()
    keywords = cfg.get("keywords", [])
    sources = [s for s in cfg.get("sources", []) if s.get("enabled", True)]
    log.info("Loaded %d sources, %d keywords", len(sources), len(keywords))

    all_items = []
    source_names_with_data = set()
    for sconf in sources:
        klass = FETCHER_CLASSES.get(sconf["id"], GenericSearchFetcher)
        fetcher = klass(sconf)
        items = fetcher.safe_fetch(keywords)
        if items:
            source_names_with_data.add(sconf["name"])
        all_items.extend(items)

    log.info("Total raw items: %d", len(all_items))

    # pipeline
    items = filter_by_keywords(all_items, keywords)
    log.info("After keyword filter: %d", len(items))
    items = filter_recent(items, days=7)
    log.info("After 7-day filter: %d", len(items))
    items = dedup_by_title(items)
    log.info("After dedup: %d", len(items))

    insight_mod.enrich(items)

    items = sort_by_date_desc(items)

    final_items = finalize_items(items)

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
        # update generated_at but keep sample items
        sample["generated_at"] = output["generated_at"]
        output = sample

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(
        "Wrote %s: %d items from %d sources",
        DATA_PATH, output.get("total", 0), output.get("source_count", 0),
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.exception("crawler fatal: %s", e)
        sys.exit(1)