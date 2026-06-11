"""citation_parser — 引用解析器

从综述文本中提取引用标注，验证引用正确性，计算引用准确率。
仅依赖标准库 re 和 typing，不依赖 Agent 框架。
"""
import re
from typing import Dict, List, Optional, Tuple


_AUTHOR_YEAR_PATTERN = re.compile(
    r"\[([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4})\]"
)

_PARENTHETICAL_PATTERN = re.compile(
    r"\(([A-Z][a-z]+(?:\s+et\s+al\.)?),\s*(\d{4})\)"
)


def extract_citations(report: str) -> List[Dict[str, str]]:
    """从综述文本中提取引用标注。

    支持两种引用格式：
    - [作者, 年份] 格式（如 [Vaswani, 2017]）
    - (作者, 年份) 格式（如 (Vaswani, 2017)）

    Args:
        report: 综述文本

    Returns:
        引用列表，每条包含 author, year, original 三个字段
    """
    if not report or not report.strip():
        return []

    citations: List[Dict[str, str]] = []
    seen: set = set()

    author_year_matches = _AUTHOR_YEAR_PATTERN.findall(report)
    for match in author_year_matches:
        parts = match.split(",")
        if len(parts) == 2:
            author = parts[0].strip()
            year = parts[1].strip()
            key = f"{author}_{year}"
            if key not in seen:
                seen.add(key)
                citations.append({
                    "author": author,
                    "year": year,
                    "original": f"[{match}]",
                })

    parenthetical_matches = _PARENTHETICAL_PATTERN.findall(report)
    for author, year in parenthetical_matches:
        key = f"{author}_{year}"
        if key not in seen:
            seen.add(key)
            citations.append({
                "author": author,
                "year": year,
                "original": f"({author}, {year})",
            })

    return citations


def validate_citations(
    extracted_citations: List[Dict[str, str]],
    paper_list: List[Dict[str, str]],
) -> Dict[str, List]:
    """比对提取的引用与论文列表，返回匹配结果。

    Args:
        extracted_citations: extract_citations() 返回的引用列表
        paper_list: 原始论文列表，每条包含 author/title/year 等字段

    Returns:
        包含 matched/unmatched/not_found 三个列表的字典
    """
    if not extracted_citations:
        return {"matched": [], "unmatched": [], "not_found": []}

    if not paper_list:
        return {
            "matched": [],
            "unmatched": list(extracted_citations),
            "not_found": [],
        }

    paper_authors_years: List[Tuple[str, str]] = []
    for paper in paper_list:
        author = paper.get("author", "") or paper.get("authors", "")
        year = str(paper.get("year", ""))
        paper_authors_years.append((author.lower(), year))

    matched: List[Dict] = []
    unmatched: List[Dict] = []
    not_found: List[Dict] = []

    for citation in extracted_citations:
        cit_author = citation.get("author", "").lower()
        cit_year = citation.get("year", "")

        found = False
        for paper_author, paper_year in paper_authors_years:
            if cit_year and paper_year and cit_year != paper_year:
                continue

            author_parts = cit_author.replace(" et al.", "").split()
            paper_author_parts = paper_author.replace(" et al.", "").split()

            if not author_parts or not paper_author_parts:
                continue

            if author_parts[0] == paper_author_parts[0]:
                found = True
                break

        if found:
            matched.append(citation)
        else:
            unmatched.append(citation)

    not_found = [
        p for i, p in enumerate(paper_list)
        if not any(
            _citation_matches_paper(c, p)
            for c in extracted_citations
        )
    ]

    return {
        "matched": matched,
        "unmatched": unmatched,
        "not_found": not_found,
    }


def calculate_citation_accuracy(validation_result: Dict[str, List]) -> float:
    """计算引用准确率。

    准确率 = 准确引用数 / 总引用数

    Args:
        validation_result: validate_citations() 返回的验证结果

    Returns:
        引用准确率（0.0-1.0）
    """
    matched = validation_result.get("matched", [])
    unmatched = validation_result.get("unmatched", [])
    total = len(matched) + len(unmatched)

    if total == 0:
        return 0.0

    return round(len(matched) / total, 4)


def _citation_matches_paper(
    citation: Dict[str, str], paper: Dict[str, str]
) -> bool:
    """判断引用是否匹配论文。"""
    cit_author = citation.get("author", "").lower()
    cit_year = citation.get("year", "")

    paper_author = (paper.get("author", "") or paper.get("authors", "")).lower()
    paper_year = str(paper.get("year", ""))

    if cit_year and paper_year and cit_year != paper_year:
        return False

    author_parts = cit_author.replace(" et al.", "").split()
    paper_author_parts = paper_author.replace(" et al.", "").split()

    if not author_parts or not paper_author_parts:
        return False

    return author_parts[0] == paper_author_parts[0]
