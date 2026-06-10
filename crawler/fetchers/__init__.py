"""fetchers package: aggregate concrete fetcher classes for run.py."""
from fetchers.sina_fetcher import SinaFetcher
from fetchers.netease_fetcher import NeteaseFetcher
from fetchers.china_fetcher import ChinaFetcher
from fetchers.pchouse_fetcher import PchouseFetcher
from fetchers.sohu_fetcher import SohuFetcher
from fetchers.brand_fetcher import BrandFetcher


# Mapping: source id (in sources.json) -> Fetcher class
FETCHER_CLASSES = {
    "sina": SinaFetcher,
    "netease": NeteaseFetcher,
    "china": ChinaFetcher,
    "pchouse": PchouseFetcher,
    "sohu": SohuFetcher,
    "aipu": BrandFetcher,
}