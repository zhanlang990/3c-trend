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
# Priority: specific fetcher > RSS > HTML list > GenericSearch (Bing)
FETCHER_CLASSES = {
    "sina": SinaFetcher,
    "netease": NeteaseFetcher,
    "china": ChinaFetcher,
    "pchouse": PchouseFetcher,
    "sohu": SohuFetcher,
    "aipu": BrandFetcher,
    "sogou-weixin": SogouWeixinFetcher,
    # Sources with RSS feeds — use RSSFetcher for higher quality data
    "ithome": RSSFetcher,
    "36kr": RSSFetcher,
    "leiphone": RSSFetcher,
    "qbitai": RSSFetcher,
    "ifanr": RSSFetcher,
    "tmtpost": RSSFetcher,
    "theverge": RSSFetcher,
    "engadget": RSSFetcher,
    "huxiu": RSSFetcher,
    "geekpark": RSSFetcher,
    "pingwest": RSSFetcher,
    "cnbeta": RSSFetcher,
    "mydrivers": RSSFetcher,
    "dgtle": RSSFetcher,
    "leikeji": RSSFetcher,
    "arstechnica": RSSFetcher,
    "techcrunch": RSSFetcher,
    "wired": RSSFetcher,
    "cnet": RSSFetcher,
    "tomshardware": RSSFetcher,
    # Remaining sources use GenericSearchFetcher (Bing search fallback)
    "zol": GenericSearchFetcher,
    "pconline": GenericSearchFetcher,
    "chinairn": GenericSearchFetcher,
    "cls": GenericSearchFetcher,
    "sina-finance": GenericSearchFetcher,
}