"""DeepSeek API client for generating insights and translations.

Uses DeepSeek Chat API to generate:
  - info_brief: Key facts summary
  - opportunity_insight: Market opportunity analysis
  - procurement_insight: Actionable procurement advice
  - Translation: Foreign language to Chinese

Requires DEEPSEEK_API_KEY environment variable.
Falls back gracefully when API key is not configured or API call fails.
"""
import json
import logging
import os
import time
import urllib.request
import urllib.parse
import urllib.error

log = logging.getLogger("deepseek")

# DeepSeek API configuration
API_BASE = "https://api.deepseek.com"
CHAT_ENDPOINT = "/chat/completions"
MODEL = "deepseek-chat"

# Rate limiting: max requests per minute
MAX_RPM = 30
_request_timestamps = []


def _get_api_key():
    """Get DeepSeek API key from environment variable."""
    return os.environ.get("DEEPSEEK_API_KEY", "")


def _rate_limit():
    """Simple rate limiter: ensure we don't exceed MAX_RPM."""
    global _request_timestamps
    now = time.time()
    # Remove timestamps older than 60 seconds
    _request_timestamps = [t for t in _request_timestamps if now - t < 60]
    if len(_request_timestamps) >= MAX_RPM:
        # Wait until the oldest request is more than 60 seconds ago
        wait_time = 60 - (now - _request_timestamps[0]) + 0.1
        if wait_time > 0:
            log.info("Rate limit: waiting %.1f seconds", wait_time)
            time.sleep(wait_time)
    _request_timestamps.append(time.time())


def _call_api(messages, temperature=0.3, max_tokens=500):
    """Call DeepSeek Chat API.

    Args:
        messages: List of message dicts [{"role": "system/user/assistant", "content": "..."}]
        temperature: Sampling temperature (0-1)
        max_tokens: Max tokens in response

    Returns:
        Response text string, or None on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        log.debug("DeepSeek API key not configured, skipping")
        return None

    _rate_limit()

    url = API_BASE + CHAT_ENDPOINT
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            # Track token usage
            usage = result.get("usage", {})
            if usage:
                log.debug("DeepSeek tokens: prompt=%d, completion=%d, total=%d",
                          usage.get("prompt_tokens", 0),
                          usage.get("completion_tokens", 0),
                          usage.get("total_tokens", 0))
            return content.strip()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        log.warning("DeepSeek API HTTP error %d: %s", e.code, body[:200])
        return None
    except Exception as e:
        log.warning("DeepSeek API call failed: %s", e)
        return None


def generate_insights(title, summary="", category_name=""):
    """Generate info_brief, opportunity_insight, procurement_insight for a news item.

    Args:
        title: News title
        summary: News summary/description (optional)
        category_name: Category name for context (optional)

    Returns:
        Dict with info_brief, opportunity_insight, procurement_insight,
        or None if API call fails.
    """
    context = f"品类：{category_name}" if category_name else "3C数码品类"

    prompt = f"""你是京东3C数码品类的资深采销分析师。请根据以下资讯，生成三个字段的中文内容：

{context}相关资讯：
标题：{title}
{'摘要：' + summary if summary else ''}

请严格按以下JSON格式输出（不要输出其他内容）：
{{
  "info_brief": "信息摘要：核心事实浓缩，50字以内",
  "opportunity_insight": "机会洞察：从市场机会角度分析，60字以内",
  "procurement_insight": "操盘建议：可执行的采销行动建议，60字以内"
}}"""

    messages = [
        {"role": "system", "content": "你是京东3C数码品类的资深采销分析师，擅长从资讯中提炼商业洞察和采销建议。输出必须为纯JSON格式。"},
        {"role": "user", "content": prompt},
    ]

    response = _call_api(messages, temperature=0.3, max_tokens=300)
    if not response:
        return None

    # Parse JSON from response (handle markdown code blocks and various formats)
    response = response.strip()
    if response.startswith("```"):
        # Remove markdown code block markers
        lines = response.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response = "\n".join(lines).strip()

    try:
        result = json.loads(response)
        # Validate required fields
        if "info_brief" in result and "procurement_insight" in result:
            return result
        log.warning("DeepSeek response missing required fields: %s", list(result.keys()))
        return None
    except json.JSONDecodeError:
        # Try extracting JSON object with regex
        import re
        m = re.search(r'\{[^{}]*"info_brief"[^{}]*\}', response, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
                if "info_brief" in result and "procurement_insight" in result:
                    return result
            except json.JSONDecodeError:
                pass
        log.warning("DeepSeek response not valid JSON: %s", response[:200])
        return None


def translate_to_chinese(title, summary=""):
    """Translate foreign language news to Chinese.

    Args:
        title: News title (potentially in foreign language)
        summary: News summary (potentially in foreign language)

    Returns:
        Dict with translated title and summary, or None if translation not needed/failed.
    """
    # Skip if text is already mostly Chinese
    chinese_chars = sum(1 for c in title if '\u4e00' <= c <= '\u9fff')
    if chinese_chars > len(title) * 0.3:
        return None  # Already Chinese, no translation needed

    text_to_translate = title
    if summary:
        text_to_translate += f"\n\n{summary}"

    prompt = f"""请将以下外文资讯翻译成中文，保持专业术语的准确性：

{text_to_translate}

请严格按以下JSON格式输出（不要输出其他内容）：
{{
  "title": "翻译后的标题",
  "summary": "翻译后的摘要"
}}"""

    messages = [
        {"role": "system", "content": "你是专业的科技资讯翻译，擅长将英文科技新闻翻译成流畅的中文。输出必须为纯JSON格式。"},
        {"role": "user", "content": prompt},
    ]

    response = _call_api(messages, temperature=0.2, max_tokens=500)
    if not response:
        return None

    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response = "\n".join(lines).strip()

    try:
        result = json.loads(response)
        if "title" in result:
            return result
        return None
    except json.JSONDecodeError:
        # Try extracting JSON object with regex
        import re
        m = re.search(r'\{[^{}]*"title"[^{}]*\}', response, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
                if "title" in result:
                    return result
            except json.JSONDecodeError:
                pass
        log.warning("DeepSeek translate response not valid JSON: %s", response[:200])
        return None


def batch_generate_insights(items, batch_size=5):
    """Generate insights for multiple items in a single API call.

    Batches items together to reduce API calls from N to N/batch_size.
    Falls back to per-item generation if batch fails.

    Args:
        items: List of dicts with 'title', 'summary' (optional), 'category_id' (optional)
        batch_size: Number of items per API call (default 5)

    Returns:
        List of insight dicts (same order as items), None for failed items.
    """
    if not items:
        return []

    results = [None] * len(items)

    # Process in batches
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        batch_result = _batch_call(batch)
        if batch_result and len(batch_result) == len(batch):
            for j, r in enumerate(batch_result):
                results[start + j] = r
        else:
            # Batch failed — fall back to per-item
            log.info("Batch %d-%d failed, falling back to per-item", start, start + len(batch) - 1)
            for j, item in enumerate(batch):
                cat_name = _CAT_NAMES.get(item.get("category_id", ""), item.get("category_id", ""))
                results[start + j] = generate_insights(
                    title=item.get("title", ""),
                    summary=item.get("summary", ""),
                    category_name=cat_name,
                )

    return results


# Category ID to Chinese name mapping
_CAT_NAMES = {
    "3d-printing": "3D打印", "smartphone": "手机", "laptop": "笔记本",
    "tablet": "平板", "smartwatch": "智能手表", "earphone": "耳机",
    "drone": "无人机", "smart-home": "智能家居", "camera": "相机",
    "monitor": "显示器", "keyboard": "键盘", "mouse": "鼠标",
    "projector": "投影仪", "tv": "电视", "ssd": "固态硬盘",
    "router": "路由器", "printer": "打印机", "wearable": "穿戴设备",
    "robot": "机器人", "chip": "芯片",
    "uv-printing": "UV打印", "cnc": "CNC",
}


def _batch_call(items):
    """Call DeepSeek API with multiple items in one request.

    Returns list of insight dicts, or None on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    # Build batch prompt
    entries = []
    for i, item in enumerate(items):
        cat_name = _CAT_NAMES.get(item.get("category_id", ""), item.get("category_id", ""))
        title = item.get("title", "")
        summary = item.get("summary", "")
        entry = f"{i+1}. [{cat_name}] {title}"
        if summary:
            entry += f" | {summary}"
        entries.append(entry)

    items_text = "\n".join(entries)
    n = len(items)

    prompt = f"""你是京东3C数码品类的资深采销分析师。请为以下{n}条资讯分别生成三个字段。

{items_text}

请严格按以下JSON数组格式输出（不要输出其他内容）：
[
  {{
    "info_brief": "信息摘要：核心事实浓缩，50字以内",
    "opportunity_insight": "机会洞察：从市场机会角度分析，60字以内",
    "procurement_insight": "操盘建议：可执行的采销行动建议，60字以内"
  }}
]
共{n}个对象，按顺序对应上述{n}条资讯。"""

    messages = [
        {"role": "system", "content": "你是京东3C数码品类的资深采销分析师，擅长从资讯中提炼商业洞察和采销建议。输出必须为纯JSON数组格式。"},
        {"role": "user", "content": prompt},
    ]

    response = _call_api(messages, temperature=0.3, max_tokens=500 * n)
    if not response:
        return None

    # Parse JSON from response
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response = "\n".join(lines).strip()

    try:
        result = json.loads(response)
        if isinstance(result, list) and len(result) == n:
            # Validate each item has required fields
            for r in result:
                if "info_brief" not in r or "procurement_insight" not in r:
                    log.warning("Batch response item missing required fields")
                    return None
            return result
        log.warning("Batch response length mismatch: expected %d, got %d", n, len(result) if isinstance(result, list) else -1)
        return None
    except json.JSONDecodeError:
        # Try extracting JSON array with regex
        import re
        m = re.search(r'\[.*\]', response, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
                if isinstance(result, list) and len(result) == n:
                    for r in result:
                        if "info_brief" not in r or "procurement_insight" not in r:
                            return None
                    return result
            except json.JSONDecodeError:
                pass
        log.warning("Batch response not valid JSON: %s", response[:200])
        return None


def is_configured():
    """Check if DeepSeek API is configured (API key available)."""
    return bool(_get_api_key())