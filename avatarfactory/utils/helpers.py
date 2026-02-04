"""
Utility functions for AvatarFactory.
"""

import hashlib
import re
from datetime import datetime
from typing import List


def generate_id(prefix: str = "item") -> str:
    """Generate a unique ID with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_part = hashlib.md5(timestamp.encode()).hexdigest()[:6]
    return f"{prefix}_{hash_part}"


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract keywords from text (simple implementation)"""
    # Remove common words
    stop_words = {
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "这",
        "中", "大", "为", "上", "个", "国", "到", "以", "说", "时", "要", "去", "你",
        "会", "着", "没", "看", "好", "自", "之", "能", "年", "得", "他", "而", "可",
        "也", "对", "用", "于", "学", "下", "来", "应", "其", "还", "那", "这个",
        "the", "is", "at", "which", "on", "a", "an", "and", "or", "but", "in", "with",
        "to", "for", "of", "as", "by", "from", "that", "this", "it", "are", "was",
    }

    # Simple word extraction
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]

    # Get most frequent
    from collections import Counter
    word_counts = Counter(keywords)
    return [word for word, count in word_counts.most_common(max_keywords)]


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_score(score: float) -> str:
    """Format score with color indicator"""
    if score >= 80:
        return f"🟢 {score:.0f}"
    elif score >= 60:
        return f"🟡 {score:.0f}"
    else:
        return f"🔴 {score:.0f}"
