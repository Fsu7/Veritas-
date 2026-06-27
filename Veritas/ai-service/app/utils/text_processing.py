import re
from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> List[dict]:
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )
    if not text or not text.strip():
        return []

    text = text.strip()
    text_len = len(text)

    if text_len <= chunk_size:
        return [
            {
                "chunk_index": 0,
                "chunk_type": "title_abstract",
                "content": text,
            }
        ]

    chunks = []
    start = 0
    chunk_index = 0

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            content = text[start:]
            if content.strip():
                if chunks and len(content) < chunk_size * 0.2:
                    prev = chunks[-1]
                    prev["content"] = prev["content"] + content
                    continue

                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "chunk_type": "continuation",
                        "content": content,
                    }
                )
                chunk_index += 1
            break

        content = text[start:end]
        chunk_type = "title_abstract" if chunk_index == 0 else "continuation"
        chunks.append(
            {
                "chunk_index": chunk_index,
                "chunk_type": chunk_type,
                "content": content,
            }
        )
        chunk_index += 1
        start = end - overlap

    return chunks


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"[\x00-\x09\x0b-\x1f\x7f]", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = text.strip()

    return text


def truncate_text(text: str, max_length: int) -> str:
    if not text or len(text) <= max_length:
        return text

    search_range = text[:max_length]
    last_period = search_range.rfind(".")
    last_newline = search_range.rfind("\n")

    cut_pos = max(last_period, last_newline)
    if cut_pos <= 0:
        cut_pos = max_length
    else:
        cut_pos = cut_pos + 1

    return text[:cut_pos].strip()
