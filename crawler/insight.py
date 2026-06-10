"""JD procurement insight generator.

Rule-based: load insight_rules.json, identify brand, match rule, fill template.
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

    def generate(self, item):
        """Generate insight string for one news item dict."""
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


def enrich(items, rules_path=None):
    """Mutate-in-place: add procurement_insight field to every item."""
    eng = InsightEngine(rules_path)
    for it in items:
        it["procurement_insight"] = eng.generate(it)
    return items