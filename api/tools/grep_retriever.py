"""
Grep-based code retrieval for hybrid RAG.

Complements FAISS semantic search with exact text matching on the cloned repository.
Supports ripgrep (rg) for speed, falls back to Python-based search.
"""

import os
import re
import subprocess
import logging
import shutil
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

EXCLUDED_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv', '.venv',
    'dist', 'build', 'target', '.next', '.nuxt', 'coverage',
    '.pytest_cache', '.idea', '.vscode', 'vendor',
}

CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp',
    '.jsx', '.tsx', '.cs', '.kt', '.swift', '.rb', '.php',
    '.md', '.txt', '.yaml', '.yml', '.json', '.xml', '.toml',
}

MAX_CONTEXT_LINES = 5
MAX_RESULTS_PER_TERM = 20
MAX_FILE_SIZE_BYTES = 512 * 1024  # skip files > 512KB


@dataclass
class GrepMatch:
    """Single grep match with surrounding context."""
    file_path: str       # relative to repo root
    line_number: int
    matched_line: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    score: float = 1.0


@dataclass
class GrepResult:
    """Aggregated grep result for a query."""
    matches: List[GrepMatch]
    matched_files: Set[str]
    search_terms: List[str]
    execution_time_ms: float = 0.0


def _has_ripgrep() -> bool:
    """Check if ripgrep (rg) is available."""
    return shutil.which('rg') is not None


def extract_search_terms(query: str) -> List[str]:
    """
    Extract meaningful search terms from a user query.

    Strategy:
    - CamelCase / PascalCase identifiers (likely class/method names)
    - snake_case identifiers
    - Quoted strings
    - Words that look like code identifiers (contain underscore or mixed case)
    - Filter out common stop words and short tokens
    """
    terms: List[str] = []

    # 1. Quoted strings
    quoted = re.findall(r'["\']([^"\']{2,})["\']', query)
    terms.extend(quoted)

    # 2. CamelCase / PascalCase identifiers (at least 2 parts)
    camel = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', query)
    terms.extend(camel)

    # 3. snake_case identifiers
    snake = re.findall(r'\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b', query)
    terms.extend(snake)

    # 4. Dot-separated identifiers (e.g., com.example.MyClass)
    dotted = re.findall(r'\b([a-zA-Z][a-zA-Z0-9]*(?:\.[a-zA-Z][a-zA-Z0-9]*){2,})\b', query)
    terms.extend(dotted)

    # 5. All-caps identifiers (constants, e.g., MAX_RETRIES)
    upper = re.findall(r'\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b', query)
    terms.extend(upper)

    # 6. Remaining tokens that look like identifiers
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
        'should', 'may', 'might', 'can', 'could', 'about', 'above', 'after',
        'before', 'between', 'from', 'into', 'through', 'during', 'with',
        'without', 'what', 'where', 'when', 'which', 'who', 'whom', 'how',
        'why', 'this', 'that', 'these', 'those', 'and', 'or', 'but', 'not',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'than', 'too', 'very', 'just', 'because', 'also',
        'class', 'function', 'method', 'file', 'code', 'project', 'module',
        'how', 'what', 'does', 'work', 'explain', 'describe', 'show',
        '的', '是', '在', '了', '和', '与', '有', '这', '那', '什么', '怎么',
        '如何', '为什么', '哪里', '哪个', '请', '帮', '我', '你', '他',
    }

    words = re.findall(r'\b\w+\b', query)
    for w in words:
        if len(w) < 3:
            continue
        if w.lower() in stop_words:
            continue
        if w not in terms:
            # Prefer words with mixed case, underscores, or that start with uppercase
            if '_' in w or (w[0].isupper() and not w.isupper()) or any(c.isupper() for c in w[1:]):
                terms.append(w)

    # Deduplicate while preserving order
    seen: Set[str] = set()
    unique_terms: List[str] = []
    for t in terms:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            unique_terms.append(t)

    return unique_terms[:8]  # cap to avoid excessive searching


def _ripgrep_search(
    repo_path: str,
    term: str,
    max_results: int = MAX_RESULTS_PER_TERM,
    context_lines: int = MAX_CONTEXT_LINES,
) -> List[GrepMatch]:
    """Search using ripgrep (rg) for maximum speed."""
    matches: List[GrepMatch] = []

    glob_excludes = []
    for d in EXCLUDED_DIRS:
        glob_excludes.extend(['--glob', f'!{d}/'])

    cmd = [
        'rg',
        '--line-number',
        '--no-heading',
        '--color', 'never',
        '--max-count', str(max_results),
        '--max-filesize', f'{MAX_FILE_SIZE_BYTES}b',
        '-C', str(context_lines),
        *glob_excludes,
        '--', term, repo_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_path,
        )
        if result.returncode not in (0, 1):  # 1 = no matches
            logger.warning(f"ripgrep exited with code {result.returncode}: {result.stderr[:200]}")
            return matches

        matches = _parse_rg_output(result.stdout, repo_path)

    except subprocess.TimeoutExpired:
        logger.warning(f"ripgrep timed out searching for '{term}'")
    except Exception as e:
        logger.error(f"ripgrep error: {e}")

    return matches


def _parse_rg_output(output: str, repo_path: str) -> List[GrepMatch]:
    """Parse ripgrep output with context lines."""
    matches: List[GrepMatch] = []
    if not output.strip():
        return matches

    current_file = None
    current_match = None
    collecting_after = False

    for line in output.split('\n'):
        if line == '--':
            # separator between match groups
            if current_match:
                matches.append(current_match)
                current_match = None
            collecting_after = False
            continue

        # rg format: file:line:content (match) or file-line-content (context)
        match_line = re.match(r'^(.+?):(\d+):(.*)$', line)
        context_line = re.match(r'^(.+?)-(\d+)-(.*)$', line)

        if match_line:
            if current_match and collecting_after:
                matches.append(current_match)
                current_match = None

            file_path = match_line.group(1)
            line_num = int(match_line.group(2))
            content = match_line.group(3)

            # Convert to relative path
            try:
                rel_path = os.path.relpath(file_path, repo_path)
            except ValueError:
                rel_path = file_path

            current_match = GrepMatch(
                file_path=rel_path,
                line_number=line_num,
                matched_line=content,
            )
            collecting_after = True

        elif context_line and current_match:
            content = context_line.group(3)
            line_num = int(context_line.group(2))

            if line_num < current_match.line_number:
                current_match.context_before.append(content)
            else:
                current_match.context_after.append(content)

    if current_match:
        matches.append(current_match)

    return matches


def _python_grep_search(
    repo_path: str,
    term: str,
    max_results: int = MAX_RESULTS_PER_TERM,
    context_lines: int = MAX_CONTEXT_LINES,
) -> List[GrepMatch]:
    """Fallback: pure Python text search."""
    matches: List[GrepMatch] = []
    term_lower = term.lower()

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in CODE_EXTENSIONS:
                continue

            fpath = os.path.join(root, fname)
            try:
                if os.path.getsize(fpath) > MAX_FILE_SIZE_BYTES:
                    continue
            except OSError:
                continue

            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception:
                continue

            rel_path = os.path.relpath(fpath, repo_path)

            for i, line in enumerate(lines):
                if term_lower in line.lower() or term in line:
                    before = [l.rstrip('\n') for l in lines[max(0, i - context_lines):i]]
                    after = [l.rstrip('\n') for l in lines[i + 1:i + 1 + context_lines]]

                    matches.append(GrepMatch(
                        file_path=rel_path,
                        line_number=i + 1,
                        matched_line=line.rstrip('\n'),
                        context_before=before,
                        context_after=after,
                    ))

                    if len(matches) >= max_results:
                        return matches

    return matches


class GrepRetriever:
    """
    Grep-based retrieval that searches the local clone of a repository.

    Designed to run alongside FAISS semantic search and produce results
    that can be merged/deduplicated with vector-retrieved documents.
    """

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._use_rg = _has_ripgrep()
        if self._use_rg:
            logger.info("GrepRetriever: using ripgrep for fast search")
        else:
            logger.info("GrepRetriever: ripgrep not found, using Python fallback")

    def search(
        self,
        query: str,
        max_total_results: int = 30,
        context_lines: int = MAX_CONTEXT_LINES,
    ) -> GrepResult:
        """
        Search the repository for terms extracted from the query.

        Returns GrepResult with matched files and snippets.
        """
        import time
        start = time.time()

        terms = extract_search_terms(query)
        if not terms:
            logger.info("GrepRetriever: no searchable terms extracted from query")
            return GrepResult(matches=[], matched_files=set(), search_terms=[],
                              execution_time_ms=0)

        logger.info(f"GrepRetriever: searching for terms: {terms}")

        all_matches: List[GrepMatch] = []
        per_term_limit = max(5, max_total_results // max(len(terms), 1))

        search_fn = _ripgrep_search if self._use_rg else _python_grep_search

        for term in terms:
            term_matches = search_fn(
                self.repo_path, term,
                max_results=per_term_limit,
                context_lines=context_lines,
            )
            all_matches.extend(term_matches)

        # Deduplicate: keep best match per (file, line)
        seen: Dict[Tuple[str, int], GrepMatch] = {}
        for m in all_matches:
            key = (m.file_path, m.line_number)
            if key not in seen:
                seen[key] = m

        unique_matches = list(seen.values())

        # Score matches: more search terms hitting a file → higher relevance
        file_term_hits: Dict[str, Set[str]] = {}
        for m in unique_matches:
            if m.file_path not in file_term_hits:
                file_term_hits[m.file_path] = set()
            for t in terms:
                if t.lower() in m.matched_line.lower():
                    file_term_hits[m.file_path].add(t.lower())

        for m in unique_matches:
            hit_count = len(file_term_hits.get(m.file_path, set()))
            m.score = hit_count / max(len(terms), 1)

        # Sort by score desc, then line number asc
        unique_matches.sort(key=lambda m: (-m.score, m.file_path, m.line_number))
        unique_matches = unique_matches[:max_total_results]

        matched_files = {m.file_path for m in unique_matches}

        elapsed = (time.time() - start) * 1000
        logger.info(
            f"GrepRetriever: found {len(unique_matches)} matches in "
            f"{len(matched_files)} files ({elapsed:.1f}ms)"
        )

        return GrepResult(
            matches=unique_matches,
            matched_files=matched_files,
            search_terms=terms,
            execution_time_ms=elapsed,
        )

    def retrieve_documents(
        self,
        query: str,
        all_documents: List,
        max_docs: int = 5,
    ) -> List:
        """
        Search via grep then map results back to existing embedded documents.

        Args:
            query: User query
            all_documents: The full list of transformed_docs from RAG
            max_docs: Maximum number of documents to return

        Returns:
            List of documents from all_documents that matched grep results,
            ordered by relevance.
        """
        grep_result = self.search(query)

        if not grep_result.matched_files:
            return []

        # Build file_path -> [docs] index from existing documents
        docs_by_file: Dict[str, List] = {}
        for doc in all_documents:
            if hasattr(doc, 'meta_data'):
                fp = doc.meta_data.get('file_path', '')
                if fp:
                    # Normalize separators
                    fp_normalized = fp.replace('\\', '/')
                    if fp_normalized not in docs_by_file:
                        docs_by_file[fp_normalized] = []
                    docs_by_file[fp_normalized].append(doc)

        # Score files by grep relevance
        file_scores: Dict[str, float] = {}
        for m in grep_result.matches:
            fp = m.file_path.replace('\\', '/')
            file_scores[fp] = max(file_scores.get(fp, 0), m.score)

        # Rank files and collect their documents
        ranked_files = sorted(file_scores.keys(), key=lambda f: -file_scores[f])

        result_docs: List = []
        seen_ids: Set[int] = set()

        for fp in ranked_files:
            if len(result_docs) >= max_docs:
                break
            for doc in docs_by_file.get(fp, []):
                doc_id = id(doc)
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    result_docs.append(doc)
                    if len(result_docs) >= max_docs:
                        break

        logger.info(
            f"GrepRetriever: mapped {len(grep_result.matched_files)} matched files "
            f"to {len(result_docs)} documents"
        )

        return result_docs
