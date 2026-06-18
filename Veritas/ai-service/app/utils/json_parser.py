"""统一的 JSON 解析工具，4 级降级策略

P2-5: 从 analyzer.py / comparer.py / reviewer.py / coordinator.py
中提取重复的 JSON 解析逻辑，统一为公共方法。
"""
import json
import re
from typing import Optional


def extract_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON，4 级降级

    Level 1: 标准 JSON 解析
    Level 2: ```json``` 代码块提取
    Level 3: ``` 代码块提取
    Level 4: 首个 {} 块提取

    Args:
        text: LLM 原始输出文本

    Returns:
        解析成功的 dict，失败返回 None
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Level 1: 标准 JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Level 2: ```json``` 代码块
    m = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Level 3: ``` 代码块
    m = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Level 4: 首个 {} 块
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None
