"""
Wiki Resource Management

Provides context managers for proper resource management during wiki generation.
Ensures codemap and other resources are loaded, used, and cleaned up correctly.
"""

import os
import json
import logging
from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any

from api.tools.codemap_cache import codemap_cache
from api.tools.wiki_exceptions import CodemapLoadError

logger = logging.getLogger(__name__)


class CodemapContext:
    """
    Context manager for codemap loading and cleanup.

    This ensures that:
    1. Codemap is loaded from cache or file when entering context
    2. If loading fails, returns empty dict (graceful degradation)
    3. Resources are properly managed on exit

    Usage:
        with CodemapContext(repo_path) as codemap:
            # Use codemap safely
            if codemap:
                # Work with codemap data
                pass
            else:
                # Graceful degradation
                pass
    """

    def __init__(self, repo_path: str, force_regenerate: bool = False):
        """
        Initialize codemap context.

        Args:
            repo_path: Path to the repository
            force_regenerate: If True, force regeneration of codemap
        """
        self.repo_path = repo_path
        self.force_regenerate = force_regenerate
        self.codemap: Optional[Dict[str, Any]] = None
        self._loaded = False

    def __enter__(self) -> Dict[str, Any]:
        """
        Enter context: load codemap.

        Returns:
            Codemap data (dict), or empty dict if loading fails

        Note:
            This method implements graceful degradation - if codemap
            loading fails, it returns an empty dict instead of raising
            an exception, allowing the workflow to continue.
        """
        try:
            # Try to get from cache first
            self.codemap = codemap_cache.get(self.repo_path, self.force_regenerate)

            if self.codemap is None:
                if self.force_regenerate:
                    logger.info(f"Force regenerate requested for {self.repo_path}")
                    # Note: Actual regeneration should be done outside this context
                    # This context manager only handles loading existing codemaps
                    self.codemap = {}
                else:
                    logger.info(f"No cached codemap found for {self.repo_path}")
                    self.codemap = {}
            else:
                logger.info(f"Using cached codemap for {self.repo_path}")

            self._loaded = True
            return self.codemap

        except CodemapLoadError as e:
            logger.error(f"Codemap load error: {e}")
            # Graceful degradation: return empty dict
            self.codemap = {}
            return self.codemap

        except Exception as e:
            logger.error(f"Unexpected error loading codemap: {e}")
            # Graceful degradation: return empty dict
            self.codemap = {}
            return self.codemap

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context: cleanup resources.

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)

        Returns:
            False to propagate exceptions (do not suppress)
        """
        if exc_type is not None:
            logger.error(f"Error in codemap context: {exc_val}")

        # Cleanup (if needed)
        # Note: We don't clear the cache here because other workers
        # might still be using it. The cache has its own TTL mechanism.

        self._loaded = False

        # Do not suppress exceptions
        return False


@contextmanager
def codemap_context(repo_path: str, force_regenerate: bool = False) -> Generator[Dict[str, Any], None, None]:
    """
    Functional context manager for codemap loading.

    This is a convenience wrapper around CodemapContext class.

    Args:
        repo_path: Path to the repository
        force_regenerate: If True, force regeneration of codemap

    Yields:
        Codemap data (dict), or empty dict if loading fails

    Usage:
        with codemap_context(repo_path) as codemap:
            if codemap:
                # Use codemap
                modules = codemap.get('key_modules', [])
            else:
                # Graceful degradation
                pass
    """
    ctx = CodemapContext(repo_path, force_regenerate)
    try:
        yield ctx.__enter__()
    finally:
        ctx.__exit__(None, None, None)


@contextmanager
def wiki_generation_context(
    repo_path: str,
    use_codemap: bool = True,
    force_regenerate_codemap: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """
    Comprehensive context manager for wiki generation.

    Manages all resources needed for wiki generation:
    - Codemap loading and caching
    - Error tracking
    - Resource cleanup

    Args:
        repo_path: Path to the repository
        use_codemap: Whether to load codemap
        force_regenerate_codemap: Whether to force codemap regeneration

    Yields:
        Dictionary with resources:
        {
            'codemap': Dict or None,
            'errors': List of (source, exception) tuples
        }

    Usage:
        with wiki_generation_context(repo_path) as resources:
            codemap = resources['codemap']
            if codemap:
                # Generate wiki with codemap enhancement
                pass
            else:
                # Generate wiki without codemap
                pass

            # Check for errors
            if resources['errors']:
                logger.warning(f"Errors occurred: {resources['errors']}")
    """
    resources = {
        'codemap': None,
        'errors': []
    }

    try:
        # Load codemap if requested
        if use_codemap:
            try:
                with codemap_context(repo_path, force_regenerate_codemap) as codemap:
                    resources['codemap'] = codemap if codemap else None
            except Exception as e:
                logger.error(f"Failed to load codemap: {e}")
                resources['errors'].append(('codemap', e))
                # Continue execution with None codemap (graceful degradation)

        yield resources

    except Exception as e:
        logger.error(f"Error in wiki generation context: {e}")
        resources['errors'].append(('general', e))
        raise

    finally:
        # Cleanup
        logger.debug("Cleaning up wiki generation resources")
        # Codemap is managed by its own cache manager
        # No explicit cleanup needed here


def save_codemap_to_cache(repo_path: str, codemap: Dict[str, Any]) -> str:
    """
    Save codemap to cache file and update cache manager.

    This is a utility function to save a newly generated codemap.

    Args:
        repo_path: Path to the repository
        codemap: Codemap data to save

    Returns:
        Path to the saved cache file

    Raises:
        CodemapLoadError: If saving fails
    """
    try:
        # Ensure repo path exists
        if not os.path.exists(repo_path):
            raise CodemapLoadError(f"Repository path does not exist: {repo_path}")

        # Save to standard cache file location
        cache_file = os.path.join(repo_path, ".codemap_summary.json")

        logger.info(f"Saving codemap to {cache_file}")

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(codemap, f, indent=2, ensure_ascii=False)

        # Update cache manager
        codemap_cache.set(repo_path, codemap, cache_file)

        logger.info(f"Successfully saved codemap to {cache_file}")
        return cache_file

    except Exception as e:
        logger.error(f"Failed to save codemap: {e}")
        raise CodemapLoadError(f"Failed to save codemap: {e}")
