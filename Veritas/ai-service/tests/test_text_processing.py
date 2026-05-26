import pytest

from app.utils.text_processing import chunk_text, clean_text, truncate_text


class TestChunkText:

    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        text = "Hello world"
        result = chunk_text(text, chunk_size=800, overlap=100)
        assert len(result) == 1
        assert result[0]["chunk_index"] == 0
        assert result[0]["chunk_type"] == "title_abstract"
        assert result[0]["content"] == text

    def test_exact_chunk_size(self):
        text = "A" * 800
        result = chunk_text(text, chunk_size=800, overlap=100)
        assert len(result) == 1
        assert result[0]["chunk_type"] == "title_abstract"

    def test_normal_chunking(self):
        text = "A" * 2000
        result = chunk_text(text, chunk_size=800, overlap=100)
        assert len(result) >= 2
        assert result[0]["chunk_index"] == 0
        assert result[0]["chunk_type"] == "title_abstract"
        for chunk in result[1:]:
            assert chunk["chunk_type"] == "continuation"

    def test_overlap_between_chunks(self):
        text = "A" * 2000
        result = chunk_text(text, chunk_size=800, overlap=100)
        if len(result) >= 2:
            overlap_text = result[0]["content"][-100:]
            assert result[1]["content"][:100] == overlap_text

    def test_chunk_index_increments(self):
        text = "A" * 2000
        result = chunk_text(text, chunk_size=800, overlap=100)
        for i, chunk in enumerate(result):
            assert chunk["chunk_index"] == i

    def test_last_chunk_merge_when_small(self):
        chunk_size = 800
        overlap = 100
        text_len = chunk_size + chunk_size + int(chunk_size * 0.1)
        text = "A" * text_len
        result = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        last_chunk = result[-1]
        if len(last_chunk["content"]) < chunk_size * 0.2:
            assert len(result) == 2
            assert len(result[-1]["content"]) > chunk_size

    def test_custom_overlap(self):
        text = "A" * 2000
        result = chunk_text(text, chunk_size=800, overlap=50)
        if len(result) >= 2:
            overlap_text = result[0]["content"][-50:]
            assert result[1]["content"][:50] == overlap_text


class TestCleanText:

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_strip_whitespace(self):
        assert clean_text("  hello  ") == "hello"

    def test_multiple_spaces(self):
        assert clean_text("hello   world") == "hello world"

    def test_control_characters(self):
        assert clean_text("hello\x00world") == "hello world"
        assert clean_text("test\x01\x02\x03") == "test"

    def test_multiple_newlines(self):
        assert clean_text("hello\n\n\nworld") == "hello\nworld"

    def test_preserve_chinese(self):
        assert clean_text("你好 世界") == "你好 世界"

    def test_preserve_basic_punctuation(self):
        text = "Hello, world! How are you? Fine; thanks: great."
        assert clean_text(text) == text

    def test_combined_cleaning(self):
        result = clean_text("  Hello\n\n\n  World  \x00  ")
        assert result == "Hello\n World"

    def test_tabs_converted_to_space(self):
        assert clean_text("hello\tworld") == "hello world"


class TestTruncateText:

    def test_short_text_no_truncation(self):
        text = "Hello world"
        assert truncate_text(text, 100) == text

    def test_truncate_at_period(self):
        text = "Hello world. This is a test."
        result = truncate_text(text, 15)
        assert result == "Hello world."

    def test_truncate_at_newline(self):
        text = "Hello world\nThis is a test"
        result = truncate_text(text, 15)
        assert result == "Hello world"

    def test_hard_truncation(self):
        text = "Hello world this is a test"
        result = truncate_text(text, 11)
        assert result == "Hello world"

    def test_strip_after_truncation(self):
        text = "Hello world.   "
        result = truncate_text(text, 13)
        assert result == "Hello world."

    def test_empty_text(self):
        assert truncate_text("", 10) == ""

    def test_exact_length(self):
        text = "Hello"
        assert truncate_text(text, 5) == "Hello"
