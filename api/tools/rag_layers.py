"""
Layered RAG Retrieval System

Implements a 3-layer RAG architecture with codemap integration:
- Layer 1: Keyword matching (fast filtering)
- Layer 2: Semantic similarity + grep hybrid (precise retrieval)
- Layer 3: Context expansion (dependency-based)
"""

import os
import time
import logging
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency; will be resolved at first use.
_GrepRetriever = None

def _get_grep_retriever_class():
    global _GrepRetriever
    if _GrepRetriever is None:
        from api.tools.grep_retriever import GrepRetriever
        _GrepRetriever = GrepRetriever
    return _GrepRetriever


@dataclass
class RAGLayerResult:
    """RAG layer retrieval result"""
    documents: List
    layer_name: str
    codemap_used: bool
    execution_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class DependencyContextExpander:
    """
    Context expander based on Codemap dependency relationships
    """

    def __init__(self, codemap: Dict[str, Any], all_documents: List):
        """
        Initialize dependency expander

        Args:
            codemap: Codemap data
            all_documents: All available documents
        """
        self.codemap = codemap
        self.all_documents = all_documents

        # Build fast lookup tables for nodes and edges
        self.nodes_by_id = {node['id']: node for node in codemap.get('nodes', [])}
        self.nodes_by_name = {node['name']: node for node in codemap.get('nodes', [])}
        self.edges = codemap.get('edges', [])

        # Build file-to-document mapping
        self.docs_by_file = {}
        for doc in all_documents:
            if hasattr(doc, 'meta_data'):
                file_path = doc.meta_data.get('file_path', '')
                if file_path:
                    self.docs_by_file[file_path] = doc

    def expand(self, initial_docs: List, max_additional: int = 5) -> List:
        """
        Expand context documents

        Args:
            initial_docs: Initially retrieved documents
            max_additional: Maximum number of additional documents to add

        Returns:
            Expanded document list
        """
        # 1. Extract entities from initial documents
        mentioned_entities = self._extract_entities_from_docs(initial_docs)

        if not mentioned_entities:
            logger.info("No entities found in initial docs, skipping expansion")
            return initial_docs

        logger.info(f"Found {len(mentioned_entities)} entities: {list(mentioned_entities)[:5]}")

        # 2. Find related entities through dependencies
        related_entities = self._find_related_entities(mentioned_entities)

        logger.info(f"Found {len(related_entities)} related entities through dependencies")

        # 3. Find documents for related entities
        additional_docs = self._find_docs_for_entities(
            related_entities - mentioned_entities,  # Exclude already included
            max_count=max_additional
        )

        logger.info(f"Adding {len(additional_docs)} additional documents")

        # 4. Merge and return
        return initial_docs + additional_docs

    def _extract_entities_from_docs(self, docs: List) -> Set[str]:
        """Extract entities (classes, methods) from documents"""
        entities = set()

        for doc in docs:
            if not hasattr(doc, 'meta_data'):
                continue

            file_path = doc.meta_data.get('file_path', '')

            # Find all entities defined in this file
            for node in self.codemap.get('nodes', []):
                if node.get('path') == file_path:
                    entities.add(node['id'])

        return entities

    def _find_related_entities(self, entities: Set[str]) -> Set[str]:
        """
        Find entities related to given entities

        Relationship definition:
        1. Direct dependencies (A imports B, A calls B)
        2. Inheritance (A extends B, A implements B)
        3. Reverse dependencies (B is imported by A, B is called by A)
        """
        related = set(entities)  # Include original entities

        # Relationship weights (for sorting)
        entity_scores = {entity: 1.0 for entity in entities}

        for edge in self.edges:
            source_id = edge.get('source')
            target_id = edge.get('target')
            edge_type = edge.get('type', '').lower()

            # If source or target is in our entities of interest
            if source_id in entities:
                # Add target entity
                related.add(target_id)

                # Calculate score based on edge type
                weight = self._get_edge_weight(edge_type)
                if target_id not in entity_scores:
                    entity_scores[target_id] = 0
                entity_scores[target_id] += weight

            elif target_id in entities:
                # Add source entity (reverse dependency)
                related.add(source_id)

                # Lower weight for reverse dependencies
                weight = self._get_edge_weight(edge_type) * 0.5
                if source_id not in entity_scores:
                    entity_scores[source_id] = 0
                entity_scores[source_id] += weight

        return related

    def _get_edge_weight(self, edge_type: str) -> float:
        """Get edge weight based on type"""
        weights = {
            'extends': 1.0,      # High relevance
            'implements': 1.0,   # High relevance
            'imports': 0.7,      # Medium relevance
            'calls': 0.5,        # Lower relevance
            'uses': 0.5,         # Lower relevance
        }
        return weights.get(edge_type, 0.3)

    def _find_docs_for_entities(self, entities: Set[str], max_count: int) -> List:
        """Find documents corresponding to entities"""
        docs = []
        entity_scores = {}

        # Calculate scores for each entity
        for entity_id in entities:
            if entity_id in self.nodes_by_id:
                node = self.nodes_by_id[entity_id]
                file_path = node.get('path', '')

                if file_path and file_path in self.docs_by_file:
                    doc = self.docs_by_file[file_path]

                    # Calculate score (higher for classes/interfaces)
                    score = 1.0
                    if node.get('type') in ['class', 'interface']:
                        score = 1.5

                    if doc not in [d[0] for d in docs]:
                        docs.append((doc, score))

        # Sort by score and return top-k
        docs.sort(key=lambda x: x[1], reverse=True)
        result = [doc for doc, _ in docs[:max_count]]

        return result


# Minimum similarity score (prob metric [0,1]) to use a document. Below this we treat as
# no relevant context to avoid feeding weak matches to the LLM (hallucination).
MIN_RELEVANCE_SCORE = 0.45


class LayeredRAG:
    """
    Three-layer RAG retrieval system

    Layer 1: Keyword matching (fast filtering)
    Layer 2: Semantic similarity (precise retrieval)
    Layer 3: Context expansion (supplementary information)
    """

    # Structure keywords for Layer 1 detection
    STRUCTURE_KEYWORDS = {
        'architecture': ['architecture', 'structure', 'layer', '架构', '结构', 'design', 'pattern'],
        'class_details': ['class', 'method', 'function', 'interface', '类', '方法', 'api', 'endpoint'],
        'dependencies': ['dependen', 'import', 'extends', 'implements', '依赖', '继承', 'relationship']
    }

    def __init__(self, base_rag, codemap_cache_manager):
        """
        Initialize layered RAG

        Args:
            base_rag: Base RAG instance (from api/rag.py)
            codemap_cache_manager: Codemap cache manager
        """
        self.base_rag = base_rag
        self.codemap_cache = codemap_cache_manager
        self.grep_retriever = None

        # Layer configurations
        self.layer_configs = {
            'layer_1': {'enabled': True, 'timeout_ms': 100},
            'layer_2': {'enabled': True, 'timeout_ms': 500},
            'layer_3': {'enabled': True, 'timeout_ms': 300}
        }

        # Initialize GrepRetriever if repo_path is available
        repo_path = getattr(base_rag, 'repo_path', None)
        if repo_path and os.path.isdir(repo_path):
            try:
                GrepRetrieverCls = _get_grep_retriever_class()
                self.grep_retriever = GrepRetrieverCls(repo_path)
                logger.info(f"GrepRetriever initialized for {repo_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize GrepRetriever: {e}")

    def retrieve(self, query: str, repo_path: str, num_docs: int = 10) -> RAGLayerResult:
        """
        Execute layered retrieval

        Args:
            query: User query
            repo_path: Repository path
            num_docs: Number of documents to return

        Returns:
            Final retrieval result
        """
        start_time = time.time()

        # Get codemap
        codemap = self.codemap_cache.get(repo_path)

        # === Layer 1: Keyword matching ===
        layer_1_result = self._layer_1_keyword_matching(query, codemap)

        # Only skip Layer 2 when we have actual docs from Layer 1 (e.g. from codemap).
        # Never return empty: global/overview questions (e.g. "项目是微服务架构吗") need semantic retrieval.
        filtered_from_layer1 = layer_1_result.get('filtered_docs', [])
        if not layer_1_result['needs_deeper_retrieval'] and filtered_from_layer1:
            execution_time = (time.time() - start_time) * 1000
            return RAGLayerResult(
                documents=filtered_from_layer1[:num_docs],
                layer_name='layer_1',
                codemap_used=layer_1_result['codemap_used'],
                execution_time_ms=execution_time,
                metadata=layer_1_result
            )

        # === Layer 2: Semantic similarity ===
        layer_2_result = self._layer_2_semantic_retrieval(
            query,
            codemap,
            layer_1_result
        )

        # === Layer 2.5: Grep retrieval (hybrid) ===
        grep_metadata: Dict[str, Any] = {'enabled': False}
        merged_docs = layer_2_result['documents']

        if self.grep_retriever:
            try:
                grep_docs = self.grep_retriever.retrieve_documents(
                    query,
                    self.base_rag.transformed_docs,
                    max_docs=5,
                )
                if grep_docs:
                    merged_docs = self._merge_documents(
                        layer_2_result['documents'], grep_docs
                    )
                    grep_metadata = {
                        'enabled': True,
                        'grep_doc_count': len(grep_docs),
                        'merged_doc_count': len(merged_docs),
                    }
                    logger.info(
                        f"Layer 2.5 grep: {len(grep_docs)} grep docs, "
                        f"merged total {len(merged_docs)}"
                    )
                else:
                    grep_metadata = {'enabled': True, 'grep_doc_count': 0}
            except Exception as e:
                logger.warning(f"Grep retrieval failed, continuing without: {e}")
                grep_metadata = {'enabled': True, 'error': str(e)}

        # === Layer 3: Context expansion ===
        layer_3_result = self._layer_3_context_expansion(
            merged_docs,
            codemap
        )

        execution_time = (time.time() - start_time) * 1000

        return RAGLayerResult(
            documents=layer_3_result[:num_docs],
            layer_name='layer_3',
            codemap_used=bool(codemap),
            execution_time_ms=execution_time,
            metadata={
                'layer_1': layer_1_result,
                'layer_2': layer_2_result,
                'layer_2_5_grep': grep_metadata,
                'layer_3': {'document_count': len(layer_3_result)}
            }
        )

    def _layer_1_keyword_matching(self, query: str, codemap: Optional[Dict]) -> Dict:
        """
        Layer 1: Keyword matching

        Fast filtering to determine if codemap context is needed

        Returns:
            {
                'needs_codemap': bool,
                'codemap_type': str or None,
                'needs_deeper_retrieval': bool,
                'codemap_used': bool,
                'filtered_docs': List
            }
        """
        query_lower = query.lower()
        codemap_type = None

        # Detect structure keywords
        for type_name, keywords in self.STRUCTURE_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                codemap_type = type_name
                break

        needs_codemap = codemap_type is not None
        codemap_used = needs_codemap and (codemap is not None)

        # Require semantic retrieval (Layer 2) for: structure keywords, or multi-word query, or
        # longer text (e.g. Chinese sentences without spaces - len(query.split()) can be 1).
        word_count = len(query.split())
        char_count = len(query.strip())
        needs_deeper_retrieval = (
            needs_codemap
            or word_count > 3
            or (char_count >= 5 and word_count >= 1)  # e.g. "项目是微服务架构吗" -> always Layer 2
        )

        result = {
            'needs_codemap': needs_codemap,
            'codemap_type': codemap_type,
            'needs_deeper_retrieval': needs_deeper_retrieval,
            'codemap_used': codemap_used,
            'filtered_docs': []
        }

        logger.info(f"Layer 1: needs_codemap={needs_codemap}, type={codemap_type}, deeper_retrieval={needs_deeper_retrieval}")

        return result

    def _layer_2_semantic_retrieval(
        self,
        query: str,
        codemap: Optional[Dict],
        layer_1_result: Dict
    ) -> Dict:
        """
        Layer 2: Semantic similarity retrieval

        Uses base RAG retriever with codemap enhancement

        Returns:
            {
                'documents': List,
                'enhanced_query': str,
                'similarity_scores': List[float]
            }
        """
        enhanced_query = query

        # Extract entities from codemap to enhance query
        if codemap and layer_1_result['needs_codemap']:
            entities = self._extract_codemap_entities(codemap, layer_1_result['codemap_type'])
            if entities:
                # Add top entities to query for better semantic matching
                top_entities = entities[:5]  # Limit to avoid query bloat
                enhanced_query = f"{query} {' '.join(top_entities)}"
                logger.info(f"Layer 2: Enhanced query with entities: {top_entities}")

        # Use base RAG retriever for semantic search
        try:
            retrieved_documents = self.base_rag.retriever(enhanced_query)

            # Extract documents from retriever result
            if retrieved_documents and len(retrieved_documents) > 0:
                out = retrieved_documents[0]
                doc_indices = out.doc_indices
                doc_scores = getattr(out, 'doc_scores', None)
                documents = [
                    self.base_rag.transformed_docs[idx]
                    for idx in doc_indices
                ]
                # Filter by relevance: only keep docs above threshold to avoid hallucination
                if doc_scores is not None and len(doc_scores) == len(documents):
                    filtered = [
                        (doc, score)
                        for doc, score in zip(documents, doc_scores)
                        if score >= MIN_RELEVANCE_SCORE
                    ]
                    documents = [d for d, _ in filtered]
                    if filtered:
                        scores_used = [s for _, s in filtered]
                        logger.info(
                            f"Layer 2: Kept {len(documents)}/{len(doc_indices)} docs above score {MIN_RELEVANCE_SCORE}, scores={scores_used[:5]}"
                        )
                    else:
                        logger.info(
                            f"Layer 2: All {len(doc_indices)} docs below relevance {MIN_RELEVANCE_SCORE}, returning none to avoid hallucination"
                        )
            else:
                documents = []

            logger.info(f"Layer 2: Retrieved {len(documents)} documents")

            return {
                'documents': documents,
                'enhanced_query': enhanced_query,
                'similarity_scores': []
            }

        except Exception as e:
            logger.error(f"Layer 2 retrieval error: {e}")
            return {
                'documents': [],
                'enhanced_query': enhanced_query,
                'similarity_scores': []
            }

    def _layer_3_context_expansion(
        self,
        documents: List,
        codemap: Optional[Dict]
    ) -> List:
        """
        Layer 3: Context expansion

        Use codemap dependency graph to expand context

        Args:
            documents: Documents from Layer 2
            codemap: Codemap data

        Returns:
            Expanded document list
        """
        if not codemap or not documents:
            logger.info("Layer 3: Skipping expansion (no codemap or no documents)")
            return documents

        try:
            # Use DependencyContextExpander
            expander = DependencyContextExpander(codemap, self.base_rag.transformed_docs)
            expanded_docs = expander.expand(
                initial_docs=documents,
                max_additional=5  # Add up to 5 additional documents
            )

            logger.info(f"Layer 3: Expanded from {len(documents)} to {len(expanded_docs)} documents")

            return expanded_docs

        except Exception as e:
            logger.error(f"Layer 3 expansion error: {e}")
            # Fallback: return Layer 2 documents
            return documents

    @staticmethod
    def _merge_documents(semantic_docs: List, grep_docs: List) -> List:
        """
        Merge semantic (FAISS) and grep retrieval results.

        Semantic results are kept in original order (higher priority).
        Grep-only results are appended after, deduplicated by file_path.
        """
        seen_files: Set[str] = set()
        merged: List = []

        for doc in semantic_docs:
            fp = ''
            if hasattr(doc, 'meta_data'):
                fp = doc.meta_data.get('file_path', '')
            merged.append(doc)
            if fp:
                seen_files.add(fp.replace('\\', '/'))

        for doc in grep_docs:
            fp = ''
            if hasattr(doc, 'meta_data'):
                fp = doc.meta_data.get('file_path', '')
            fp_normalized = fp.replace('\\', '/') if fp else ''
            if fp_normalized and fp_normalized not in seen_files:
                merged.append(doc)
                seen_files.add(fp_normalized)

        return merged

    def _extract_codemap_entities(self, codemap: Dict, codemap_type: Optional[str]) -> List[str]:
        """
        Extract relevant entities from codemap based on query type

        Args:
            codemap: Codemap data
            codemap_type: Type of codemap context needed

        Returns:
            List of entity names
        """
        entities = []

        try:
            if codemap_type == 'architecture':
                # Extract key modules and architecture layers
                # architecture_layers is a dict: {layer_name: [class_names]}
                architecture_layers = codemap.get('architecture_layers', {})
                if isinstance(architecture_layers, dict):
                    # Extract layer names and class names from each layer
                    for layer_name, classes in architecture_layers.items():
                        entities.append(layer_name)
                        entities.extend(classes[:5])  # Add top 5 classes from each layer
                elif isinstance(architecture_layers, list):
                    # Handle legacy format (list of dicts)
                    for layer in architecture_layers:
                        if isinstance(layer, dict):
                            entities.append(layer.get('name', ''))
                        else:
                            entities.append(str(layer))

                for module in codemap.get('key_modules', [])[:10]:  # Top 10 modules
                    entities.append(module.get('name', ''))

            elif codemap_type == 'class_details':
                # Extract class and method names
                for node in codemap.get('nodes', [])[:20]:  # Top 20 nodes
                    if node.get('type') in ['class', 'interface', 'function']:
                        entities.append(node.get('name', ''))

            elif codemap_type == 'dependencies':
                # Extract nodes with most dependencies
                node_connections = {}
                for edge in codemap.get('edges', []):
                    source = edge.get('source')
                    target = edge.get('target')
                    node_connections[source] = node_connections.get(source, 0) + 1
                    node_connections[target] = node_connections.get(target, 0) + 1

                # Get top connected nodes
                top_nodes = sorted(node_connections.items(), key=lambda x: x[1], reverse=True)[:10]

                # Build node lookup from codemap
                nodes_by_id = {node['id']: node for node in codemap.get('nodes', [])}

                for node_id, _ in top_nodes:
                    if node_id in nodes_by_id:
                        # Get node name for entity
                        node_name = nodes_by_id[node_id].get('name', node_id)
                        entities.append(node_name)

            # Filter out empty strings
            entities = [e for e in entities if e]

        except Exception as e:
            logger.error(f"Error extracting codemap entities: {e}")

        return entities
