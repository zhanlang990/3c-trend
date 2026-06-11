"""JD procurement insight generator.

Hybrid approach:
  - DeepSeek API (primary): Generate high-quality insights via LLM
  - Rule-based templates (fallback): When API unavailable or fails

Generates three fields per item:
  - info_brief: 信息摘要 (key facts condensed)
  - opportunity_insight: 机会洞察 (market opportunity angle)
  - procurement_insight: 操盘建议 (actionable procurement advice)

Also handles:
  - P4: Strip bare URLs from summary text
  - P8: Translate foreign-language titles/summaries to Chinese
"""
import json
import logging
import os
import re

import deepseek_client

log = logging.getLogger("insight")

# --- P4: Bare URL stripping ---
_URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)


def strip_bare_urls(text):
    """Remove bare URLs from text, replacing with empty string.

    Handles URLs in summary/description fields that are noise.
    Preserves the rest of the text around the URL.
    """
    if not text:
        return text
    cleaned = _URL_RE.sub('', text).strip()
    # Clean up artifacts: multiple spaces, dangling punctuation
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'[,，]\s*$', '', cleaned)
    cleaned = re.sub(r'^\s*[,，]\s*', '', cleaned)
    return cleaned if cleaned else text  # Keep original if URL was the entire text


def _strip_bare_urls_from_title(text):
    """Strip bare URLs from title field. Only strips if the title looks like
    a search result anchor (starts with or is dominated by a URL).
    Regular titles with URLs embedded are left as-is.
    """
    if not text:
        return text
    # Only strip if title starts with a URL or is mostly a URL
    if _URL_RE.match(text):
        cleaned = _URL_RE.sub('', text).strip()
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned if cleaned else text
    return text


# --- P8: Foreign language detection ---
def _is_foreign(text):
    """Check if text is predominantly non-Chinese (likely needs translation).

    Returns True if < 30% of characters are Chinese and text has
    significant Latin content.
    """
    if not text:
        return False
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    latin_chars = sum(1 for c in text if c.isalpha() and c.isascii())
    total = len(text)
    if total == 0:
        return False
    # If less than 30% Chinese and significant Latin content
    if chinese_chars / total < 0.3 and latin_chars / total > 0.3:
        return True
    return False


# --- Rule-based insight engine (fallback) ---
class _RuleInsightEngine:
    """Rule-based insight generator — used as fallback when DeepSeek API unavailable."""

    def __init__(self, rules_path=None):
        if rules_path is None:
            rules_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "insight_rules.json",
            )
        with open(rules_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.brand_map = self.cfg.get("brand_keywords", {})
        self.rules = self.cfg.get("rules", [])
        self.fallback = self.cfg.get(
            "fallback",
            "持续关注{brand}动态，评估其对相关价格带与流量节奏的边际影响。",
        )

    def detect_brand(self, text):
        """Return Chinese brand name, or '该品牌' if none matched."""
        if not text:
            return "该品牌"
        lower = text.lower()
        for kw, name in self.brand_map.items():
            if kw.lower() in lower:
                return name
        return "该品牌"

    def generate_info_brief(self, item):
        """Generate info_brief (信息摘要) - condensed key facts from title + summary."""
        title = item.get("title", "")
        summary = item.get("summary", "")
        sources = item.get("sources", [])
        if isinstance(sources, list):
            src_text = "、".join(sources[:3])
        else:
            src_text = item.get("source", "")

        brief_parts = []
        if title:
            brief_parts.append(title.rstrip("。？！"))
        if src_text:
            brief_parts.append(src_text + "报道")
        if len(brief_parts) == 0:
            return ""
        brief = "，".join(brief_parts) + "。"
        if len(brief) > 100:
            brief = brief[:97] + "..."
        return brief

    def generate_opportunity_insight(self, item):
        """Generate opportunity_insight (机会洞察) - market opportunity angle."""
        title = item.get("title", "")
        summary = item.get("summary", "")
        text = (title + " " + summary).lower()
        brand = self.detect_brand(title + " " + summary)

        opportunity = ""
        if any(kw in text for kw in ["增长", "上升", "新高", "爆发", "翻倍", "两位数"]):
            opportunity = "品类增长信号明确，建议提前锁定头部品牌坑位与促销资源，抢占增量窗口。"
        elif any(kw in text for kw in ["新品", "发布", "上市", "首发", "推出"]):
            opportunity = "新品周期开启，首发流量红利可期，建议跟进品牌首发节奏与种草矩阵布局。"
        elif any(kw in text for kw in ["智能", "AI", "物联网", "iot", "语音", "远程"]):
            opportunity = "智能化升级驱动品类结构变化，具备AI/IoT能力的SKU将吃到结构性红利。"
        elif any(kw in text for kw in ["补贴", "以旧换新", "国补", "消费券", "节能"]):
            opportunity = "政策补贴窗口打开，补贴合规SKU将获得流量倾斜，建议优先上架补贴目录商品。"
        elif any(kw in text for kw in ["价格", "降价", "促销", "打折", "低价"]):
            opportunity = "价格竞争加剧，关注头部品牌促销节奏，适时调整引流款与利润款组合。"
        elif any(kw in text for kw in ["出口", "海外", "全球", "国际"]):
            opportunity = "出海动向值得关注，跨境业务可借势品牌外溢效应同步推广国内中高端线。"
        elif any(kw in text for kw in ["融资", "投资", "并购", "ipo", "上市"]):
            opportunity = "资本动作释放扩张信号，建议密切关注{brand}后续渠道与营销投入节奏。".format(brand=brand)
        elif any(kw in text for kw in ["标准", "国标", "认证", "3c", "合规"]):
            opportunity = "合规门槛提升将加速行业出清，已获认证的品牌有望抢占份额真空。"
        elif any(kw in text for kw in ["跨界", "融合", "场景", "生态"]):
            opportunity = "品类边界正在被重构，跨场景组合销售与生态联动成为新增长点。"

        if not opportunity:
            opportunity = "关注{brand}在该品类的后续动态，评估其对价格带与流量节奏的边际影响。".format(brand=brand)

        if len(opportunity) > 80:
            opportunity = opportunity[:77] + "..."
        return opportunity

    def generate_procurement(self, item):
        """Generate procurement_insight (操盘建议) for one news item dict."""
        text = (item.get("title", "") + " " + item.get("summary", ""))
        brand = self.detect_brand(text)

        chosen_template = None
        for rule in self.rules:
            for kw in rule.get("match_any", []):
                if kw and kw.lower() in text.lower():
                    chosen_template = rule.get("template", "")
                    break
            if chosen_template:
                break

        template = chosen_template or self.fallback
        insight = template.replace("{brand}", brand)
        if len(insight) > 80:
            insight = insight[:77] + "..."
        return insight


# --- Main enrich function ---
def enrich(items, rules_path=None):
    """Mutate-in-place: add info_brief, opportunity_insight, procurement_insight fields.

    Also handles:
      - P4: Strip bare URLs from summary and title
      - P8: Translate foreign-language titles/summaries

    Uses DeepSeek API when configured; falls back to rule-based templates.
    """
    use_deepseek = deepseek_client.is_configured()
    if use_deepseek:
        log.info("DeepSeek API configured — using LLM for insights (batch mode)")
    else:
        log.info("DeepSeek API not configured — using rule-based templates")

    # Always init rule_engine as fallback
    rule_engine = _RuleInsightEngine(rules_path)

    translated_count = 0
    deepseek_count = 0
    fallback_count = 0

    # --- Phase 1: P4 (strip URLs) + P8 (translate) — sequential, fast ---
    for i, it in enumerate(items):
        # --- P4: Strip bare URLs from summary and title ---
        summary = it.get("summary", "")
        if summary:
            cleaned_summary = strip_bare_urls(summary)
            if cleaned_summary != summary:
                it["summary"] = cleaned_summary
        title = it.get("title", "")
        if title:
            cleaned_title = _strip_bare_urls_from_title(title)
            if cleaned_title != title:
                it["title"] = cleaned_title

        # --- P8: Translate foreign-language content ---
        if _is_foreign(title) and use_deepseek:
            translation = deepseek_client.translate_to_chinese(title, it.get("summary", ""))
            if translation:
                if translation.get("title"):
                    it["title"] = translation["title"]
                if translation.get("summary") and it.get("summary"):
                    it["summary"] = translation["summary"]
                translated_count += 1

    # --- Phase 2: Batch DeepSeek insight generation ---
    if use_deepseek:
        batch_results = deepseek_client.batch_generate_insights(items, batch_size=5)
        for i, result in enumerate(batch_results):
            if result:
                items[i]["info_brief"] = result.get("info_brief", "")
                items[i]["opportunity_insight"] = result.get("opportunity_insight", "")
                items[i]["procurement_insight"] = result.get("procurement_insight", "")
                deepseek_count += 1
            else:
                # Fallback to rule-based for this item
                items[i]["info_brief"] = rule_engine.generate_info_brief(items[i])
                items[i]["opportunity_insight"] = rule_engine.generate_opportunity_insight(items[i])
                items[i]["procurement_insight"] = rule_engine.generate_procurement(items[i])
                fallback_count += 1
    else:
        # No DeepSeek — use rule-based for all items
        for it in items:
            it["info_brief"] = rule_engine.generate_info_brief(it)
            it["opportunity_insight"] = rule_engine.generate_opportunity_insight(it)
            it["procurement_insight"] = rule_engine.generate_procurement(it)
            fallback_count += 1

    log.info("Insight enrichment: %d items total, %d via DeepSeek, %d via rules, %d translated",
             len(items), deepseek_count, fallback_count, translated_count)
    return items