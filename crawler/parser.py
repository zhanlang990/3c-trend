"""Generic parsing utilities: date parsing, html text cleanup, normalization."""
import re
from datetime import datetime, timedelta


# ---------- date parsing ----------

_PATTERNS = [
    # 2026-05-12 / 2026/05/12 / 2026.05.12
    (re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})"),
     lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    # 2026年5月12日
    (re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
     lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    # 5月12日 (current year)
    (re.compile(r"(\d{1,2})月(\d{1,2})日"),
     lambda m: datetime(datetime.now().year, int(m.group(1)), int(m.group(2)))),
    # 05-12 (current year)
    (re.compile(r"^(\d{1,2})-(\d{1,2})$"),
     lambda m: datetime(datetime.now().year, int(m.group(1)), int(m.group(2)))),
]


def parse_date(text):
    """Parse date string to datetime. Returns None on failure."""
    if not text:
        return None
    text = text.strip()

    # relative time
    if "刚刚" in text or "分钟前" in text or "小时前" in text:
        return datetime.now()
    m = re.search(r"(\d+)\s*天前", text)
    if m:
        days = int(m.group(1))
        return datetime.now() - timedelta(days=days)
    m = re.search(r"昨天", text)
    if m:
        return datetime.now() - timedelta(days=1)
    m = re.search(r"前天", text)
    if m:
        return datetime.now() - timedelta(days=2)

    for pat, fn in _PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return fn(m)
            except ValueError:
                continue
    return None


# ---------- text cleanup ----------

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def clean_text(text):
    """Strip html tags and collapse whitespace."""
    if not text:
        return ""
    text = _HTML_TAG.sub(" ", text)
    entities = {
        "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&ldquo;": '"', "&rdquo;": '"'
    }
    for k, v in entities.items():
        text = text.replace(k, v)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


_PUNCT = re.compile(r"[\s\u3000\.,，。、:：;；!！?？\-—_\(\)（）\[\]【】《》\"'""'']+")


def normalize_title(title):
    """Normalize title for dedup: strip whitespace and most punctuation."""
    if not title:
        return ""
    return _PUNCT.sub("", title).lower()


def truncate(text, n=160):
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text if len(text) <= n else text[:n] + "..."


# ---------- url cleanup ----------

def absolute_url(href, base):
    """Convert relative href to absolute."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        # extract scheme + host from base
        m = re.match(r"(https?://[^/]+)", base)
        if m:
            return m.group(1) + href
    return base.rstrip("/") + "/" + href