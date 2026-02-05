#!/usr/bin/env python3
"""
测试新增功能的脚本
测试模块化RAG架构、并行wiki页面生成、Mermaid标签预处理
"""

import sys
import os
import asyncio
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_mermaid_preprocessor():
    """测试MermaidPreprocessor功能"""
    logger.info("=" * 60)
    logger.info("测试1: MermaidPreprocessor功能")
    logger.info("=" * 60)
    
    try:
        from api.tools.mermaid_preprocessor import MermaidPreprocessor
        
        # 测试用例1: 包含Markdown链接的Mermaid代码
        test_code_1 = """sequenceDiagram
    participant User
    participant Service
    User->>Service: Request [file.py]()
    Service-->>User: Response Sources: [data.json]()
    autonumber    , [text] description
"""
        
        cleaned_1 = MermaidPreprocessor.preprocess(test_code_1)
        logger.info(f"原始代码:\n{test_code_1}")
        logger.info(f"清理后代码:\n{cleaned_1}")
        
        # 验证清理结果
        assert "[file.py]()" not in cleaned_1, "应该移除Markdown链接"
        assert "Sources:" not in cleaned_1, "应该移除Sources引用"
        assert "autonumber    , [text]" not in cleaned_1, "应该修复autonumber后的逗号和括号"
        logger.info("✅ MermaidPreprocessor测试通过")
        
        # 测试用例2: 序列图语法错误
        test_code_2 = """sequenceDiagram
    participant A, [description]
    A->>B: Message, [note]
    activate Service, [text]
"""
        
        cleaned_2 = MermaidPreprocessor.preprocess(test_code_2)
        logger.info(f"\n原始代码:\n{test_code_2}")
        logger.info(f"清理后代码:\n{cleaned_2}")
        
        assert ", [description]" not in cleaned_2, "应该移除participant后的逗号和括号"
        assert ", [note]" not in cleaned_2, "应该移除箭头标签后的逗号和括号"
        logger.info("✅ MermaidPreprocessor序列图测试通过")
        
        # 测试用例3: 从Markdown中提取并处理
        markdown_content = """# 文档

一些文本

```mermaid
graph TD
    A[Start] , [Error]
    B --> C Sources: [file.py]()
```
"""
        
        processed = MermaidPreprocessor.extract_and_process_mermaid_blocks(markdown_content)
        logger.info(f"\n原始Markdown:\n{markdown_content}")
        logger.info(f"处理后Markdown:\n{processed}")
        
        assert ", [Error]" not in processed, "应该移除错误语法"
        assert "Sources:" not in processed, "应该移除Sources引用"
        logger.info("✅ MermaidPreprocessor Markdown提取测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MermaidPreprocessor测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_layered_rag():
    """测试LayeredRAG功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: LayeredRAG功能")
    logger.info("=" * 60)
    
    try:
        from api.tools.rag_layers import LayeredRAG, RAGLayerResult
        from unittest.mock import Mock
        
        # 创建模拟的base_rag和codemap_cache
        mock_base_rag = Mock()
        mock_base_rag.retriever = Mock(return_value=[Mock(doc_indices=[0, 1, 2])])
        mock_base_rag.transformed_docs = [
            Mock(meta_data={'file_path': 'file1.py'}),
            Mock(meta_data={'file_path': 'file2.py'}),
            Mock(meta_data={'file_path': 'file3.py'}),
        ]
        
        mock_codemap_cache = Mock()
        mock_codemap_cache.get = Mock(return_value={
            'nodes': [
                {'id': 'node1', 'name': 'ClassA', 'type': 'class', 'path': 'file1.py'},
                {'id': 'node2', 'name': 'ClassB', 'type': 'class', 'path': 'file2.py'},
            ],
            'edges': [
                {'source': 'node1', 'target': 'node2', 'type': 'imports'},
            ],
            'architecture_layers': [],
            'key_modules': []
        })
        
        # 创建LayeredRAG实例
        layered_rag = LayeredRAG(mock_base_rag, mock_codemap_cache)
        
        # 测试1: 简单查询（应该在第一层返回）
        logger.info("\n测试1: 简单查询")
        result1 = layered_rag.retrieve("Hi", "/test/repo", num_docs=5)
        assert isinstance(result1, RAGLayerResult), "应该返回RAGLayerResult"
        logger.info(f"结果: layer_name={result1.layer_name}, codemap_used={result1.codemap_used}")
        
        # 测试2: 架构查询（应该使用codemap）
        logger.info("\n测试2: 架构查询")
        result2 = layered_rag.retrieve("What is the architecture?", "/test/repo", num_docs=5)
        assert isinstance(result2, RAGLayerResult), "应该返回RAGLayerResult"
        logger.info(f"结果: layer_name={result2.layer_name}, codemap_used={result2.codemap_used}")
        assert result2.codemap_used, "架构查询应该使用codemap"
        
        # 测试3: 依赖查询
        logger.info("\n测试3: 依赖查询")
        result3 = layered_rag.retrieve("Show dependencies", "/test/repo", num_docs=5)
        assert isinstance(result3, RAGLayerResult), "应该返回RAGLayerResult"
        logger.info(f"结果: layer_name={result3.layer_name}, codemap_used={result3.codemap_used}")
        
        logger.info("✅ LayeredRAG测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ LayeredRAG测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parallel_wiki_generator():
    """测试ParallelWikiGenerator功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: ParallelWikiGenerator功能")
    logger.info("=" * 60)
    
    try:
        from api.tools.wiki_generator import ParallelWikiGenerator, PageGenerationResult
        
        # 创建模拟的LLM服务
        class MockLLMService:
            async def generate(self, prompt: str) -> str:
                await asyncio.sleep(0.1)  # 模拟延迟
                return f"# Generated Content\n\nContent for: {prompt[:50]}..."
        
        mock_llm = MockLLMService()
        
        # 创建ParallelWikiGenerator实例
        generator = ParallelWikiGenerator(
            llm_service=mock_llm,
            max_workers=3,
            enable_codemap=False  # 简化测试，不使用codemap
        )
        
        # 准备测试页面
        test_pages = [
            {'title': 'Page 1', 'description': 'First page', 'relevant_files': []},
            {'title': 'Page 2', 'description': 'Second page', 'relevant_files': []},
            {'title': 'Page 3', 'description': 'Third page', 'relevant_files': []},
        ]
        
        logger.info(f"\n开始并行生成 {len(test_pages)} 个页面...")
        
        # 执行并行生成
        results = await generator.generate_pages_parallel(
            pages=test_pages,
            repo_path="/test/repo"
        )
        
        # 验证结果
        assert len(results) == len(test_pages), f"应该生成 {len(test_pages)} 个结果"
        
        for i, result in enumerate(results):
            assert isinstance(result, PageGenerationResult), f"结果 {i} 应该是PageGenerationResult"
            assert result.page_index == i, f"结果 {i} 的page_index应该是 {i}"
            logger.info(f"页面 {i}: title={result.title}, success={result.success}, "
                       f"generation_time={result.generation_time_ms:.2f}ms")
        
        # 获取统计信息
        stats = generator.get_statistics(results)
        logger.info(f"\n统计信息: {stats}")
        
        assert stats['total_pages'] == len(test_pages), "总页面数应该正确"
        assert stats['success_rate'] > 0, "成功率应该大于0"
        
        logger.info("✅ ParallelWikiGenerator测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ ParallelWikiGenerator测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_integration():
    """检查功能是否已集成到主流程"""
    logger.info("\n" + "=" * 60)
    logger.info("检查功能集成情况")
    logger.info("=" * 60)
    
    integration_status = {
        'MermaidPreprocessor': False,
        'LayeredRAG': False,
        'ParallelWikiGenerator': False,
    }
    
    # 检查MermaidPreprocessor是否在API中被使用
    try:
        # 检查websocket_wiki.py
        with open('api/websocket_wiki.py', 'r', encoding='utf-8') as f:
            websocket_wiki_content = f.read()
            if 'MermaidPreprocessor' in websocket_wiki_content:
                integration_status['MermaidPreprocessor'] = True
                logger.info("✅ MermaidPreprocessor在websocket_wiki.py中被使用")
            else:
                logger.warning("⚠️  MermaidPreprocessor未在websocket_wiki.py中使用")
    except Exception as e:
        logger.warning(f"⚠️  无法检查websocket_wiki.py: {e}")
    
    # 检查LayeredRAG是否在RAG中被使用
    try:
        with open('api/rag.py', 'r', encoding='utf-8') as f:
            rag_content = f.read()
            if 'LayeredRAG' in rag_content or 'layered_rag' in rag_content:
                integration_status['LayeredRAG'] = True
                logger.info("✅ LayeredRAG在rag.py中被使用")
            else:
                logger.warning("⚠️  LayeredRAG未在rag.py中使用")
    except Exception as e:
        logger.warning(f"⚠️  无法检查rag.py: {e}")
    
    # 检查ParallelWikiGenerator是否在websocket_wiki.py中被使用
    try:
        with open('api/websocket_wiki.py', 'r', encoding='utf-8') as f:
            websocket_wiki_content = f.read()
            if 'ParallelWikiGenerator' in websocket_wiki_content:
                integration_status['ParallelWikiGenerator'] = True
                logger.info("✅ ParallelWikiGenerator在websocket_wiki.py中被使用")
            else:
                logger.warning("⚠️  ParallelWikiGenerator未在websocket_wiki.py中使用")
    except Exception as e:
        logger.warning(f"⚠️  无法检查websocket_wiki.py: {e}")
    
    return integration_status


async def main():
    """主测试函数"""
    logger.info("开始测试新增功能...")
    logger.info("")
    
    results = {}
    
    # 测试1: MermaidPreprocessor
    results['MermaidPreprocessor'] = test_mermaid_preprocessor()
    
    # 测试2: LayeredRAG
    results['LayeredRAG'] = test_layered_rag()
    
    # 测试3: ParallelWikiGenerator
    results['ParallelWikiGenerator'] = await test_parallel_wiki_generator()
    
    # 检查集成情况
    integration_status = check_integration()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    logger.info("\n功能测试结果:")
    for feature, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"  {feature}: {status}")
    
    logger.info("\n集成检查结果:")
    for feature, integrated in integration_status.items():
        status = "✅ 已集成" if integrated else "⚠️  未集成"
        logger.info(f"  {feature}: {status}")
    
    # 总体评估
    all_tests_passed = all(results.values())
    all_integrated = all(integration_status.values())
    
    logger.info("\n" + "=" * 60)
    if all_tests_passed and all_integrated:
        logger.info("✅ 所有功能测试通过且已集成")
    elif all_tests_passed:
        logger.info("✅ 所有功能测试通过，但部分功能未集成到主流程")
    else:
        logger.info("❌ 部分功能测试失败")
    logger.info("=" * 60)
    
    return all_tests_passed


if __name__ == "__main__":
    asyncio.run(main())

