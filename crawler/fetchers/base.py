"""Base fetcher: shared HTTP behavior, UA pool, random delay, error isolation."""
import random
import time
import logging
import urllib.request
import urllib.parse
import gzip
import io


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 "
    "Firefox/125.0",
]


log = logging.getLogger("fetcher")


class BaseFetcher:
    """Base class for source-specific fetchers."""

    timeout = 10
    min_delay = 0.1
    max_delay = 0.3

    def __init__(self, source_config):
        """source_config: dict from sources.json -> sources[]"""
        self.id = source_config.get("id", "")
        self.name = source_config.get("name", "")
        self.config = source_config

    # ---- subclass override ----
    def fetch(self, keywords):
        """Fetch a list of news dicts for given keywords.
        Each dict must contain: title, url, summary, _publish_dt (datetime)
        plus 'source' (auto-injected by safe_fetch).
        Subclasses should override this."""
        return []

    # ---- shared helpers ----
    def safe_fetch(self, keywords):
        """Wrapper with try/except + source injection."""
        try:
            items = self.fetch(keywords) or []
        except Exception as e:
            log.warning("[%s] fetch failed: %s", self.name, e)
            return []
        for it in items:
            it.setdefault("source", self.name)
        log.info("[%s] got %d items", self.name, len(items))
        return items

    def http_get(self, url, referer=None):
        """Robust HTTP GET using urllib only (no external deps required)."""
        time.sleep(random.uniform(self.min_delay, self.max_delay))
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                # try multiple encodings
                for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
                    try:
                        return raw.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return raw.decode("utf-8", errors="ignore")
        except Exception as e:
            log.debug("[%s] http_get error %s: %s", self.name, url, e)
            raise

    @staticmethod
    def build_search_url(template, keyword):
        """Substitute {keyword} with url-encoded keyword.
        Also encodes any non-ASCII characters already in the template."""
        kw = urllib.parse.quote(keyword)
        url = template.replace("{keyword}", kw)
        # Encode non-ASCII chars in the URL (e.g. Chinese keywords in template)
        if any(ord(c) > 127 for c in url):
            # Split URL into ASCII and non-ASCII parts, encode non-ASCII
            parts = []
            for c in url:
                if ord(c) > 127:
                    parts.append(urllib.parse.quote(c))
                else:
                    parts.append(c)
            url = "".join(parts)
        return url