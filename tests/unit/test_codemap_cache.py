"""
Unit tests for CodemapCacheManager

Tests:
- Singleton pattern
- Thread safety
- TTL expiration
- File loading and saving
"""

import unittest
import tempfile
import os
import json
import time
import threading
from datetime import datetime, timedelta

from api.tools.codemap_cache import CodemapCacheManager, codemap_cache
from api.tools.wiki_exceptions import CodemapLoadError


class TestCodemapCacheManager(unittest.TestCase):
    """Test CodemapCacheManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test
        self.test_dir = tempfile.mkdtemp()

        # Clear cache before each test
        codemap_cache.clear()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clear cache after test
        codemap_cache.clear()

        # Clean up temp directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_singleton_pattern(self):
        """Test that CodemapCacheManager is a singleton."""
        instance1 = CodemapCacheManager()
        instance2 = CodemapCacheManager()

        self.assertIs(instance1, instance2, "Should return the same instance")
        self.assertIs(instance1, codemap_cache, "Should be the same as global instance")

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        test_data = {
            'total_files': 100,
            'total_classes': 50,
            'key_modules': [{'name': 'TestModule', 'type': 'class'}]
        }

        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")

        # Set cache
        codemap_cache.set(self.test_dir, test_data, cache_file)

        # Get from cache
        result = codemap_cache.get(self.test_dir)

        self.assertIsNotNone(result)
        self.assertEqual(result['total_files'], 100)
        self.assertEqual(result['total_classes'], 50)

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        result = codemap_cache.get('/nonexistent/path')
        self.assertIsNone(result)

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        test_data = {'test': 'data'}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")

        # Set cache
        codemap_cache.set(self.test_dir, test_data, cache_file)

        # Manually expire the cache by modifying TTL
        # (In real scenario, this would happen after 1 hour)
        old_ttl = codemap_cache._ttl
        codemap_cache._ttl = timedelta(seconds=0)

        # Should not find in cache (expired)
        result = codemap_cache.get(self.test_dir)

        # Restore TTL
        codemap_cache._ttl = old_ttl

        # Result should be None because cache expired and no file exists
        self.assertIsNone(result)

    def test_load_from_file(self):
        """Test loading codemap from file."""
        test_data = {
            'total_files': 200,
            'key_modules': []
        }

        # Create cache file
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Get from cache (should load from file)
        result = codemap_cache.get(self.test_dir)

        self.assertIsNotNone(result)
        self.assertEqual(result['total_files'], 200)

    def test_force_reload(self):
        """Test force reload bypasses cache."""
        test_data = {'version': 1}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")

        # Set initial cache
        codemap_cache.set(self.test_dir, test_data, cache_file)

        # Update file with new data
        updated_data = {'version': 2}
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f)

        # Normal get should return cached version 1
        result1 = codemap_cache.get(self.test_dir, force_reload=False)
        self.assertEqual(result1['version'], 1)

        # Force reload should get version 2 from file
        result2 = codemap_cache.get(self.test_dir, force_reload=True)
        self.assertEqual(result2['version'], 2)

    def test_thread_safety(self):
        """Test thread-safe concurrent access."""
        test_data = {'thread_test': True}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")

        results = []
        errors = []

        def worker(worker_id):
            """Worker function for concurrent access."""
            try:
                # Set cache
                data = {'worker': worker_id}
                codemap_cache.set(f"{self.test_dir}_{worker_id}", data, cache_file)

                # Get cache
                result = codemap_cache.get(f"{self.test_dir}_{worker_id}")

                results.append((worker_id, result))
            except Exception as e:
                errors.append((worker_id, e))

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10, "All threads should complete")

    def test_clear_cache(self):
        """Test clearing cache."""
        # Add multiple entries
        for i in range(3):
            codemap_cache.set(f"{self.test_dir}_{i}", {'id': i}, "test.json")

        # Clear all
        codemap_cache.clear()

        stats = codemap_cache.get_stats()
        self.assertEqual(stats['total_entries'], 0)

    def test_clear_specific_cache(self):
        """Test clearing specific cache entry."""
        # Add multiple entries
        codemap_cache.set(f"{self.test_dir}_1", {'id': 1}, "test1.json")
        codemap_cache.set(f"{self.test_dir}_2", {'id': 2}, "test2.json")

        # Clear only one
        codemap_cache.clear(f"{self.test_dir}_1")

        stats = codemap_cache.get_stats()
        self.assertEqual(stats['total_entries'], 1)

    def test_get_stats(self):
        """Test getting cache statistics."""
        test_data = {'test': 'data'}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")

        codemap_cache.set(self.test_dir, test_data, cache_file)

        stats = codemap_cache.get_stats()

        self.assertEqual(stats['total_entries'], 1)
        self.assertIn('entries', stats)
        self.assertEqual(len(stats['entries']), 1)

        entry = stats['entries'][0]
        self.assertIn('repo_path', entry)
        self.assertIn('loaded_at', entry)
        self.assertIn('age_seconds', entry)

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON file raises CodemapLoadError."""
        # Create invalid JSON file
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")
        with open(cache_file, 'w') as f:
            f.write("invalid json {{{")

        # Should raise CodemapLoadError
        with self.assertRaises(CodemapLoadError):
            codemap_cache.get(self.test_dir)


if __name__ == '__main__':
    unittest.main()
