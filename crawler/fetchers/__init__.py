"""fetchers package: aggregate concrete fetcher classes for run.py."""
from fetchers.sina_fetcher import SinaFetcher
from fetchers.netease_fetcher import NeteaseFetcher
from fetchers.china_fetcher import ChinaFetcher
from fetchers.pchouse_fetcher import PchouseFetcher
from fetchers.sohu_fetcher import SohuFetcher
from fetchers.brand_fetcher import BrandFetcher
from fetchers.generic_search import GenericSearchFetcher
from fetchers.sogou_weixin_fetcher import SogouWeixinFetcher


# Mapping: source id (in categories.json) -> Fetcher class
# Known sources use GenericSearchFetcher with DEFAULT_SEARCH_URLS fallback
FETCHER_CLASSES = {
    "sina": SinaFetcher,
    "netease": NeteaseFetcher,
    "china": ChinaFetcher,
    "pchouse": PchouseFetcher,
    "sohu": SohuFetcher,
    "aipu": BrandFetcher,
    "sogou-weixin": SogouWeixinFetcher,
    "ithome": GenericSearchFetcher,
    "zol": GenericSearchFetcher,
    "pconline": GenericSearchFetcher,
    "cnbeta": GenericSearchFetcher,
    "chinairn": GenericSearchFetcher,
    "taobao-baike": GenericSearchFetcher,
    "eastmoney": GenericSearchFetcher,
    "cls": GenericSearchFetcher,
    "sina-finance": GenericSearchFetcher,
}