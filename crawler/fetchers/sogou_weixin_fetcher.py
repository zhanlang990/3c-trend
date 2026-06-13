"""Sogou WeChat article search fetcher.

Extracts articles from weixin.sogou.com with proper date parsing
from JavaScript timeConvert() timestamps.

Key features:
- Parses UNIX timestamps from timeConvert() calls for accurate dates
- Filters results to recent 7 days
- Extracts account name as additional context
- Handles sogou redirect URLs
"""
import re
import datetime
import logging
from fetchers.base import BaseFetcher

log = logging.getLogger("fetcher")

# Sogou WeChat search URL template
# type=2: search articles (not accounts)
SOGOU_WEIXIN_URL = "https://weixin.sogou.com/weixin?type=2&query={keyword}"

# Regex patterns for parsing
_H3_LINK_RE = re.compile(
    r'<h3[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>\s*</h3>',
    re.DOTALL,
)
_TIMESTAMP_RE = re.compile(
    r"timeConvert\('(\d{10})'\)",
)
_ACCOUNT_RE = re.compile(
    r'<span class="all-time-y2"[^>]*>(.*?)</span>',
    re.DOTALL,
)
_SUMMARY_RE = re.compile(
    r'<p class="txt-info"[^>]*>(.*?)</p>',
    re.DOTALL,
)
_EM_RE = re.compile(r'<em[^>]*>|</em>', re.DOTALL)
_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_HTML_ENTITY_RE = re.compile(r'&(?:ldquo|rdquo|mdash|ndash|nbsp|amp|lt|gt|quot);')


def _clean_html(text):
    """Remove HTML tags, entities, and normalize whitespace."""
    text = _COMMENT_RE.sub('', text)  # remove <!-- --> comments
    text = _EM_RE.sub('', text)  # remove <em> open/close tags, keep content
    text = _HTML_TAG_RE.sub('', text)
    text = _HTML_ENTITY_RE.sub('', text)
    text = text.replace('\u3000', ' ').replace('\xa0', ' ')
    return text.strip()


def _timestamp_to_date(ts_str):
    """Convert UNIX timestamp string to date string YYYY-MM-DD."""
    try:
        dt = datetime.datetime.fromtimestamp(int(ts_str))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ""


class SogouWeixinFetcher(BaseFetcher):
    """Fetch WeChat articles via Sogou WeChat search.

    Parses the HTML result page to extract:
    - title (from <h3><a> tags)
    - url (sogou redirect link, resolved to absolute)
    - date (from timeConvert() JavaScript timestamps)
    - account name (from <span class="all-time-y2">)
    - summary (from <p class="txt-info">)
    """

    # Maximum age in days for articles
    MAX_DAYS = 7

    def fetch(self, keywords):
        items = []
        seen_urls = set()
        cutoff = datetime.datetime.now() - datetime.timedelta(days=self.MAX_DAYS)

        for kw in keywords[:5]:
            url = self.build_search_url(SOGOU_WEIXIN_URL, kw)
            try:
                html = self.http_get(url, referer="https://weixin.sogou.com/")
            except Exception as e:
                log.debug("[sogou-weixin] http_get failed for %s: %s", kw, e)
                continue

            # Extra delay between keyword searches to avoid rate limiting
            import time
            time.sleep(2.0)

            # Split HTML into result blocks by <div class="txt-box">
            blocks = re.split(r'<div class="txt-box"', html)
            if len(blocks) < 2:
                log.debug("[sogou-weixin] no txt-box blocks found for kw=%s", kw)
                continue

            for block in blocks[1:]:  # skip the part before first txt-box
                try:
                    item = self._parse_block(block, kw, url)
                except Exception as e:
                    log.debug("[sogou-weixin] parse block error: %s", e)
                    continue
                if not item or item["url"] in seen_urls:
                    continue

                # Filter by date: only keep articles within MAX_DAYS
                if item.get("_publish_dt"):
                    try:
                        if item["_publish_dt"] < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass

                seen_urls.add(item["url"])
                items.append(item)

        return items

    def _parse_block(self, block, keyword, base_url):
        """Parse a single result block into a news item dict."""
        # Extract title and URL
        title_match = _H3_LINK_RE.search(block)
        if not title_match:
            return None
        href = title_match.group(1)
        raw_title = title_match.group(2)
        title = _clean_html(raw_title)
        if not title or len(title) < 4:
            return None

        # Resolve relative URL
        if href.startswith("/"):
            href = "https://weixin.sogou.com" + href
        # Clean amp; entities in URL
        href = href.replace("&", "&")

        # Extract date from timeConvert timestamp
        date_str = ""
        dt_obj = None
        ts_match = _TIMESTAMP_RE.search(block)
        if ts_match:
            date_str = _timestamp_to_date(ts_match.group(1))
            try:
                dt_obj = datetime.datetime.fromtimestamp(int(ts_match.group(1)))
            except (ValueError, OSError):
                pass

        # Extract account name
        account = ""
        acct_match = _ACCOUNT_RE.search(block)
        if acct_match:
            account = _clean_html(acct_match.group(1))

        # Extract summary
        summary = ""
        sum_match = _SUMMARY_RE.search(block)
        if sum_match:
            summary = _clean_html(sum_match.group(1))
            if len(summary) > 200:
                summary = summary[:200] + "..."

        return {
            "title": title,
            "url": href,
            "date": date_str,
            "_publish_dt": dt_obj,
            "summary": summary,
            "source": account or self.name,
            "account": account,
            "matched_keywords": [keyword],
        }