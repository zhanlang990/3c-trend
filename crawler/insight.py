"""JD procurement insight generator.

Rule-based: load insight_rules.json, identify brand, match rule, fill template.
Generates three fields per item:
  - info_brief: 信息摘要 (key facts condensed)
  - opportunity_insight: 机会洞察 (market opportunity angle)
  - procurement_insight: 操盘建议 (actionable procurement advice)
"""
import json
import os


class InsightEngine:
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

        # enforce length cap (80 chars)
        if len(insight) > 80:
            insight = insight[:77] + "..."
        return insight

    def generate_info_brief(self, item):
        """Generate info_brief (信息摘要) - condensed key facts from title + summary."""
        title = item.get("title", "")
        summary = item.get("summary", "")
        sources = item.get("sources", [])
        if isinstance(sources, list):
            src_text = "、".join(sources[:3])
        else:
            src_text = item.get("source", "")

        # Build brief: core fact + source attribution
        brief_parts = []
        if title:
            brief_parts.append(title.rstrip("。？！"))
        if src_text:
            brief_parts.append(src_text + "报道")
        if len(brief_parts) == 0:
            return ""
        brief = "，".join(brief_parts) + "。"
        # Cap at 100 chars
        if len(brief) > 100:
            brief = brief[:97] + "..."
        return brief

    def generate_opportunity_insight(self, item):
        """Generate opportunity_insight (机会洞察) - market opportunity angle."""
        title = item.get("title", "")
        summary = item.get("summary", "")
        text = (title + " " + summary).lower()
        brand = self.detect_brand(title + " " + summary)

        # Pattern-based opportunity templates
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

        # Cap at 80 chars
        if len(opportunity) > 80:
            opportunity = opportunity[:77] + "..."
        return opportunity


def enrich(items, rules_path=None):
    """Mutate-in-place: add info_brief, opportunity_insight, procurement_insight fields."""
    eng = InsightEngine(rules_path)
    for it in items:
        it["info_brief"] = eng.generate_info_brief(it)
        it["opportunity_insight"] = eng.generate_opportunity_insight(it)
        it["procurement_insight"] = eng.generate_procurement(it)
    return items