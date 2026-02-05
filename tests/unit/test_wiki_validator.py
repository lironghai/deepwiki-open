"""
Unit tests for WikiStructureValidator

Tests:
- Structure validation
- Page validation
- Error detection
- Sanitization
"""

import unittest

from api.tools.wiki_validator import WikiStructureValidator
from api.tools.wiki_exceptions import WikiValidationError


class TestWikiStructureValidator(unittest.TestCase):
    """Test WikiStructureValidator functionality."""

    def test_valid_structure(self):
        """Test validation of valid wiki structure."""
        valid_structure = {
            'pages': [
                {
                    'title': 'Introduction',
                    'content': 'Welcome to the wiki'
                },
                {
                    'title': 'Getting Started',
                    'content': 'How to get started'
                }
            ],
            'metadata': {
                'repo': 'test/repo',
                'language': 'en'
            }
        }

        is_valid, errors = WikiStructureValidator.validate_structure(valid_structure)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_missing_pages_field(self):
        """Test validation fails when 'pages' field is missing."""
        invalid_structure = {
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertIn("Missing required field: pages", errors)

    def test_missing_metadata_field(self):
        """Test validation fails when 'metadata' field is missing."""
        invalid_structure = {
            'pages': []
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertIn("Missing required field: metadata", errors)

    def test_empty_pages_list(self):
        """Test validation fails when pages list is empty."""
        invalid_structure = {
            'pages': [],
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertIn("'pages' list is empty", errors)

    def test_invalid_pages_type(self):
        """Test validation fails when pages is not a list."""
        invalid_structure = {
            'pages': 'not a list',
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertTrue(any("'pages' must be a list" in err for err in errors))

    def test_invalid_metadata_type(self):
        """Test validation fails when metadata is not a dict."""
        invalid_structure = {
            'pages': [{'title': 'Test', 'content': 'Test'}],
            'metadata': 'not a dict'
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertTrue(any("'metadata' must be a dict" in err for err in errors))

    def test_page_missing_title(self):
        """Test validation fails when page is missing title."""
        invalid_structure = {
            'pages': [
                {
                    'content': 'Content without title'
                }
            ],
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertTrue(any("missing required field 'title'" in err for err in errors))

    def test_page_missing_content(self):
        """Test validation fails when page is missing content."""
        invalid_structure = {
            'pages': [
                {
                    'title': 'Title without content'
                }
            ],
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertTrue(any("missing required field 'content'" in err for err in errors))

    def test_page_empty_title(self):
        """Test validation fails when page title is empty."""
        invalid_structure = {
            'pages': [
                {
                    'title': '   ',  # Empty after strip
                    'content': 'Some content'
                }
            ],
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertTrue(any("'title' cannot be empty" in err for err in errors))

    def test_page_invalid_type(self):
        """Test validation fails when page is not a dict."""
        invalid_structure = {
            'pages': [
                'not a dict'
            ],
            'metadata': {}
        }

        is_valid, errors = WikiStructureValidator.validate_structure(invalid_structure)

        self.assertFalse(is_valid)
        self.assertTrue(any("must be a dict" in err for err in errors))

    def test_validate_and_raise_success(self):
        """Test validate_and_raise with valid structure."""
        valid_structure = {
            'pages': [
                {
                    'title': 'Test',
                    'content': 'Content'
                }
            ],
            'metadata': {}
        }

        # Should not raise
        WikiStructureValidator.validate_and_raise(valid_structure)

    def test_validate_and_raise_failure(self):
        """Test validate_and_raise with invalid structure."""
        invalid_structure = {
            'pages': []
        }

        with self.assertRaises(WikiValidationError):
            WikiStructureValidator.validate_and_raise(invalid_structure)

    def test_validate_single_page_success(self):
        """Test validation of single page."""
        valid_page = {
            'title': 'Test Page',
            'content': 'Test content',
            'description': 'A test page',
            'relevant_files': ['file1.py', 'file2.py']
        }

        is_valid, errors = WikiStructureValidator.validate_page(valid_page)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_single_page_failure(self):
        """Test validation of invalid page."""
        invalid_page = {
            'title': 'Test'
            # Missing content
        }

        is_valid, errors = WikiStructureValidator.validate_page(invalid_page)

        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

    def test_sanitize_page(self):
        """Test page sanitization."""
        dirty_page = {
            'title': '  Test Page  ',
            'content': '  Content  ',
            'description': '  Description  ',
            'relevant_files': ['file1.py'],
            'extra_field': 'should be ignored'
        }

        sanitized = WikiStructureValidator.sanitize_page(dirty_page)

        # Check required fields are cleaned
        self.assertEqual(sanitized['title'], 'Test Page')
        self.assertEqual(sanitized['content'], 'Content')
        self.assertEqual(sanitized['description'], 'Description')

        # Check optional fields are preserved
        self.assertEqual(sanitized['relevant_files'], ['file1.py'])

        # Check extra field is not included
        self.assertNotIn('extra_field', sanitized)

    def test_sanitize_page_missing_fields(self):
        """Test sanitization adds default values for missing fields."""
        minimal_page = {}

        sanitized = WikiStructureValidator.sanitize_page(minimal_page)

        # Should have default title and empty content
        self.assertEqual(sanitized['title'], 'Untitled Page')
        self.assertEqual(sanitized['content'], '')

    def test_sanitize_page_invalid_relevant_files(self):
        """Test sanitization removes invalid relevant_files."""
        page_with_invalid_files = {
            'title': 'Test',
            'content': 'Content',
            'relevant_files': 'not a list'  # Invalid type
        }

        sanitized = WikiStructureValidator.sanitize_page(page_with_invalid_files)

        # Invalid relevant_files should not be included
        self.assertNotIn('relevant_files', sanitized)


if __name__ == '__main__':
    unittest.main()
