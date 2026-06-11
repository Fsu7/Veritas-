"""test_citation_parser — 引用解析器单元测试"""
import pytest

from app.utils.citation_parser import (
    calculate_citation_accuracy,
    extract_citations,
    validate_citations,
)


class TestExtractCitations:
    """测试 extract_citations() 函数"""

    def test_extract_author_year_format(self):
        """验证正确提取 [作者, 年份] 格式"""
        report = "Transformer架构[Vaswani, 2017]彻底改变了NLP领域。BERT[Devlin, 2019]进一步推动了预训练模型的发展。"
        citations = extract_citations(report)
        assert len(citations) == 2
        assert citations[0]["author"] == "Vaswani"
        assert citations[0]["year"] == "2017"
        assert citations[0]["original"] == "[Vaswani, 2017]"
        assert citations[1]["author"] == "Devlin"
        assert citations[1]["year"] == "2019"

    def test_extract_parentheses_format(self):
        """验证正确提取 (Author, Year) 格式"""
        report = "Transformer架构(Vaswani, 2017)彻底改变了NLP领域。"
        citations = extract_citations(report)
        assert len(citations) == 1
        assert citations[0]["author"] == "Vaswani"
        assert citations[0]["year"] == "2017"
        assert citations[0]["original"] == "(Vaswani, 2017)"

    def test_extract_mixed_formats(self):
        """验证混合格式提取"""
        report = "Transformer[Vaswani, 2017]和BERT(Devlin, 2019)都是重要模型。"
        citations = extract_citations(report)
        assert len(citations) == 2

    def test_extract_et_al_format(self):
        """验证 et al. 格式提取"""
        report = "多Agent系统[Brown et al., 2020]展示了强大的能力。"
        citations = extract_citations(report)
        assert len(citations) == 1
        assert citations[0]["author"] == "Brown et al."

    def test_extract_deduplication(self):
        """验证同一引用不重复提取"""
        report = "Transformer[Vaswani, 2017]是一种架构。Transformer[Vaswani, 2017]被广泛使用。"
        citations = extract_citations(report)
        assert len(citations) == 1

    def test_extract_empty_report(self):
        """验证空报告返回空列表"""
        assert extract_citations("") == []
        assert extract_citations(None) == []

    def test_extract_no_citations(self):
        """验证无引用标注的报告返回空列表"""
        report = "这是一段没有任何引用的普通文本。"
        citations = extract_citations(report)
        assert citations == []

    def test_extract_whitespace_only(self):
        """验证仅空白字符的报告返回空列表"""
        assert extract_citations("   \n\t  ") == []


class TestValidateCitations:
    """测试 validate_citations() 函数"""

    def test_validate_all_matched(self):
        """验证所有引用都匹配"""
        citations = [
            {"author": "Vaswani", "year": "2017", "original": "[Vaswani, 2017]"},
            {"author": "Devlin", "year": "2019", "original": "[Devlin, 2019]"},
        ]
        papers = [
            {"author": "Vaswani", "year": "2017", "title": "Attention Is All You Need"},
            {"author": "Devlin", "year": "2019", "title": "BERT"},
        ]
        result = validate_citations(citations, papers)
        assert len(result["matched"]) == 2
        assert len(result["unmatched"]) == 0

    def test_validate_unmatched_citation(self):
        """验证不匹配的引用"""
        citations = [
            {"author": "Vaswani", "year": "2017", "original": "[Vaswani, 2017]"},
            {"author": "NonExistent", "year": "2020", "original": "[NonExistent, 2020]"},
        ]
        papers = [
            {"author": "Vaswani", "year": "2017", "title": "Attention Is All You Need"},
        ]
        result = validate_citations(citations, papers)
        assert len(result["matched"]) == 1
        assert len(result["unmatched"]) == 1
        assert result["unmatched"][0]["author"] == "NonExistent"

    def test_validate_empty_citations(self):
        """验证空引用列表"""
        result = validate_citations([], [{"author": "Test", "year": "2020"}])
        assert result["matched"] == []
        assert result["unmatched"] == []
        assert result["not_found"] == []

    def test_validate_empty_papers(self):
        """验证空论文列表"""
        citations = [
            {"author": "Vaswani", "year": "2017", "original": "[Vaswani, 2017]"},
        ]
        result = validate_citations(citations, [])
        assert len(result["matched"]) == 0
        assert len(result["unmatched"]) == 1

    def test_validate_authors_field(self):
        """验证使用 authors 字段的论文"""
        citations = [
            {"author": "Vaswani", "year": "2017", "original": "[Vaswani, 2017]"},
        ]
        papers = [
            {"authors": "Vaswani et al.", "year": "2017", "title": "Attention"},
        ]
        result = validate_citations(citations, papers)
        assert len(result["matched"]) == 1


class TestCalculateCitationAccuracy:
    """测试 calculate_citation_accuracy() 函数"""

    def test_accuracy_all_matched(self):
        """验证全部匹配时准确率为1.0"""
        result = {
            "matched": [
                {"author": "Vaswani", "year": "2017"},
                {"author": "Devlin", "year": "2019"},
            ],
            "unmatched": [],
        }
        assert calculate_citation_accuracy(result) == 1.0

    def test_accuracy_half_matched(self):
        """验证一半匹配时准确率为0.5"""
        result = {
            "matched": [{"author": "Vaswani", "year": "2017"}],
            "unmatched": [{"author": "Fake", "year": "2020"}],
        }
        assert calculate_citation_accuracy(result) == 0.5

    def test_accuracy_none_matched(self):
        """验证全部不匹配时准确率为0.0"""
        result = {
            "matched": [],
            "unmatched": [
                {"author": "Fake", "year": "2020"},
            ],
        }
        assert calculate_citation_accuracy(result) == 0.0

    def test_accuracy_empty_result(self):
        """验证空结果时准确率为0.0"""
        result = {"matched": [], "unmatched": []}
        assert calculate_citation_accuracy(result) == 0.0

    def test_accuracy_precision(self):
        """验证准确率精度（4位小数）"""
        result = {
            "matched": [{"author": "A", "year": "2020"}] * 2,
            "unmatched": [{"author": "B", "year": "2021"}],
        }
        accuracy = calculate_citation_accuracy(result)
        assert accuracy == round(2 / 3, 4)
