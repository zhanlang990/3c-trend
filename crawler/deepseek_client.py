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
        with urllib.request.urlopen(req, timeout=30) as resp:
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

    # Parse JSON from response (handle markdown code blocks)
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
        log.warning("DeepSeek translate response not valid JSON: %s", response[:200])
        return None


def is_configured():
    """Check if DeepSeek API is configured (API key available)."""
    return bool(_get_api_key())