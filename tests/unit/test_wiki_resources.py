"""
Unit tests for Wiki Resource Management

Tests:
- CodemapContext context manager
- Wiki generation context
- Graceful degradation
- Error handling
"""

import unittest
import tempfile
import os
import json
import shutil

from api.tools.wiki_resources import (
    CodemapContext,
    codemap_context,
    wiki_generation_context,
    save_codemap_to_cache
)
from api.tools.codemap_cache import codemap_cache
from api.tools.wiki_exceptions import CodemapLoadError


class TestCodemapContext(unittest.TestCase):
    """Test CodemapContext context manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        codemap_cache.clear()

    def tearDown(self):
        """Clean up test fixtures."""
        codemap_cache.clear()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_context_manager_with_existing_codemap(self):
        """Test context manager with existing codemap file."""
        # Create codemap file
        test_data = {'total_files': 100}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Use context manager
        with CodemapContext(self.test_dir) as codemap:
            self.assertIsNotNone(codemap)
            self.assertEqual(codemap['total_files'], 100)

    def test_context_manager_without_codemap(self):
        """Test context manager without codemap file (graceful degradation)."""
        # Use context manager (no file exists)
        with CodemapContext(self.test_dir) as codemap:
            self.assertIsNotNone(codemap)
            self.assertEqual(codemap, {})  # Should return empty dict

    def test_context_manager_exception_handling(self):
        """Test that exceptions in context are properly handled."""
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'test': 'data'}, f)

        try:
            with CodemapContext(self.test_dir) as codemap:
                self.assertIsNotNone(codemap)
                # Raise exception inside context
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Context manager should have cleaned up properly
        # (No assertions needed, just checking it doesn't crash)

    def test_functional_context_manager(self):
        """Test functional codemap_context wrapper."""
        test_data = {'functional': True}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        with codemap_context(self.test_dir) as codemap:
            self.assertIsNotNone(codemap)
            self.assertTrue(codemap.get('functional', False))


class TestWikiGenerationContext(unittest.TestCase):
    """Test wiki_generation_context."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        codemap_cache.clear()

    def tearDown(self):
        """Clean up test fixtures."""
        codemap_cache.clear()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_wiki_context_with_codemap(self):
        """Test wiki generation context with codemap enabled."""
        test_data = {'wiki': 'test'}
        cache_file = os.path.join(self.test_dir, ".codemap_summary.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        with wiki_generation_context(self.test_dir, use_codemap=True) as resources:
            self.assertIn('codemap', resources)
            self.assertIn('errors', resources)

            self.assertIsNotNone(resources['codemap'])
            self.assertEqual(resources['codemap']['wiki'], 'test')
            self.assertEqual(len(resources['errors']), 0)

    def test_wiki_context_without_codemap(self):
        """Test wiki generation context with codemap disabled."""
        with wiki_generation_context(self.test_dir, use_codemap=False) as resources:
            self.assertIn('codemap', resources)
            self.assertIn('errors', resources)

            self.assertIsNone(resources['codemap'])
            self.assertEqual(len(resources['errors']), 0)

    def test_wiki_context_error_tracking(self):
        """Test error tracking in wiki generation context."""
        # No codemap file exists, but we're trying to use it
        with wiki_generation_context(self.test_dir, use_codemap=True) as resources:
            # Should handle gracefully (no errors tracked for missing file)
            # Because CodemapContext has graceful degradation
            self.assertEqual(len(resources['errors']), 0)


class TestSaveCodemapToCache(unittest.TestCase):
    """Test save_codemap_to_cache utility."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        codemap_cache.clear()

    def tearDown(self):
        """Clean up test fixtures."""
        codemap_cache.clear()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_codemap_success(self):
        """Test successful codemap save."""
        test_data = {
            'total_files': 150,
            'key_modules': [{'name': 'TestModule'}]
        }

        cache_file = save_codemap_to_cache(self.test_dir, test_data)

        # Check file was created
        self.assertTrue(os.path.exists(cache_file))

        # Check cache was updated
        cached_data = codemap_cache.get(self.test_dir)
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data['total_files'], 150)

    def test_save_codemap_invalid_path(self):
        """Test save codemap with invalid path."""
        with self.assertRaises(CodemapLoadError):
            save_codemap_to_cache('/invalid/nonexistent/path', {})


if __name__ == '__main__':
    unittest.main()
