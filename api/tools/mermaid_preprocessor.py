"""
Mermaid Diagram Preprocessor

Preprocesses Mermaid diagram syntax to fix common AI-generated errors.
This ensures diagrams render correctly in the frontend without requiring
extensive client-side cleanup.
"""

import re
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class MermaidPreprocessor:
    """
    Preprocesses Mermaid diagram syntax to fix common errors.

    Handles issues commonly found in AI-generated Mermaid code:
    - Markdown links and references
    - Comma syntax errors
    - Bracket issues
    - Invalid characters
    """

    # Common error patterns
    ERROR_PATTERNS = {
        'markdown_links': r'\[([^\]]+)\]\([^\)]+\)',
        'sources_references': r'Sources?:\s*.*$',
        'trailing_commas': r',\s*$',
        'leading_commas': r'^\s*,',
        'bracket_comma': r',\s*\[',
        'isolated_brackets': r'^\s*\[[^\]]*$',
    }

    @classmethod
    def preprocess(cls, mermaid_code: str, aggressive: bool = False) -> str:
        """
        Preprocess Mermaid diagram code to fix syntax errors.

        Args:
            mermaid_code: Raw Mermaid diagram code
            aggressive: If True, apply more aggressive cleaning (may lose some info)

        Returns:
            Cleaned Mermaid code

        Example:
            >>> code = "graph TD\\n    A[Start] , [Error]"
            >>> clean = MermaidPreprocessor.preprocess(code)
            >>> "Error" not in clean
            True
        """
        if not mermaid_code or not mermaid_code.strip():
            return ""

        logger.debug(f"Preprocessing Mermaid code ({len(mermaid_code)} chars)")

        cleaned = mermaid_code

        # Step 1: Remove Markdown links and references
        cleaned = cls._remove_markdown_elements(cleaned)

        # Step 2: Fix sequence diagram syntax errors
        cleaned = cls._fix_sequence_diagram_syntax(cleaned)

        # Step 3: Fix arrow syntax errors
        cleaned = cls._fix_arrow_syntax(cleaned)

        # Step 4: Fix flowchart and class diagram errors
        cleaned = cls._fix_diagram_common_errors(cleaned)

        # Step 5: Clean up brackets
        cleaned = cls._clean_brackets(cleaned)

        # Step 6: Remove invalid commas
        cleaned = cls._remove_invalid_commas(cleaned)

        # Step 7: Clean up whitespace and formatting
        cleaned = cls._clean_formatting(cleaned)

        # Step 8: Aggressive cleanup if requested
        if aggressive:
            cleaned = cls._aggressive_cleanup(cleaned)

        logger.debug(f"Preprocessing complete ({len(cleaned)} chars)")

        return cleaned.strip()

    @classmethod
    def _remove_markdown_elements(cls, code: str) -> str:
        """Remove Markdown links, references, and formatting"""
        cleaned = code

        # Remove Sources: [filename]() format
        cleaned = re.sub(r'Sources?:\s*\[[^\]]+\]\([^\)]*\)', '', cleaned, flags=re.IGNORECASE)

        # Remove standalone Markdown links (keep link text)
        # Note: Use [^\)]* instead of [^\)]+ to match empty parentheses like [file.py]()
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', cleaned)

        # Remove Chinese/English bracket references
        cleaned = re.sub(r'[（(]Sources?:[^）)]+[）)]', '', cleaned)

        # Remove other reference formats
        cleaned = re.sub(r'^\s*Sources?:\s*.*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        cleaned = re.sub(r'\[Sources?:\s*[^\]]+\]', '', cleaned, flags=re.IGNORECASE)

        # Remove Markdown formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)  # Italic
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)  # Inline code

        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)

        return cleaned

    @classmethod
    def _fix_sequence_diagram_syntax(cls, code: str) -> str:
        """Fix sequence diagram specific syntax errors"""
        cleaned = code

        # Fix: autonumber followed by comma and bracket
        cleaned = re.sub(r'(\s*autonumber\s*),\s*\[.*$', r'\1', cleaned, flags=re.MULTILINE)

        # Fix: autonumber followed by comma and anything
        cleaned = re.sub(r'(\s*autonumber\s*),.*$', r'\1', cleaned, flags=re.MULTILINE)

        # Fix: participant followed by comma
        cleaned = re.sub(
            r'(participant\s+[A-Za-z0-9_]+(?:\s+as\s+[A-Za-z0-9_]+)?)\s*,\s*\[.*$',
            r'\1',
            cleaned,
            flags=re.MULTILINE
        )

        cleaned = re.sub(
            r'(participant\s+[A-Za-z0-9_]+(?:\s+as\s+[A-Za-z0-9_]+)?)\s*,.*$',
            r'\1',
            cleaned,
            flags=re.MULTILINE
        )

        # Fix: arrow followed by comma and bracket
        cleaned = re.sub(r'(->>[\+\-]?[^:]*):([^,]*),\s*\[[^\]]*\](.*)$', r'\1:\2', cleaned, flags=re.MULTILINE)

        # Fix: arrow with comma after colon
        cleaned = re.sub(r'(->>[\+\-]?\s*\w+\s*:\s*[^,\n]*),\s*\[[^\]]*\]', r'\1', cleaned)

        # Fix: keywords followed by comma and bracket
        keywords = ['activate', 'deactivate', 'loop', 'alt', 'opt', 'par', 'and', 'else', 'end',
                   'box', 'note', 'rect', 'critical', 'break']
        for keyword in keywords:
            cleaned = re.sub(
                rf'({keyword})\s*,\s*\[.*$',
                r'\1',
                cleaned,
                flags=re.MULTILINE | re.IGNORECASE
            )
            cleaned = re.sub(
                rf'({keyword})\s*,.*$',
                r'\1',
                cleaned,
                flags=re.MULTILINE | re.IGNORECASE
            )

        return cleaned

    @classmethod
    def _fix_arrow_syntax(cls, code: str) -> str:
        """Fix arrow syntax errors"""
        cleaned = code

        # Fix: comma between participant name and arrow
        cleaned = re.sub(r'([A-Za-z0-9_]+)\s*,\s*(->>?[\+\-]?)', r'\1\2', cleaned)

        # Fix: comma before various arrow types
        arrow_types = ['->', '--', '->>', '-->>', '->x', '-->>x', '-)', '--)']
        for arrow in arrow_types:
            escaped_arrow = re.escape(arrow)
            cleaned = re.sub(
                rf'([A-Za-z0-9_]+)\s*,\s*({escaped_arrow})',
                r'\1\2',
                cleaned
            )

        # Fix: multiple commas in arrow labels
        cleaned = re.sub(
            r'(->>?[\+\-]?\s*\w+\s*:\s*[^:,\n]+),\s*([^:\n]+)',
            r'\1 \2',
            cleaned
        )

        return cleaned

    @classmethod
    def _fix_diagram_common_errors(cls, code: str) -> str:
        """Fix common errors in flowcharts, class diagrams, ER diagrams"""
        cleaned = code

        # Fix: flowchart node definition with comma
        cleaned = re.sub(r'([A-Za-z0-9_]+)\s*\[([^\]]*)\]\s*,', r'\1[\2]', cleaned)

        # Fix: class diagram relationship with comma
        cleaned = re.sub(
            r'([A-Za-z0-9_]+)\s*(-->|<\|--|<\|\.\.|--|\*--|o--)\s*([A-Za-z0-9_]+)\s*,',
            r'\1\2\3',
            cleaned
        )

        # Fix: ER diagram entity with comma
        cleaned = re.sub(r'([A-Za-z0-9_]+)\s*\{\s*([^}]*)\s*\}\s*,', r'\1{\2}', cleaned)

        return cleaned

    @classmethod
    def _clean_brackets(cls, code: str) -> str:
        """Clean up bracket-related issues"""
        cleaned = code

        # Remove isolated right brackets
        cleaned = re.sub(r'^\s*[^\s\w-]+\].*', '', cleaned, flags=re.MULTILINE)

        # Remove lines with isolated brackets
        cleaned = re.sub(r'^\s*\w+\]\s+.*', '', cleaned, flags=re.MULTILINE)

        # Remove isolated left brackets
        cleaned = re.sub(r'^\s*\[[^\]]*$', '', cleaned, flags=re.MULTILINE)

        # Remove lines starting with comma and bracket
        cleaned = re.sub(r'^\s*,?\s*\[.*?\].*$', '', cleaned, flags=re.MULTILINE)

        # Remove isolated brackets with no valid content before them
        cleaned = re.sub(r',\s*\[[^\]]+\]', '', cleaned)

        # Remove Markdown links inside brackets
        cleaned = re.sub(r'\[([^\]]*)\[([^\]]+)\]\([^\)]+\)([^\]]*)\]', r'[\1\2\3]', cleaned)

        return cleaned

    @classmethod
    def _remove_invalid_commas(cls, code: str) -> str:
        """Remove invalid commas"""
        cleaned = code

        # Remove trailing commas
        cleaned = re.sub(r',\s*$', '', cleaned, flags=re.MULTILINE)

        # Remove leading commas
        cleaned = re.sub(r'^\s*,', '', cleaned, flags=re.MULTILINE)

        # Remove commas after keywords at end of line
        keywords = ['autonumber', 'activate', 'deactivate', 'end', 'else', 'and']
        for keyword in keywords:
            cleaned = re.sub(
                rf'({keyword})\s*,(\s*$)',
                r'\1\2',
                cleaned,
                flags=re.MULTILINE | re.IGNORECASE
            )

        return cleaned

    @classmethod
    def _clean_formatting(cls, code: str) -> str:
        """Clean up whitespace and formatting"""
        cleaned = code

        # Normalize whitespace (multiple spaces to single space, preserve newlines)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)

        # Remove trailing whitespace
        cleaned = re.sub(r'[ \t]+$', '', cleaned, flags=re.MULTILINE)

        # Remove empty lines or whitespace-only lines
        cleaned = re.sub(r'^\s*$', '', cleaned, flags=re.MULTILINE)

        # Clean up multiple consecutive empty lines (max 2)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        # Remove leading empty lines
        cleaned = re.sub(r'^\n+', '', cleaned)

        # Remove trailing empty lines
        cleaned = re.sub(r'\n+$', '', cleaned)

        return cleaned

    @classmethod
    def _aggressive_cleanup(cls, code: str) -> str:
        """
        Aggressive cleanup - may remove some valid content.
        Use only when normal preprocessing fails.
        """
        cleaned = code

        # Remove all bracket content (might be erroneous labels)
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)

        # Remove all isolated commas
        cleaned = re.sub(r'\s*,\s*', ' ', cleaned)

        # Normalize all whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\n\s+', '\n', cleaned)

        # Clean up multiple empty lines
        cleaned = re.sub(r'\n{2,}', '\n', cleaned)

        return cleaned.strip()

    @classmethod
    def extract_and_process_mermaid_blocks(cls, markdown_content: str) -> str:
        """
        Extract Mermaid code blocks from Markdown and preprocess them.

        Args:
            markdown_content: Markdown content containing Mermaid blocks

        Returns:
            Markdown content with preprocessed Mermaid blocks

        Example:
            >>> md = "Some text\\n```mermaid\\ngraph TD\\n    A , [Error]\\n```\\nMore text"
            >>> processed = MermaidPreprocessor.extract_and_process_mermaid_blocks(md)
            >>> ", [Error]" not in processed
            True
        """
        if not markdown_content:
            return ""

        # Pattern to match mermaid code blocks
        pattern = r'```mermaid\n(.*?)```'

        def preprocess_block(match):
            """Preprocess a single mermaid block"""
            mermaid_code = match.group(1)
            processed_code = cls.preprocess(mermaid_code)
            return f"```mermaid\n{processed_code}\n```"

        # Replace all mermaid blocks with preprocessed versions
        processed_content = re.sub(
            pattern,
            preprocess_block,
            markdown_content,
            flags=re.DOTALL
        )

        return processed_content

    @classmethod
    def validate_syntax(cls, mermaid_code: str) -> Tuple[bool, List[str]]:
        """
        Validate Mermaid syntax and return errors.

        Args:
            mermaid_code: Mermaid diagram code

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            >>> code = "graph TD\\n    A[Start]"
            >>> valid, errors = MermaidPreprocessor.validate_syntax(code)
            >>> valid
            True
        """
        errors = []

        if not mermaid_code or not mermaid_code.strip():
            errors.append("Empty Mermaid code")
            return False, errors

        # Check for common error patterns
        lines = mermaid_code.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for trailing commas
            if re.search(r',\s*$', line):
                errors.append(f"Line {i}: Trailing comma")

            # Check for comma before bracket
            if re.search(r',\s*\[', line):
                errors.append(f"Line {i}: Comma before bracket")

            # Check for isolated brackets
            if re.search(r'^\s*\[[^\]]*$', line):
                errors.append(f"Line {i}: Isolated left bracket")

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def get_statistics(cls, mermaid_code: str) -> Dict[str, Any]:
        """
        Get statistics about Mermaid code.

        Args:
            mermaid_code: Mermaid diagram code

        Returns:
            Dictionary with statistics

        Example:
            >>> code = "graph TD\\n    A --> B\\n    B --> C"
            >>> stats = MermaidPreprocessor.get_statistics(code)
            >>> stats['line_count']
            3
        """
        if not mermaid_code:
            return {
                'line_count': 0,
                'char_count': 0,
                'diagram_type': None,
                'has_errors': False
            }

        lines = mermaid_code.strip().split('\n')
        first_line = lines[0].strip() if lines else ''

        # Detect diagram type
        diagram_type = None
        if first_line.startswith('graph'):
            diagram_type = 'flowchart'
        elif first_line.startswith('sequenceDiagram'):
            diagram_type = 'sequence'
        elif first_line.startswith('classDiagram'):
            diagram_type = 'class'
        elif first_line.startswith('erDiagram'):
            diagram_type = 'er'
        elif first_line.startswith('gantt'):
            diagram_type = 'gantt'
        elif first_line.startswith('pie'):
            diagram_type = 'pie'

        # Check for errors
        is_valid, errors = cls.validate_syntax(mermaid_code)

        return {
            'line_count': len(lines),
            'char_count': len(mermaid_code),
            'diagram_type': diagram_type,
            'has_errors': not is_valid,
            'error_count': len(errors),
            'errors': errors
        }
