"""
Unit tests for Parallel Wiki Generator

Tests:
- PageGenerationResult dataclass
- ParallelWikiGenerator initialization
- Single page generation
- Parallel page generation
- Error handling
- Codemap integration
- Statistics calculation
"""

import unittest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from dataclasses import asdict

from api.tools.wiki_generator import (
    PageGenerationResult,
    ParallelWikiGenerator
)


class MockLLMService:
    """Mock LLM service for testing"""
    def __init__(self, should_fail=False, delay_ms=0):
        self.should_fail = should_fail
        self.delay_ms = delay_ms
        self.call_count = 0

    async def generate(self, prompt: str) -> str:
        """Mock generate method"""
        self.call_count += 1

        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000)

        if self.should_fail:
            raise Exception("Mock LLM service failure")

        return f"Generated content for prompt: {prompt[:50]}..."


class TestPageGenerationResult(unittest.TestCase):
    """Test PageGenerationResult dataclass"""

    def test_create_successful_result(self):
        """Test creating a successful generation result"""
        result = PageGenerationResult(
            page_index=0,
            title="Test Page",
            content="# Test Content",
            success=True,
            codemap_used=True,
            modules_referenced=5,
            generation_time_ms=150.5
        )

        self.assertEqual(result.page_index, 0)
        self.assertEqual(result.title, "Test Page")
        self.assertEqual(result.content, "# Test Content")
        self.assertTrue(result.success)
        self.assertTrue(result.codemap_used)
        self.assertEqual(result.modules_referenced, 5)
        self.assertEqual(result.generation_time_ms, 150.5)
        self.assertIsNone(result.error)

    def test_create_failed_result(self):
        """Test creating a failed generation result"""
        result = PageGenerationResult(
            page_index=1,
            title="Failed Page",
            content="",
            success=False,
            error="Generation failed"
        )

        self.assertEqual(result.page_index, 1)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Generation failed")


class TestParallelWikiGenerator(unittest.TestCase):
    """Test ParallelWikiGenerator functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.llm_service = MockLLMService()
        self.generator = ParallelWikiGenerator(
            llm_service=self.llm_service,
            max_workers=3,
            enable_codemap=False  # Disable for basic tests
        )

    def test_initialization(self):
        """Test generator initialization"""
        self.assertIsNotNone(self.generator.llm_service)
        self.assertEqual(self.generator.max_workers, 3)
        self.assertFalse(self.generator.enable_codemap)

    def test_initialization_with_defaults(self):
        """Test generator initialization with default values"""
        generator = ParallelWikiGenerator()

        self.assertIsNone(generator.llm_service)
        self.assertEqual(generator.max_workers, 5)
        self.assertTrue(generator.enable_codemap)

    def test_generate_empty_pages_list(self):
        """Test generating with empty pages list"""
        async def run_test():
            results = await self.generator.generate_pages_parallel([], "/test/repo")
            self.assertEqual(len(results), 0)

        asyncio.run(run_test())

    def test_generate_single_page(self):
        """Test generating a single page"""
        async def run_test():
            pages = [
                {
                    'title': 'Test Page 1',
                    'description': 'Test description',
                    'relevant_files': []
                }
            ]

            results = await self.generator.generate_pages_parallel(
                pages,
                "/test/repo"
            )

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].success)
            self.assertEqual(results[0].title, 'Test Page 1')
            self.assertIn('Generated content', results[0].content)

        asyncio.run(run_test())

    def test_generate_multiple_pages_parallel(self):
        """Test generating multiple pages in parallel"""
        async def run_test():
            pages = [
                {'title': f'Page {i}', 'description': f'Description {i}'}
                for i in range(10)
            ]

            results = await self.generator.generate_pages_parallel(
                pages,
                "/test/repo"
            )

            self.assertEqual(len(results), 10)

            # Verify all succeeded
            successful = sum(1 for r in results if r.success)
            self.assertEqual(successful, 10)

            # Verify order is maintained
            for i, result in enumerate(results):
                self.assertEqual(result.page_index, i)
                self.assertEqual(result.title, f'Page {i}')

        asyncio.run(run_test())

    def test_progress_callback(self):
        """Test progress callback is called"""
        progress_calls = []

        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        async def run_test():
            pages = [{'title': f'Page {i}'} for i in range(5)]

            await self.generator.generate_pages_parallel(
                pages,
                "/test/repo",
                progress_callback=progress_callback
            )

            # Should have 5 progress updates
            self.assertEqual(len(progress_calls), 5)

            # Last call should be (5, 5)
            self.assertEqual(progress_calls[-1], (5, 5))

        asyncio.run(run_test())

    def test_error_handling_partial_failure(self):
        """Test handling when some pages fail"""
        # Create service that fails on specific calls
        failing_service = MockLLMService()
        failing_service.should_fail = True

        generator = ParallelWikiGenerator(
            llm_service=failing_service,
            enable_codemap=False
        )

        async def run_test():
            pages = [
                {'title': 'Page 1'},
                {'title': 'Page 2'},
                {'title': 'Page 3'}
            ]

            results = await generator.generate_pages_parallel(pages, "/test/repo")

            self.assertEqual(len(results), 3)

            # All should fail because service always fails
            failed = sum(1 for r in results if not r.success)
            self.assertEqual(failed, 3)

            # Each should have error message
            for result in results:
                self.assertIsNotNone(result.error)

        asyncio.run(run_test())

    def test_extract_relevant_modules(self):
        """Test extracting relevant modules from codemap"""
        codemap = {
            'key_modules': [
                {'name': 'ModuleA', 'file': '/test/file1.py', 'type': 'class'},
                {'name': 'ModuleB', 'file': '/test/file2.py', 'type': 'class'},
                {'name': 'ModuleC', 'file': '/other/file3.py', 'type': 'function'}
            ],
            'nodes': [
                {'name': 'NodeA', 'path': '/test/file1.py', 'type': 'class'}
            ]
        }

        page = {
            'title': 'Test',
            'relevant_files': ['/test/file1.py', '/test/file2.py']
        }

        modules = self.generator._extract_relevant_modules(page, codemap)

        # Should find ModuleA, ModuleB, and NodeA
        self.assertGreaterEqual(len(modules), 2)

        module_names = [m.get('name') for m in modules]
        self.assertIn('ModuleA', module_names)
        self.assertIn('ModuleB', module_names)

    def test_extract_relevant_modules_no_files(self):
        """Test extracting modules when page has no relevant files"""
        codemap = {
            'key_modules': [
                {'name': 'ModuleA', 'file': '/test/file1.py'}
            ]
        }

        page = {
            'title': 'Test',
            'relevant_files': []
        }

        modules = self.generator._extract_relevant_modules(page, codemap)

        self.assertEqual(len(modules), 0)

    def test_build_enhanced_prompt(self):
        """Test building enhanced prompt with codemap"""
        page = {
            'title': 'Test Page',
            'description': 'Test description'
        }

        modules = [
            {'name': 'TestModule', 'type': 'class', 'description': 'A test module'}
        ]

        codemap = {
            'architecture_layers': [
                {'name': 'Layer1'},
                {'name': 'Layer2'}
            ]
        }

        prompt = self.generator._build_enhanced_prompt(page, modules, codemap)

        self.assertIn('Test Page', prompt)
        self.assertIn('Test description', prompt)
        self.assertIn('TestModule', prompt)
        self.assertIn('Layer1', prompt)
        self.assertIn('Layer2', prompt)

    def test_build_basic_prompt(self):
        """Test building basic prompt without codemap"""
        page = {
            'title': 'Basic Page',
            'description': 'Basic description'
        }

        prompt = self.generator._build_basic_prompt(page)

        self.assertIn('Basic Page', prompt)
        self.assertIn('Basic description', prompt)

    def test_generate_template_content(self):
        """Test generating template content"""
        page = {
            'title': 'Template Test',
            'description': 'Template description'
        }

        content = self.generator._generate_template_content(page)

        self.assertIn('Template Test', content)
        self.assertIn('Template description', content)
        self.assertIn('# Template Test', content)

    def test_generate_template_content_with_modules(self):
        """Test generating template content with modules"""
        page = {'title': 'Test'}

        modules = [
            {'name': 'ModuleA', 'type': 'class'},
            {'name': 'ModuleB', 'type': 'function'}
        ]

        content = self.generator._generate_template_content_with_modules(
            page,
            modules
        )

        self.assertIn('ModuleA', content)
        self.assertIn('ModuleB', content)
        self.assertIn('Related Modules', content)

    def test_get_statistics_empty(self):
        """Test statistics calculation with empty results"""
        stats = self.generator.get_statistics([])

        self.assertEqual(stats['total_pages'], 0)
        self.assertEqual(stats['successful'], 0)
        self.assertEqual(stats['failed'], 0)

    def test_get_statistics(self):
        """Test statistics calculation"""
        results = [
            PageGenerationResult(
                page_index=0,
                title="Page 1",
                content="Content",
                success=True,
                codemap_used=True,
                modules_referenced=5,
                generation_time_ms=100.0
            ),
            PageGenerationResult(
                page_index=1,
                title="Page 2",
                content="Content",
                success=True,
                codemap_used=False,
                modules_referenced=0,
                generation_time_ms=200.0
            ),
            PageGenerationResult(
                page_index=2,
                title="Page 3",
                content="",
                success=False,
                error="Failed",
                generation_time_ms=50.0
            )
        ]

        stats = self.generator.get_statistics(results)

        self.assertEqual(stats['total_pages'], 3)
        self.assertEqual(stats['successful'], 2)
        self.assertEqual(stats['failed'], 1)
        self.assertAlmostEqual(stats['success_rate'], 66.67, places=1)
        self.assertAlmostEqual(stats['avg_generation_time_ms'], 116.67, places=1)
        self.assertAlmostEqual(stats['codemap_usage_rate'], 33.33, places=1)
        self.assertEqual(stats['total_modules_referenced'], 5)

    def test_codemap_integration(self):
        """Test integration with codemap cache"""
        # Create generator with codemap enabled
        generator = ParallelWikiGenerator(
            llm_service=self.llm_service,
            enable_codemap=True
        )

        async def run_test():
            with patch('api.tools.wiki_generator.codemap_cache') as mock_cache:
                # Mock codemap data
                mock_cache.get.return_value = {
                    'nodes': [
                        {'name': 'TestNode', 'path': '/test/file.py', 'type': 'class'}
                    ],
                    'key_modules': [],
                    'architecture_layers': []
                }

                pages = [{'title': 'Test Page', 'relevant_files': ['/test/file.py']}]

                results = await generator.generate_pages_parallel(pages, "/test/repo")

                # Verify codemap was accessed
                mock_cache.get.assert_called_with("/test/repo")

                self.assertEqual(len(results), 1)
                self.assertTrue(results[0].success)

        asyncio.run(run_test())

    def test_max_workers_configuration(self):
        """Test max_workers configuration"""
        generator_3 = ParallelWikiGenerator(max_workers=3)
        generator_10 = ParallelWikiGenerator(max_workers=10)

        self.assertEqual(generator_3.max_workers, 3)
        self.assertEqual(generator_10.max_workers, 10)

    def test_llm_service_async_call(self):
        """Test calling async LLM service"""
        async def run_test():
            prompt = "Test prompt"
            content = await self.generator._call_llm_service(prompt)

            self.assertIsNotNone(content)
            self.assertIn("Generated content", content)

            # Verify LLM was called
            self.assertEqual(self.llm_service.call_count, 1)

        asyncio.run(run_test())

    def test_generation_without_llm_service(self):
        """Test generation without LLM service (fallback to templates)"""
        generator = ParallelWikiGenerator(
            llm_service=None,
            enable_codemap=False
        )

        async def run_test():
            pages = [{'title': 'Fallback Test', 'description': 'Test'}]

            results = await generator.generate_pages_parallel(pages, "/test/repo")

            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].success)

            # Content should be template-based
            self.assertIn('Fallback Test', results[0].content)
            self.assertIn('Overview', results[0].content)

        asyncio.run(run_test())

    def test_page_order_maintained(self):
        """Test that page order is maintained even with parallel execution"""
        async def run_test():
            # Use delays to ensure out-of-order completion
            pages = [
                {'title': f'Page {i}', 'delay': (10 - i) * 10}
                for i in range(10)
            ]

            results = await self.generator.generate_pages_parallel(pages, "/test/repo")

            # Verify order is maintained
            for i, result in enumerate(results):
                self.assertEqual(result.page_index, i)

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
