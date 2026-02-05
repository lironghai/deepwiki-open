"""
Wiki Structure Validator

Validates wiki structure and page data to ensure consistency and correctness.
"""

import logging
from typing import Dict, List, Any, Tuple

from api.tools.wiki_exceptions import WikiValidationError

logger = logging.getLogger(__name__)


class WikiStructureValidator:
    """
    Validator for wiki structure and pages.

    Ensures that wiki data conforms to expected schema and constraints.
    """

    # Required fields for wiki structure
    REQUIRED_STRUCTURE_FIELDS = ['pages', 'metadata']

    # Required fields for wiki page
    REQUIRED_PAGE_FIELDS = ['title', 'content']

    # Optional page fields
    OPTIONAL_PAGE_FIELDS = [
        'description',
        'relevant_files',
        'index',
        'codemap_used',
        'modules_referenced'
    ]

    @classmethod
    def validate_structure(cls, wiki_structure: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate wiki structure.

        Args:
            wiki_structure: Wiki structure dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            is_valid, errors = WikiStructureValidator.validate_structure(structure)
            if not is_valid:
                logger.error(f"Validation errors: {errors}")
        """
        errors = []

        # Check if input is a dictionary
        if not isinstance(wiki_structure, dict):
            errors.append(f"Wiki structure must be a dict, got {type(wiki_structure)}")
            return False, errors

        # Check required fields
        for field in cls.REQUIRED_STRUCTURE_FIELDS:
            if field not in wiki_structure:
                errors.append(f"Missing required field: {field}")

        # Validate pages field
        if 'pages' in wiki_structure:
            pages = wiki_structure['pages']

            if not isinstance(pages, list):
                errors.append(f"'pages' must be a list, got {type(pages)}")
            elif len(pages) == 0:
                errors.append("'pages' list is empty")
            else:
                # Validate each page
                for i, page in enumerate(pages):
                    page_errors = cls._validate_page(page, i)
                    errors.extend(page_errors)

        # Validate metadata field
        if 'metadata' in wiki_structure:
            metadata = wiki_structure['metadata']

            if not isinstance(metadata, dict):
                errors.append(f"'metadata' must be a dict, got {type(metadata)}")

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def _validate_page(cls, page: Any, index: int) -> List[str]:
        """
        Validate a single page.

        Args:
            page: Page data to validate
            index: Page index (for error messages)

        Returns:
            List of error messages
        """
        errors = []
        prefix = f"Page {index}"

        # Check if page is a dictionary
        if not isinstance(page, dict):
            errors.append(f"{prefix}: must be a dict, got {type(page)}")
            return errors

        # Check required fields
        for field in cls.REQUIRED_PAGE_FIELDS:
            if field not in page:
                errors.append(f"{prefix}: missing required field '{field}'")

        # Validate title
        if 'title' in page:
            title = page['title']
            if not isinstance(title, str):
                errors.append(f"{prefix}: 'title' must be a string, got {type(title)}")
            elif len(title.strip()) == 0:
                errors.append(f"{prefix}: 'title' cannot be empty")

        # Validate content
        if 'content' in page:
            content = page['content']
            if not isinstance(content, str):
                errors.append(f"{prefix}: 'content' must be a string, got {type(content)}")

        # Validate relevant_files (if present)
        if 'relevant_files' in page:
            relevant_files = page['relevant_files']
            if not isinstance(relevant_files, list):
                errors.append(f"{prefix}: 'relevant_files' must be a list, got {type(relevant_files)}")

        return errors

    @classmethod
    def validate_and_raise(cls, wiki_structure: Dict[str, Any]):
        """
        Validate wiki structure and raise exception if invalid.

        Args:
            wiki_structure: Wiki structure to validate

        Raises:
            WikiValidationError: If validation fails
        """
        is_valid, errors = cls.validate_structure(wiki_structure)

        if not is_valid:
            error_message = "Wiki structure validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            logger.error(error_message)
            raise WikiValidationError(error_message)

        logger.debug("Wiki structure validation passed")

    @classmethod
    def validate_page(cls, page: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single page.

        Args:
            page: Page data to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = cls._validate_page(page, 0)
        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def validate_page_and_raise(cls, page: Dict[str, Any]):
        """
        Validate a page and raise exception if invalid.

        Args:
            page: Page data to validate

        Raises:
            WikiValidationError: If validation fails
        """
        is_valid, errors = cls.validate_page(page)

        if not is_valid:
            error_message = "Page validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            logger.error(error_message)
            raise WikiValidationError(error_message)

        logger.debug("Page validation passed")

    @classmethod
    def sanitize_page(cls, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize page data by ensuring required fields and cleaning up invalid data.

        This is useful for handling legacy or partially-formed page data.

        Args:
            page: Page data to sanitize

        Returns:
            Sanitized page data
        """
        sanitized = {}

        # Ensure required fields
        sanitized['title'] = page.get('title', 'Untitled Page').strip()
        sanitized['content'] = page.get('content', '').strip()

        # Copy optional fields if valid
        if 'description' in page and isinstance(page['description'], str):
            sanitized['description'] = page['description'].strip()

        if 'relevant_files' in page and isinstance(page['relevant_files'], list):
            sanitized['relevant_files'] = page['relevant_files']

        if 'index' in page and isinstance(page['index'], int):
            sanitized['index'] = page['index']

        if 'codemap_used' in page and isinstance(page['codemap_used'], bool):
            sanitized['codemap_used'] = page['codemap_used']

        if 'modules_referenced' in page and isinstance(page['modules_referenced'], int):
            sanitized['modules_referenced'] = page['modules_referenced']

        return sanitized
