"""
Parallel Wiki Page Generator

Implements parallel wiki page generation using asyncio + ThreadPoolExecutor.
Integrates with codemap for enhanced content generation.
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from api.tools.codemap_cache import codemap_cache
from api.tools.wiki_resources import codemap_context
from api.tools.wiki_exceptions import WikiGenerationError

logger = logging.getLogger(__name__)


@dataclass
class PageGenerationResult:
    """Result of page generation"""
    page_index: int
    title: str
    content: str
    success: bool
    error: Optional[str] = None
    codemap_used: bool = False
    modules_referenced: int = 0
    generation_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ParallelWikiGenerator:
    """
    Parallel wiki page generator

    Uses asyncio + ThreadPoolExecutor for true parallel generation.
    Integrates with codemap cache for enhanced content.
    """

    def __init__(
        self,
        llm_service: Optional[Any] = None,
        max_workers: int = 5,
        enable_codemap: bool = True
    ):
        """
        Initialize parallel generator

        Args:
            llm_service: LLM service instance for content generation
            max_workers: Maximum number of concurrent workers
            enable_codemap: Whether to use codemap enhancement
        """
        self.llm_service = llm_service
        self.max_workers = max_workers
        self.enable_codemap = enable_codemap

        logger.info(f"Initialized ParallelWikiGenerator with {max_workers} workers")

    async def generate_pages_parallel(
        self,
        pages: List[Dict[str, Any]],
        repo_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[PageGenerationResult]:
        """
        Generate multiple wiki pages in parallel

        Args:
            pages: List of page information dictionaries
            repo_path: Repository path
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            List of PageGenerationResult objects
        """
        if not pages:
            logger.warning("No pages to generate")
            return []

        logger.info(f"Starting parallel generation for {len(pages)} pages")
        start_time = time.time()

        # Pre-load codemap to cache (ensures all workers can access it)
        if self.enable_codemap:
            codemap = codemap_cache.get(repo_path)
            if codemap is None:
                logger.warning("Codemap not available, generating without it")
            else:
                logger.info(f"Codemap loaded: {len(codemap.get('nodes', []))} nodes")

        # Create tasks for all pages
        tasks = []
        for i, page in enumerate(pages):
            task = self._generate_single_page(page, repo_path, i)
            tasks.append(task)

        # Execute in parallel with progress tracking
        results = []
        completed = 0

        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                completed += 1

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(completed, len(pages))

                logger.info(f"Progress: {completed}/{len(pages)} pages completed")

            except Exception as e:
                logger.error(f"Unexpected error in page generation: {e}")
                # Create error result
                error_result = PageGenerationResult(
                    page_index=completed,
                    title="Error",
                    content="",
                    success=False,
                    error=str(e)
                )
                results.append(error_result)
                completed += 1

        # Sort results by page_index to maintain order
        results.sort(key=lambda x: x.page_index)

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = time.time() - start_time

        logger.info(
            f"Parallel generation complete: {successful} success, {failed} failed, "
            f"total time: {total_time:.2f}s"
        )

        return results

    async def _generate_single_page(
        self,
        page: Dict[str, Any],
        repo_path: str,
        page_index: int
    ) -> PageGenerationResult:
        """
        Generate a single page (runs in independent worker)

        Args:
            page: Page information
            repo_path: Repository path
            page_index: Page index

        Returns:
            PageGenerationResult
        """
        start_time = time.time()
        title = page.get('title', f'Page {page_index}')

        logger.info(f"Generating page {page_index}: {title}")

        try:
            # Use codemap context for proper resource management
            if self.enable_codemap:
                
                # Fetch GitNexus GraphRAG Context
                graph_context_text = ""
                try:
                    from api.tools.graph_retriever import GraphRetriever
                    retriever = GraphRetriever(repo_path)
                    
                    query_text = f"{title} {page.get('description', '')}"
                    graph_result = await retriever.query_context(query_text)
                    if graph_result:
                        graph_context_text = f"\n## Deep Graph Context (from GitNexus)\n{graph_result}\n"
                except Exception as e:
                    logger.warning(f"Failed to fetch GraphRAG context for page {title}: {e}")
                    
                with codemap_context(repo_path) as codemap:
                    # We pass the graph_context_text to be appended to the prompt
                    content, modules = await self._generate_with_codemap(
                        page,
                        codemap,
                        page_index,
                        graph_context_text
                    )
                    codemap_used = bool(codemap)
                    modules_referenced = len(modules)
            else:
                content = await self._generate_without_codemap(page, page_index)
                codemap_used = False
                modules_referenced = 0

            generation_time = (time.time() - start_time) * 1000

            return PageGenerationResult(
                page_index=page_index,
                title=title,
                content=content,
                success=True,
                codemap_used=codemap_used,
                modules_referenced=modules_referenced,
                generation_time_ms=generation_time,
                metadata=page
            )

        except Exception as e:
            logger.error(f"Error generating page {page_index} ({title}): {e}")
            generation_time = (time.time() - start_time) * 1000

            return PageGenerationResult(
                page_index=page_index,
                title=title,
                content="",
                success=False,
                error=str(e),
                generation_time_ms=generation_time,
                metadata=page
            )

    async def _generate_with_codemap(
        self,
        page: Dict[str, Any],
        codemap: Dict[str, Any],
        page_index: int,
        graph_context_text: str = ""
    ) -> tuple[str, List[Dict]]:
        """
        Generate content with codemap enhancement

        Args:
            page: Page information
            codemap: Codemap data
            page_index: Page index
            graph_context_text: Additional context from Graph Retriever

        Returns:
            Tuple of (content, relevant_modules)
        """
        # Extract relevant modules from codemap
        relevant_modules = self._extract_relevant_modules(page, codemap)

        logger.info(
            f"Page {page_index}: Found {len(relevant_modules)} relevant modules"
        )

        # Generate content with codemap context
        content = await self._generate_content_with_codemap(
            page,
            relevant_modules,
            codemap,
            graph_context_text
        )

        return content, relevant_modules

    async def _generate_without_codemap(
        self,
        page: Dict[str, Any],
        page_index: int
    ) -> str:
        """
        Generate content without codemap

        Args:
            page: Page information
            page_index: Page index

        Returns:
            Generated content
        """
        logger.info(f"Page {page_index}: Generating without codemap")

        # Build basic prompt
        prompt = self._build_basic_prompt(page)

        # Generate content
        if self.llm_service:
            content = await self._call_llm_service(prompt)
        else:
            # Fallback: use template content
            content = self._generate_template_content(page)

        return content

    def _extract_relevant_modules(
        self,
        page: Dict[str, Any],
        codemap: Dict[str, Any]
    ) -> List[Dict]:
        """
        Extract modules from codemap relevant to the page

        Args:
            page: Page information
            codemap: Codemap data

        Returns:
            List of relevant module dictionaries
        """
        if not codemap:
            return []

        relevant_files = page.get('relevant_files', [])
        if not relevant_files:
            return []

        relevant_modules = []

        # Match modules by file path
        for module in codemap.get('key_modules', []):
            module_file = module.get('file', '')
            if any(rf in module_file for rf in relevant_files):
                relevant_modules.append(module)

        # Also check nodes for matching files
        for node in codemap.get('nodes', []):
            node_path = node.get('path', '')
            if any(rf in node_path for rf in relevant_files):
                # Convert node to module-like structure
                relevant_modules.append({
                    'name': node.get('name', ''),
                    'type': node.get('type', ''),
                    'file': node_path,
                    'description': node.get('summary', '')
                })

        return relevant_modules

    async def _generate_content_with_codemap(
        self,
        page: Dict[str, Any],
        modules: List[Dict],
        codemap: Dict[str, Any],
        graph_context_text: str = ""
    ) -> str:
        """
        Generate content using codemap information

        Args:
            page: Page information
            modules: Relevant modules
            codemap: Full codemap data
            graph_context_text: Additional context from GitNexus graph

        Returns:
            Generated content
        """
        # Build enhanced prompt with codemap context
        prompt = self._build_enhanced_prompt(page, modules, codemap, graph_context_text)

        # Call LLM service
        if self.llm_service:
            content = await self._call_llm_service(prompt)
        else:
            # Fallback: use template with module info
            content = self._generate_template_content_with_modules(page, modules)

        return content

    def _build_enhanced_prompt(
        self,
        page: Dict[str, Any],
        modules: List[Dict],
        codemap: Dict[str, Any],
        graph_context_text: str = ""
    ) -> str:
        """
        Build enhanced prompt with codemap context

        Args:
            page: Page information
            modules: Relevant modules
            codemap: Codemap data
            graph_context_text: Additional context from GitNexus graph

        Returns:
            Enhanced prompt string
        """
        title = page.get('title', 'Untitled')
        description = page.get('description', '')

        prompt = f"# Generate Wiki Page: {title}\n\n"

        if description:
            prompt += f"## Description\n{description}\n\n"

        if graph_context_text:
            prompt += f"{graph_context_text}\n\n"

        # Add module context
        if modules:
            prompt += "## Relevant Code Modules\n\n"
            for module in modules[:10]:  # Limit to top 10
                module_name = module.get('name', 'Unknown')
                module_type = module.get('type', 'unknown')
                module_desc = module.get('description', 'No description')

                prompt += f"- **{module_name}** ({module_type}): {module_desc}\n"

            prompt += "\n"

        # Add architecture context if available
        if codemap and codemap.get('architecture_layers'):
            prompt += "## Architecture Context\n\n"
            # architecture_layers is a dict: {layer_name: [class_names]}
            architecture_layers = codemap.get('architecture_layers', {})
            if isinstance(architecture_layers, dict):
                for layer_name, classes in list(architecture_layers.items())[:5]:
                    if classes:
                        prompt += f"- **{layer_name}**: {', '.join(classes[:10])}{'...' if len(classes) > 10 else ''}\n"
            elif isinstance(architecture_layers, list):
                # Handle legacy format (list of dicts)
                for layer in architecture_layers[:5]:
                    layer_name = layer.get('name', 'Unknown') if isinstance(layer, dict) else str(layer)
                    prompt += f"- {layer_name}\n"

            prompt += "\n"

        prompt += "## Instructions\n"
        prompt += "Generate comprehensive wiki page content in Markdown format.\n"
        prompt += "Include code examples, explanations, and relevant details.\n"

        return prompt

    def _build_basic_prompt(self, page: Dict[str, Any]) -> str:
        """Build basic prompt without codemap"""
        title = page.get('title', 'Untitled')
        description = page.get('description', '')

        prompt = f"# Generate Wiki Page: {title}\n\n"

        if description:
            prompt += f"## Description\n{description}\n\n"

        prompt += "## Instructions\n"
        prompt += "Generate wiki page content in Markdown format.\n"

        return prompt

    async def _call_llm_service(self, prompt: str) -> str:
        """
        Call LLM service to generate content

        Args:
            prompt: Prompt string

        Returns:
            Generated content

        Raises:
            WikiGenerationError: If LLM call fails
        """
        try:
            # Check if llm_service has async generate method
            if hasattr(self.llm_service, 'generate'):
                if asyncio.iscoroutinefunction(self.llm_service.generate):
                    content = await self.llm_service.generate(prompt)
                else:
                    # Wrap sync call in executor
                    loop = asyncio.get_event_loop()
                    content = await loop.run_in_executor(
                        None,
                        self.llm_service.generate,
                        prompt
                    )
            else:
                raise WikiGenerationError("LLM service has no generate method")

            return content

        except Exception as e:
            logger.error(f"LLM service call failed: {e}")
            raise WikiGenerationError(f"LLM generation failed: {e}")

    def _generate_template_content(self, page: Dict[str, Any]) -> str:
        """Generate template content as fallback"""
        title = page.get('title', 'Untitled')
        description = page.get('description', 'No description provided')

        content = f"# {title}\n\n"
        content += f"{description}\n\n"
        content += "## Overview\n\n"
        content += "This section provides an overview of the topic.\n\n"
        content += "## Details\n\n"
        content += "Detailed information will be added here.\n"

        return content

    def _generate_template_content_with_modules(
        self,
        page: Dict[str, Any],
        modules: List[Dict]
    ) -> str:
        """Generate template content with module information"""
        content = self._generate_template_content(page)

        if modules:
            content += "\n## Related Modules\n\n"
            for module in modules[:10]:
                module_name = module.get('name', 'Unknown')
                module_type = module.get('type', 'unknown')
                content += f"- **{module_name}** ({module_type})\n"

        return content

    def get_statistics(self, results: List[PageGenerationResult]) -> Dict[str, Any]:
        """
        Calculate generation statistics

        Args:
            results: List of generation results

        Returns:
            Statistics dictionary
        """
        if not results:
            return {
                'total_pages': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'avg_generation_time_ms': 0.0,
                'codemap_usage_rate': 0.0
            }

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        avg_time = sum(r.generation_time_ms for r in results) / len(results)
        codemap_used = sum(1 for r in results if r.codemap_used)

        return {
            'total_pages': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': successful / len(results) * 100,
            'avg_generation_time_ms': avg_time,
            'codemap_usage_rate': codemap_used / len(results) * 100,
            'total_modules_referenced': sum(r.modules_referenced for r in results)
        }
