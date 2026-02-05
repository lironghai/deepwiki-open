"""
Codemap Cache Manager

Thread-safe singleton cache manager for codemap data.
Ensures multiple workers can share the same codemap instance efficiently.
"""

import threading
import json
import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from api.tools.wiki_exceptions import CodemapLoadError

logger = logging.getLogger(__name__)


@dataclass
class CodemapCacheEntry:
    """
    Codemap cache entry with metadata.

    Attributes:
        data: The actual codemap data (parsed JSON)
        loaded_at: Timestamp when the codemap was loaded
        repo_path: Path to the repository
        file_path: Path to the cache file
    """
    data: Dict[str, Any]
    loaded_at: datetime
    repo_path: str
    file_path: str


class CodemapCacheManager:
    """
    Thread-safe singleton cache manager for codemap data.

    This manager ensures that:
    1. Multiple workers share the same codemap instance (memory efficient)
    2. All operations are thread-safe (using RLock)
    3. Cached data expires after a configurable TTL (default: 1 hour)
    4. File system is used as persistent storage

    Usage:
        from api.tools.codemap_cache import codemap_cache

        # Get codemap (automatically loads from cache or file)
        codemap = codemap_cache.get(repo_path)

        # Set codemap (save to cache)
        codemap_cache.set(repo_path, data, file_path)

        # Clear cache (optional)
        codemap_cache.clear(repo_path)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the cache manager (only once)."""
        if self._initialized:
            return

        # Cache storage
        self._cache: Dict[str, CodemapCacheEntry] = {}

        # Reentrant lock for thread-safe operations
        self._cache_lock = threading.RLock()

        # Cache configuration
        self._ttl = timedelta(hours=1)  # Cache valid for 1 hour

        self._initialized = True
        logger.info("CodemapCacheManager initialized")

    def get(self, repo_path: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get codemap data from cache.

        This method is thread-safe and will:
        1. Check in-memory cache first
        2. Validate cache expiration
        3. Load from file if cache miss or expired
        4. Return None if not found

        Args:
            repo_path: Path to the repository
            force_reload: If True, bypass cache and reload from file

        Returns:
            Codemap data dictionary, or None if not found

        Thread-safe: Yes
        """
        with self._cache_lock:
            cache_key = self._get_cache_key(repo_path)

            # Check in-memory cache
            if not force_reload and cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check expiration
                age = datetime.now() - entry.loaded_at
                if age < self._ttl:
                    logger.debug(f"Cache hit for {repo_path} (age: {age.total_seconds():.1f}s)")
                    return entry.data
                else:
                    # Expired, remove from cache
                    logger.info(f"Cache expired for {repo_path}, removing")
                    del self._cache[cache_key]

            # Cache miss or expired, try loading from file
            return self._load_from_file(repo_path)

    def set(self, repo_path: str, data: Dict[str, Any], file_path: str):
        """
        Set codemap data to cache.

        This method is thread-safe and will store the data in memory.

        Args:
            repo_path: Path to the repository
            data: Codemap data to cache
            file_path: Path to the cache file (for reference)

        Thread-safe: Yes
        """
        with self._cache_lock:
            cache_key = self._get_cache_key(repo_path)

            self._cache[cache_key] = CodemapCacheEntry(
                data=data,
                loaded_at=datetime.now(),
                repo_path=repo_path,
                file_path=file_path
            )

            logger.info(f"Cached codemap for {repo_path} ({len(data)} keys)")

    def clear(self, repo_path: Optional[str] = None):
        """
        Clear cache.

        Args:
            repo_path: If specified, clear only this repository's cache.
                      If None, clear all cache entries.

        Thread-safe: Yes
        """
        with self._cache_lock:
            if repo_path is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cleared all cache ({count} entries)")
            else:
                cache_key = self._get_cache_key(repo_path)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.info(f"Cleared cache for {repo_path}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - total_entries: Number of cached items
            - entries: List of entry details

        Thread-safe: Yes
        """
        with self._cache_lock:
            entries = []
            for cache_key, entry in self._cache.items():
                age = datetime.now() - entry.loaded_at
                entries.append({
                    'repo_path': entry.repo_path,
                    'file_path': entry.file_path,
                    'loaded_at': entry.loaded_at.isoformat(),
                    'age_seconds': age.total_seconds(),
                    'data_keys': list(entry.data.keys()) if entry.data else []
                })

            return {
                'total_entries': len(self._cache),
                'ttl_seconds': self._ttl.total_seconds(),
                'entries': entries
            }

    def _get_cache_key(self, repo_path: str) -> str:
        """
        Generate a normalized cache key from repository path.

        Args:
            repo_path: Path to repository

        Returns:
            Normalized cache key
        """
        # Normalize path to handle different path separators
        return os.path.normpath(repo_path).lower()

    def _load_from_file(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """
        Load codemap from file system.

        This method is called when cache miss occurs.
        It will try to load from the standard cache file location.

        Args:
            repo_path: Path to repository

        Returns:
            Codemap data or None if file doesn't exist or load fails

        Note:
            This method must be called with _cache_lock held.
        """
        # Try standard cache file location
        cache_file = os.path.join(repo_path, ".codemap_summary.json")

        if not os.path.exists(cache_file):
            logger.debug(f"Codemap cache file not found: {cache_file}")
            return None

        try:
            logger.info(f"Loading codemap from file: {cache_file}")

            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate basic structure
            if not isinstance(data, dict):
                raise CodemapLoadError(f"Invalid codemap format: expected dict, got {type(data)}")

            # Store in cache
            self.set(repo_path, data, cache_file)

            logger.info(f"Successfully loaded codemap from {cache_file}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse codemap JSON: {e}")
            raise CodemapLoadError(f"Invalid JSON in codemap file: {e}")

        except Exception as e:
            logger.error(f"Failed to load codemap from file: {e}")
            raise CodemapLoadError(f"Failed to load codemap: {e}")


# Global singleton instance
codemap_cache = CodemapCacheManager()
