"""
Unit tests for Layered RAG System

Tests:
- RAGLayerResult dataclass
- DependencyContextExpander
- LayeredRAG three-layer retrieval
- Codemap integration
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import asdict

from api.tools.rag_layers import (
    RAGLayerResult,
    DependencyContextExpander,
    LayeredRAG
)


class MockDocument:
    """Mock document for testing"""
    def __init__(self, file_path: str, content: str = ""):
        self.meta_data = {'file_path': file_path}
        self.text = content
        self.vector = [0.1] * 768  # Mock embedding


class TestRAGLayerResult(unittest.TestCase):
    """Test RAGLayerResult dataclass"""

    def test_create_layer_result(self):
        """Test creating a layer result"""
        docs = [MockDocument('file1.py'), MockDocument('file2.py')]

        result = RAGLayerResult(
            documents=docs,
            layer_name='layer_2',
            codemap_used=True,
            execution_time_ms=150.5,
            metadata={'test': 'data'}
        )

        self.assertEqual(len(result.documents), 2)
        self.assertEqual(result.layer_name, 'layer_2')
        self.assertTrue(result.codemap_used)
        self.assertEqual(result.execution_time_ms, 150.5)
        self.assertEqual(result.metadata['test'], 'data')

    def test_default_metadata(self):
        """Test default empty metadata"""
        result = RAGLayerResult(
            documents=[],
            layer_name='layer_1',
            codemap_used=False,
            execution_time_ms=10.0
        )

        self.assertEqual(result.metadata, {})


class TestDependencyContextExpander(unittest.TestCase):
    """Test DependencyContextExpander functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock codemap
        self.codemap = {
            'nodes': [
                {'id': 'node1', 'name': 'ClassA', 'type': 'class', 'path': 'file1.py'},
                {'id': 'node2', 'name': 'ClassB', 'type': 'class', 'path': 'file2.py'},
                {'id': 'node3', 'name': 'ClassC', 'type': 'class', 'path': 'file3.py'},
                {'id': 'node4', 'name': 'FunctionD', 'type': 'function', 'path': 'file4.py'},
            ],
            'edges': [
                {'source': 'node1', 'target': 'node2', 'type': 'imports'},
                {'source': 'node1', 'target': 'node3', 'type': 'extends'},
                {'source': 'node2', 'target': 'node4', 'type': 'calls'},
            ]
        }

        # Create mock documents
        self.all_documents = [
            MockDocument('file1.py', 'class ClassA'),
            MockDocument('file2.py', 'class ClassB'),
            MockDocument('file3.py', 'class ClassC'),
            MockDocument('file4.py', 'def FunctionD'),
        ]

    def test_initialization(self):
        """Test expander initialization"""
        expander = DependencyContextExpander(self.codemap, self.all_documents)

        self.assertEqual(len(expander.nodes_by_id), 4)
        self.assertEqual(len(expander.nodes_by_name), 4)
        self.assertEqual(len(expander.edges), 3)
        self.assertEqual(len(expander.docs_by_file), 4)

    def test_extract_entities_from_docs(self):
        """Test extracting entities from documents"""
        expander = DependencyContextExpander(self.codemap, self.all_documents)

        initial_docs = [self.all_documents[0]]  # file1.py
        entities = expander._extract_entities_from_docs(initial_docs)

        # Should extract node1 (ClassA from file1.py)
        self.assertIn('node1', entities)

    def test_find_related_entities(self):
        """Test finding related entities through dependencies"""
        expander = DependencyContextExpander(self.codemap, self.all_documents)

        # Start with node1
        entities = {'node1'}
        related = expander._find_related_entities(entities)

        # Should find node1, node2 (imports), node3 (extends)
        self.assertIn('node1', related)  # Original
        self.assertIn('node2', related)  # Imported by node1
        self.assertIn('node3', related)  # Extended by node1

    def test_edge_weights(self):
        """Test edge weight calculation"""
        expander = DependencyContextExpander(self.codemap, self.all_documents)

        # Test different edge types
        self.assertEqual(expander._get_edge_weight('extends'), 1.0)
        self.assertEqual(expander._get_edge_weight('implements'), 1.0)
        self.assertEqual(expander._get_edge_weight('imports'), 0.7)
        self.assertEqual(expander._get_edge_weight('calls'), 0.5)
        self.assertEqual(expander._get_edge_weight('unknown'), 0.3)

    def test_find_docs_for_entities(self):
        """Test finding documents for entities"""
        expander = DependencyContextExpander(self.codemap, self.all_documents)

        entities = {'node2', 'node3'}
        docs = expander._find_docs_for_entities(entities, max_count=2)

        # Should return documents for node2 and node3
        self.assertLessEqual(len(docs), 2)

    def test_expand_context(self):
        """Test full context expansion"""
        expander = DependencyContextExpander(self.codemap, self.all_documents)

        initial_docs = [self.all_documents[0]]  # file1.py (node1)
        expanded = expander.expand(initial_docs, max_additional=2)

        # Should include initial docs + additional related docs
        self.assertGreaterEqual(len(expanded), len(initial_docs))
        self.assertIn(self.all_documents[0], expanded)

    def test_expand_with_no_entities(self):
        """Test expansion when no entities found"""
        # Empty codemap
        empty_codemap = {'nodes': [], 'edges': []}
        expander = DependencyContextExpander(empty_codemap, self.all_documents)

        initial_docs = [self.all_documents[0]]
        expanded = expander.expand(initial_docs, max_additional=2)

        # Should return original docs unchanged
        self.assertEqual(expanded, initial_docs)


class TestLayeredRAG(unittest.TestCase):
    """Test LayeredRAG three-layer retrieval"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock base RAG
        self.base_rag = Mock()
        self.base_rag.transformed_docs = [
            MockDocument('file1.py', 'class ClassA'),
            MockDocument('file2.py', 'class ClassB'),
            MockDocument('file3.py', 'class ClassC'),
        ]

        # Create mock retriever result
        mock_retriever_result = [Mock()]
        mock_retriever_result[0].doc_indices = [0, 1]  # Return first 2 docs
        self.base_rag.retriever = Mock(return_value=mock_retriever_result)

        # Create mock codemap cache
        self.codemap_cache = Mock()
        self.codemap = {
            'nodes': [
                {'id': 'node1', 'name': 'ClassA', 'type': 'class', 'path': 'file1.py'},
                {'id': 'node2', 'name': 'ClassB', 'type': 'class', 'path': 'file2.py'},
            ],
            'edges': [
                {'source': 'node1', 'target': 'node2', 'type': 'imports'},
            ],
            'key_modules': [
                {'name': 'ModuleA'},
                {'name': 'ModuleB'},
            ],
            'architecture_layers': [
                {'name': 'presentation'},
                {'name': 'business'},
            ]
        }
        self.codemap_cache.get = Mock(return_value=self.codemap)

        # Create LayeredRAG instance
        self.layered_rag = LayeredRAG(self.base_rag, self.codemap_cache)

    def test_initialization(self):
        """Test LayeredRAG initialization"""
        self.assertIsNotNone(self.layered_rag.base_rag)
        self.assertIsNotNone(self.layered_rag.codemap_cache)
        self.assertEqual(len(self.layered_rag.layer_configs), 3)

    def test_layer_1_keyword_matching_with_structure(self):
        """Test Layer 1 with structure keywords"""
        query = "What is the architecture of the system?"

        result = self.layered_rag._layer_1_keyword_matching(query, self.codemap)

        self.assertTrue(result['needs_codemap'])
        self.assertEqual(result['codemap_type'], 'architecture')
        self.assertTrue(result['needs_deeper_retrieval'])
        self.assertTrue(result['codemap_used'])

    def test_layer_1_keyword_matching_class_query(self):
        """Test Layer 1 with class-related keywords"""
        query = "Show me the class definition"

        result = self.layered_rag._layer_1_keyword_matching(query, self.codemap)

        self.assertTrue(result['needs_codemap'])
        self.assertEqual(result['codemap_type'], 'class_details')

    def test_layer_1_keyword_matching_dependency_query(self):
        """Test Layer 1 with dependency keywords"""
        query = "What are the dependencies of this module?"

        result = self.layered_rag._layer_1_keyword_matching(query, self.codemap)

        self.assertTrue(result['needs_codemap'])
        self.assertEqual(result['codemap_type'], 'dependencies')

    def test_layer_1_simple_query(self):
        """Test Layer 1 with simple query (no structure keywords)"""
        query = "Hi"

        result = self.layered_rag._layer_1_keyword_matching(query, self.codemap)

        self.assertFalse(result['needs_codemap'])
        self.assertIsNone(result['codemap_type'])
        self.assertFalse(result['needs_deeper_retrieval'])

    def test_layer_2_semantic_retrieval(self):
        """Test Layer 2 semantic retrieval"""
        query = "Find ClassA implementation"
        layer_1_result = {
            'needs_codemap': True,
            'codemap_type': 'class_details'
        }

        result = self.layered_rag._layer_2_semantic_retrieval(
            query,
            self.codemap,
            layer_1_result
        )

        # Should have called base retriever
        self.base_rag.retriever.assert_called_once()

        # Should return documents
        self.assertIn('documents', result)
        self.assertIn('enhanced_query', result)

    def test_layer_2_without_codemap(self):
        """Test Layer 2 without codemap"""
        query = "Find something"
        layer_1_result = {
            'needs_codemap': False,
            'codemap_type': None
        }

        result = self.layered_rag._layer_2_semantic_retrieval(
            query,
            None,  # No codemap
            layer_1_result
        )

        # Enhanced query should be same as original
        self.assertEqual(result['enhanced_query'], query)

    def test_layer_3_context_expansion(self):
        """Test Layer 3 context expansion"""
        documents = [self.base_rag.transformed_docs[0]]

        result = self.layered_rag._layer_3_context_expansion(
            documents,
            self.codemap
        )

        # Should return list of documents (potentially expanded)
        self.assertIsInstance(result, list)

    def test_layer_3_without_codemap(self):
        """Test Layer 3 without codemap"""
        documents = [self.base_rag.transformed_docs[0]]

        result = self.layered_rag._layer_3_context_expansion(
            documents,
            None  # No codemap
        )

        # Should return original documents unchanged
        self.assertEqual(result, documents)

    def test_layer_3_with_empty_documents(self):
        """Test Layer 3 with empty documents"""
        result = self.layered_rag._layer_3_context_expansion(
            [],  # Empty
            self.codemap
        )

        # Should return empty list
        self.assertEqual(result, [])

    def test_extract_codemap_entities_architecture(self):
        """Test extracting architecture entities"""
        entities = self.layered_rag._extract_codemap_entities(
            self.codemap,
            'architecture'
        )

        # Should include architecture layers and key modules
        self.assertIn('presentation', entities)
        self.assertIn('business', entities)
        self.assertIn('ModuleA', entities)

    def test_extract_codemap_entities_class_details(self):
        """Test extracting class entities"""
        entities = self.layered_rag._extract_codemap_entities(
            self.codemap,
            'class_details'
        )

        # Should include class names
        self.assertIn('ClassA', entities)
        self.assertIn('ClassB', entities)

    def test_full_retrieval_pipeline(self):
        """Test complete retrieval pipeline"""
        query = "What is the architecture?"
        repo_path = "/test/repo"

        result = self.layered_rag.retrieve(query, repo_path, num_docs=5)

        # Should return RAGLayerResult
        self.assertIsInstance(result, RAGLayerResult)

        # Should have called codemap cache
        self.codemap_cache.get.assert_called_with(repo_path)

        # Should have execution time
        self.assertGreater(result.execution_time_ms, 0)

    def test_retrieval_short_circuits_at_layer_1(self):
        """Test that simple queries short-circuit at Layer 1"""
        query = "Hi"  # Simple query
        repo_path = "/test/repo"

        result = self.layered_rag.retrieve(query, repo_path)

        # Should return at Layer 1
        self.assertEqual(result.layer_name, 'layer_1')

        # Should not call base retriever
        self.base_rag.retriever.assert_not_called()

    def test_retrieval_goes_through_all_layers(self):
        """Test that complex queries go through all layers"""
        query = "Explain the class architecture and dependencies"
        repo_path = "/test/repo"

        result = self.layered_rag.retrieve(query, repo_path)

        # Should go through all layers
        self.assertEqual(result.layer_name, 'layer_3')

        # Should have called base retriever
        self.base_rag.retriever.assert_called()

        # Should have metadata from all layers
        self.assertIn('layer_1', result.metadata)
        self.assertIn('layer_2', result.metadata)
        self.assertIn('layer_3', result.metadata)

    def test_retrieval_with_no_codemap(self):
        """Test retrieval when codemap is not available"""
        self.codemap_cache.get = Mock(return_value=None)

        query = "What is the architecture?"
        repo_path = "/test/repo"

        result = self.layered_rag.retrieve(query, repo_path)

        # Should still complete
        self.assertIsInstance(result, RAGLayerResult)

        # Codemap should not be used
        self.assertFalse(result.codemap_used)


if __name__ == '__main__':
    unittest.main()
