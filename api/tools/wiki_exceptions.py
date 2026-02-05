"""
Wiki Exception Hierarchy

Provides structured exception handling for wiki generation and RAG operations.
"""


class WikiException(Exception):
    """
    Base exception for all wiki-related errors.

    This is the root of the exception hierarchy and should be used
    for catching all wiki-related errors.
    """
    pass


class WikiValidationError(WikiException):
    """
    Raised when wiki structure validation fails.

    Examples:
        - Invalid page structure
        - Missing required fields
        - Invalid data types
    """
    pass


class WikiGenerationError(WikiException):
    """
    Raised when wiki content generation fails.

    Examples:
        - LLM generation failure
        - Timeout during generation
        - Invalid generated content
    """
    pass


class WikiResourceError(WikiException):
    """
    Raised when resource management fails.

    Examples:
        - File not found
        - Permission denied
        - Resource exhausted
    """
    pass


class CodemapLoadError(WikiResourceError):
    """
    Raised when codemap loading or generation fails.

    Examples:
        - Codemap file not found
        - Codemap parsing error
        - Codemap generation timeout
    """
    pass


class RAGRetrievalError(WikiException):
    """
    Raised when RAG retrieval fails.

    Examples:
        - No documents found
        - Embedding failure
        - FAISS index error
    """
    pass
