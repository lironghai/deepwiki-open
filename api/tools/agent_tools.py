"""
Agent tools for Agentic RAG with function calling.
Defines tool schemas (OpenAI format) and execution logic for rag_search and grep_search.
"""

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TOOL_CAPABLE_PROVIDERS = {"openai", "openrouter", "azure", "dashscope"}

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": (
                "Search the repository codebase using semantic similarity. "
                "Use this when you need more context about specific concepts, classes, "
                "functions, or features that were not included in the initial context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Semantic search query describing what you're looking for",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of code snippets to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": (
                "Search for exact text patterns in the repository files using regex. "
                "Use this when you need to find specific strings, function/class/variable names, "
                "imports, or configuration values."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search for",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "File glob pattern to filter (e.g. '*.py', 'src/**/*.ts')",
                        "default": "*",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matching lines to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


def supports_tool_calling(provider: str) -> bool:
    """Check whether the given provider supports OpenAI-compatible function calling."""
    return provider in TOOL_CAPABLE_PROVIDERS


def execute_tool(
    tool_name: str,
    arguments: str,
    rag_instance: Any = None,
    repo_path: Optional[str] = None,
) -> str:
    """
    Execute a named tool with the given JSON arguments string.
    Returns the tool output as a plain-text string.
    """
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        return f"Error: Invalid JSON arguments: {arguments}"

    if tool_name == "rag_search":
        return _execute_rag_search(args, rag_instance)
    elif tool_name == "grep_search":
        return _execute_grep_search(args, repo_path)
    else:
        return f"Error: Unknown tool '{tool_name}'"


# ---------------------------------------------------------------------------
# RAG search
# ---------------------------------------------------------------------------

def _execute_rag_search(args: Dict, rag_instance: Any) -> str:
    query = args.get("query", "")
    top_k = args.get("top_k", 5)

    if not query:
        return "Error: 'query' parameter is required for rag_search"
    if not rag_instance:
        return "Error: RAG instance not available"

    try:
        retrieved = rag_instance(query)
        if not retrieved or not retrieved[0].documents:
            return "No relevant documents found for the query."

        docs = retrieved[0].documents[:top_k]
        results = []
        for i, doc in enumerate(docs):
            file_path = doc.meta_data.get("file_path", "unknown")
            content = doc.text[:2000]
            results.append(f"## Result {i + 1}: {file_path}\n{content}")

        return "\n\n---\n\n".join(results)
    except Exception as e:
        logger.error(f"Error in rag_search: {e}")
        return f"Error during RAG search: {e}"


# ---------------------------------------------------------------------------
# Grep search
# ---------------------------------------------------------------------------

def _execute_grep_search(args: Dict, repo_path: Optional[str]) -> str:
    pattern = args.get("pattern", "")
    file_glob = args.get("file_glob", "*")
    max_results = min(args.get("max_results", 20), 50)

    if not pattern:
        return "Error: 'pattern' parameter is required for grep_search"
    if not repo_path or not os.path.exists(repo_path):
        return f"Error: Repository path not available or does not exist: {repo_path}"

    try:
        return _ripgrep_search(pattern, repo_path, file_glob, max_results)
    except FileNotFoundError:
        return _python_grep(pattern, repo_path, file_glob, max_results)
    except subprocess.TimeoutExpired:
        return "Error: Search timed out. Try a more specific pattern."
    except Exception as e:
        logger.error(f"Error in grep_search: {e}")
        return f"Error during grep search: {e}"


def _ripgrep_search(
    pattern: str, repo_path: str, file_glob: str, max_results: int
) -> str:
    cmd = [
        "rg",
        "--max-count", str(max_results),
        "--no-heading",
        "--line-number",
        "--color", "never",
    ]
    if file_glob and file_glob != "*":
        cmd.extend(["--glob", file_glob])
    cmd.extend(["--", pattern, "."])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=repo_path,
    )

    if result.returncode == 0 and result.stdout.strip():
        lines = result.stdout.strip().split("\n")[:max_results]
        return "\n".join(lines)
    elif result.returncode == 1:
        return "No matches found."
    else:
        raise FileNotFoundError("ripgrep returned unexpected exit code")


def _python_grep(
    pattern: str, repo_path: str, file_glob: str, max_results: int
) -> str:
    """Fallback grep implementation using Python stdlib."""
    import fnmatch
    import glob as glob_module

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "vendor", ".tox"}

    if file_glob and file_glob != "*":
        files = glob_module.glob(
            os.path.join(repo_path, "**", file_glob), recursive=True
        )
    else:
        files = []
        for root, dirs, filenames in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for f in filenames:
                files.append(os.path.join(root, f))

    results: List[str] = []
    for filepath in files:
        if len(results) >= max_results:
            break
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                for line_num, line in enumerate(fh, 1):
                    if compiled.search(line):
                        rel_path = os.path.relpath(filepath, repo_path)
                        results.append(f"{rel_path}:{line_num}:{line.rstrip()}")
                        if len(results) >= max_results:
                            break
        except (IOError, UnicodeDecodeError):
            continue

    return "\n".join(results) if results else "No matches found."


# ---------------------------------------------------------------------------
# Hybrid retrieval: grep from user query (for pre-prompt context)
# ---------------------------------------------------------------------------

# Max lines to include from grep in initial context
GREP_PREPROMPT_MAX_RESULTS = 30


def _grep_pattern_from_query(query: str) -> Optional[str]:
    """Derive a safe grep pattern from user query (identifier or escaped prefix)."""
    if not query or not query.strip():
        return None
    q = query.strip()
    # Prefer code-like identifiers (e.g. RAG, prepare_retriever, get_model_config)
    identifiers = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{1,}", q)
    if identifiers:
        # Use longest identifier to be more specific
        return max(identifiers, key=len)
    # Fallback: escaped prefix of query (e.g. for "how does X work")
    prefix = q[:80].strip()
    return re.escape(prefix) if prefix else None


def grep_for_query(
    query: str,
    repo_path: Optional[str],
    max_results: int = GREP_PREPROMPT_MAX_RESULTS,
) -> str:
    """
    Run grep on the repo using a pattern derived from the user query.
    Returns raw output (path:line_num:content per line) or 'No matches found.' / error string.
    """
    pattern = _grep_pattern_from_query(query)
    if not pattern:
        return "No matches found."
    if not repo_path or not os.path.exists(repo_path):
        return "No matches found."
    args = {"pattern": pattern, "file_glob": "*", "max_results": max_results}
    return _execute_grep_search(args, repo_path)


def format_grep_context_for_prompt(raw_grep_output: str) -> str:
    """
    Turn raw grep output (path:line_num:content per line) into a block for context_text:
    ## Keyword matches (grep)
    ## File Path: <path>
      line_num: content
    ...
    Returns empty string if no matches or on parse error.
    """
    if not raw_grep_output or "No matches" in raw_grep_output or raw_grep_output.strip().startswith("Error"):
        return ""
    by_file: Dict[str, List[str]] = {}
    for line in raw_grep_output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Format: path:line_num:content (content may contain ':')
        # Prefer left split so content with colons is preserved
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[1].strip().isdigit():
            file_path, line_num, content = parts[0], parts[1].strip(), parts[2]
        else:
            # Windows path with colon: path is C:\...; split from right
            rest = line.rsplit(":", 1)
            if len(rest) != 2:
                continue
            path_plus_ln, content = rest[0], rest[1]
            pair = path_plus_ln.rsplit(":", 1)
            if len(pair) != 2 or not pair[1].strip().isdigit():
                continue
            file_path, line_num = pair[0], pair[1].strip()
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(f"  {line_num}: {content}")
    if not by_file:
        return ""
    parts = ["## Keyword matches (grep)\n"]
    for file_path in sorted(by_file.keys()):
        parts.append(f"## File Path: {file_path}\n")
        parts.append("\n".join(by_file[file_path]))
        parts.append("\n")
    return "\n".join(parts).strip()
