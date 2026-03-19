from api.data_pipeline import (
    LLMCodeSummarizer,
    build_semantic_embedding_text,
    chunk_python_ast_first,
)
from api.text_chunker_v2 import EnhancedCodeChunker


def test_build_semantic_embedding_text_contains_summary_and_code():
    summary = "This chunk handles authentication flow."
    code = "def login(user):\n    return user.is_valid()"
    text = build_semantic_embedding_text(code, summary)

    assert "[Semantic Summary]" in text
    assert "[Code]" in text
    assert summary in text
    assert code in text


def test_llm_code_summarizer_uses_heuristic_when_disabled():
    summarizer = LLMCodeSummarizer({"enabled": False})
    code = "class AuthService:\n    def validate(self, token):\n        return True"
    summary = summarizer.summarize(code, "src/auth.py", {"block_type": "code"})

    assert "src/auth.py" in summary
    assert "AuthService" in summary or "code implementation chunk" in summary


def test_enhanced_chunker_splits_large_paragraph_with_fixed_fallback():
    # Single large function with a long non-empty paragraph (no blank lines),
    # which previously could overflow chunk limits in edge cases.
    large_func_body = "\n".join([f"    value_{i} = {i}" for i in range(500)])
    code = f"def huge_function():\n{large_func_body}\n    return value_1\n"

    # Simple token estimator for deterministic testing
    count_tokens = lambda text: max(1, len(text) // 4)
    chunker = EnhancedCodeChunker(max_tokens=300, overlap_tokens=20, force_split_threshold=1.0)
    chunks = chunker.chunk_text(code, count_tokens, {"file_type": "py"})

    assert len(chunks) > 1
    for chunk in chunks:
        assert count_tokens(chunk.content) <= 300


def test_python_ast_chunking_produces_multiple_structured_chunks():
    code = """
import os

class A:
    def run(self):
        return 1

def helper():
    return 2
"""
    count_tokens = lambda text: max(1, len(text) // 4)
    chunks = chunk_python_ast_first(
        content=code,
        relative_path="sample.py",
        count_tokens_fn=count_tokens,
        max_tokens=120,
        overlap_tokens=20,
    )

    assert len(chunks) >= 2
    assert all("import os" in chunk.content for chunk in chunks)
