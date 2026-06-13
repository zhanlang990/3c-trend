"""fetchers package: aggregate concrete fetcher classes for run.py."""
from fetchers.sina_fetcher import SinaFetcher
from fetchers.netease_fetcher import NeteaseFetcher
from fetchers.china_fetcher import ChinaFetcher
from fetchers.pchouse_fetcher import PchouseFetcher
from fetchers.sohu_fetcher import SohuFetcher
from fetchers.brand_fetcher import BrandFetcher
from fetchers.generic_search import GenericSearchFetcher
from fetchers.sogou_weixin_fetcher import SogouWeixinFetcher
from fetchers.rss_fetcher import RSSFetcher
from fetchers.html_list_fetcher import HtmlListFetcher


# Mapping: source id (in categories.json) -> Fetcher class
# Only sources with working RSS feeds use RSSFetcher.
# Sources without RSS use GenericSearchFetcher (Sogou news search) via fallback.
FETCHER_CLASSES = {
    "sina": SinaFetcher,
    "netease": NeteaseFetcher,
    "china": ChinaFetcher,
    "pchouse": PchouseFetcher,
    "sohu": SohuFetcher,
    "aipu": BrandFetcher,
    "sogou-weixin": SogouWeixinFetcher,
    # Sources with working official RSS feeds
    "ithome": RSSFetcher,
    "36kr": RSSFetcher,
    "leiphone": RSSFetcher,
    "ifanr": RSSFetcher,
    "tmtpost": RSSFetcher,
    "engadget": RSSFetcher,
    "cnet": RSSFetcher,
    "arstechnica": RSSFetcher,
    "techcrunch": RSSFetcher,
    "wired": RSSFetcher,
    "tomshardware": RSSFetcher,
}