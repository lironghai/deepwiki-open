"""
API Tools Module

Provides utility classes and functions for enhanced RAG and Wiki generation:
- Codemap caching and management
- Wiki resource management (Context Managers)
- Exception hierarchy
- Wiki structure validation
- Layered RAG retrieval
- Parallel wiki generation
"""

from api.tools.wiki_exceptions import (
    WikiException,
    WikiValidationError,
    WikiGenerationError,
    WikiResourceError,
    CodemapLoadError,
    RAGRetrievalError,
)

from api.tools.codemap_cache import CodemapCacheManager, codemap_cache
from api.tools.rag_layers import (
    RAGLayerResult,
    DependencyContextExpander,
    LayeredRAG,
)
from api.tools.wiki_generator import (
    PageGenerationResult,
    ParallelWikiGenerator,
)
from api.tools.mermaid_preprocessor import MermaidPreprocessor

__all__ = [
    # Exceptions
    "WikiException",
    "WikiValidationError",
    "WikiGenerationError",
    "WikiResourceError",
    "CodemapLoadError",
    "RAGRetrievalError",
    # Cache
    "CodemapCacheManager",
    "codemap_cache",
    # Layered RAG
    "RAGLayerResult",
    "DependencyContextExpander",
    "LayeredRAG",
    # Parallel Generation
    "PageGenerationResult",
    "ParallelWikiGenerator",
    # Mermaid Preprocessing
    "MermaidPreprocessor",
]
