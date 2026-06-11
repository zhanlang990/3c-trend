"""RSS/Atom feed fetcher.

Directly fetches articles from a source's RSS or Atom feed.
This provides higher quality data than Bing search:
  - Accurate publish dates from feed entries
  - Clean titles without search snippet artifacts
  - Summaries/descriptions from feed content
  - Direct article URLs (no redirect/anchor issues)

Uses only stdlib (xml.etree.ElementTree) - no external dependencies.
"""
import re
import logging
from datetime import datetime
from xml.etree import ElementTree as ET

from fetchers.base import BaseFetcher
from parser import parse_date

log = logging.getLogger("fetcher")

# XML namespace prefixes commonly used in Atom feeds
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def _parse_rss_date(text):
    """Parse various RSS date formats to datetime.

    Handles RFC 822, ISO 8601, and common variants.
    """
    if not text:
        return None
    text = text.strip()

    # ISO 8601: 2026-06-15T10:30:00+08:00 or 2026-06-15T10:30:00Z
    iso_patterns = [
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:[+-]\d{2}:\d{2}|Z)?",
        r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})",
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\+\d{4}",
    ]
    for pat in iso_patterns:
        m = re.match(pat, text)
        if m:
            try:
                return datetime(
                    int(m.group(1)), int(m.group(2)), int(m.group(3)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)),
                )
            except ValueError:
                continue

    # RFC 822: Mon, 15 Jun 2026 10:30:00 +0800
    rfc_months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    m = re.match(
        r"(?:\w{3},\s*)?(\d{1,2})\s+(\w{3})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})",
        text,
    )
    if m:
        try:
            month = rfc_months.get(m.group(2))
            if month:
                return datetime(
                    int(m.group(3)), month, int(m.group(1)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)),
                )
        except ValueError:
            pass

    # Fallback to generic parser
    return parse_date(text)


def _clean_feed_html(text):
    """Remove HTML tags and entities from feed content."""
    if not text:
        return ""
    # Remove CDATA sections
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode common entities
    entities = {
        "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&ldquo;": '\u201c', "&rdquo;": '\u201d',
        "&mdash;": "\u2014", "&ndash;": "\u2013",
    }
    for k, v in entities.items():
        text = text.replace(k, v)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class RSSFetcher(BaseFetcher):
    """Fetch articles from an RSS or Atom feed URL.

    Source config should include:
      - rss_url: The RSS/Atom feed URL (required)
      - max_items: Max items to return (default 50)
    """

    def fetch(self, keywords):
        rss_url = self.config.get("rss_url", "")
        if not rss_url:
            log.warning("[%s] No rss_url configured", self.name)
            return []

        max_items = self.config.get("max_items", 50)
        items = []

        try:
            xml = self.http_get(rss_url)
        except Exception as e:
            log.warning("[%s] RSS fetch failed: %s", self.name, e)
            return []

        # Parse XML
        try:
            # Remove XML declaration to avoid encoding issues
            xml = re.sub(r'<\?xml[^>]*\?>', '', xml, count=1)
            # Remove problematic characters that break XML parsing
            xml = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml)
            root = ET.fromstring(xml)
        except ET.ParseError as e:
            log.warning("[%s] RSS parse failed: %s", self.name, e)
            # Try more aggressive cleanup: remove all non-ASCII in tag names
            try:
                xml = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|nbsp|ldquo|rdquo|mdash|ndash|#\d+);)', '&amp;', xml)
                root = ET.fromstring(xml)
            except ET.ParseError:
                log.warning("[%s] RSS parse failed even after cleanup, skipping", self.name)
                return []

        # Detect feed type and extract entries
        # RSS 2.0: <rss><channel><item>...</item></channel></rss>
        # Atom: <feed><entry>...</entry></feed>
        if root.tag == "rss" or root.tag == "channel":
            items = self._parse_rss2(root, max_items)
        elif root.tag.endswith("}feed") or root.tag == "feed":
            items = self._parse_atom(root, max_items)
        else:
            # Try both
            channel = root.find("channel")
            if channel is not None:
                items = self._parse_rss2(root, max_items)
            else:
                items = self._parse_atom(root, max_items)

        log.info("[%s] RSS parsed %d items from %s", self.name, len(items), rss_url)
        return items

    def _parse_rss2(self, root, max_items):
        """Parse RSS 2.0 format."""
        items = []
        channel = root.find("channel")
        if channel is None:
            channel = root  # root itself may be <channel>
        for item_el in channel.findall("item")[:max_items]:
            title = (item_el.findtext("title") or "").strip()
            link = (item_el.findtext("link") or "").strip()
            desc = item_el.findtext("description") or ""
            pub_date = item_el.findtext("pubDate") or ""

            if not title or not link:
                continue

            dt = _parse_rss_date(pub_date)
            summary = _clean_feed_html(desc)
            # Truncate summary to ~200 chars
            if len(summary) > 200:
                summary = summary[:197] + "..."

            items.append({
                "title": _clean_feed_html(title),
                "url": link,
                "summary": summary,
                "_publish_dt": dt,
            })
        return items

    def _parse_atom(self, root, max_items):
        """Parse Atom feed format."""
        items = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        if not entries:
            entries = root.findall("entry")
        for entry in entries[:max_items]:
            title_el = entry.find("atom:title", ns) or entry.find("title")
            link_el = entry.find("atom:link", ns) or entry.find("link")
            summary_el = entry.find("atom:summary", ns) or entry.find("summary")
            content_el = entry.find("atom:content", ns) or entry.find("content")
            updated_el = entry.find("atom:updated", ns) or entry.find("updated")
            published_el = entry.find("atom:published", ns) or entry.find("published")

            title = (title_el.text or "").strip() if title_el is not None else ""
            link = ""
            if link_el is not None:
                link = link_el.get("href", "") or link_el.text or ""

            desc = ""
            if summary_el is not None and summary_el.text:
                desc = summary_el.text
            elif content_el is not None and content_el.text:
                desc = content_el.text

            pub_text = ""
            if published_el is not None and published_el.text:
                pub_text = published_el.text
            elif updated_el is not None and updated_el.text:
                pub_text = updated_el.text

            if not title or not link:
                continue

            dt = _parse_rss_date(pub_text)
            summary = _clean_feed_html(desc)
            if len(summary) > 200:
                summary = summary[:197] + "..."

            items.append({
                "title": _clean_feed_html(title),
                "url": link,
                "summary": summary,
                "_publish_dt": dt,
            })
        return items