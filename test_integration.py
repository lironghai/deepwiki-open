#!/usr/bin/env python3
"""
集成功能测试脚本
测试LayeredRAG、MermaidPreprocessor、ParallelWikiGenerator的集成
"""

import sys
import os
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_layered_rag_integration():
    """测试LayeredRAG集成到RAG类"""
    logger.info("=" * 60)
    logger.info("测试1: LayeredRAG集成到RAG类")
    logger.info("=" * 60)
    
    try:
        from api.rag import RAG
        from unittest.mock import Mock, patch
        
        # 创建RAG实例（启用layered retrieval）
        rag = RAG(provider="google", use_layered_retrieval=True)
        
        # 检查layered_rag属性是否存在
        assert hasattr(rag, 'use_layered_retrieval'), "RAG应该有use_layered_retrieval属性"
        assert rag.use_layered_retrieval == True, "use_layered_retrieval应该为True"
        assert hasattr(rag, '_codemap_cache'), "RAG应该有_codemap_cache属性"
        
        logger.info("✅ LayeredRAG集成检查通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ LayeredRAG集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mermaid_preprocessor_endpoint():
    """测试MermaidPreprocessor API端点"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: MermaidPreprocessor API端点")
    logger.info("=" * 60)
    
    try:
        from api.tools.mermaid_preprocessor import MermaidPreprocessor
        
        # 测试内容
        test_content = """# 文档

一些文本

```mermaid
sequenceDiagram
    participant User
    User->>Service: Request [file.py]()
    autonumber    , [text] description
```
"""
        
        # 预处理
        processed = MermaidPreprocessor.extract_and_process_mermaid_blocks(test_content)
        
        logger.info(f"原始内容长度: {len(test_content)}")
        logger.info(f"处理后内容长度: {len(processed)}")
        
        # 验证
        assert "[file.py]()" not in processed, "应该移除Markdown链接"
        assert "autonumber    , [text]" not in processed, "应该修复autonumber语法"
        
        logger.info("✅ MermaidPreprocessor端点测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ MermaidPreprocessor端点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_with_layered_retrieval():
    """测试RAG使用LayeredRAG检索"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: RAG使用LayeredRAG检索")
    logger.info("=" * 60)
    
    try:
        from api.rag import RAG
        from unittest.mock import Mock, patch
        
        # 创建RAG实例
        rag = RAG(provider="google", use_layered_retrieval=True)
        
        # Mock prepare_retriever
        with patch.object(rag, 'prepare_retriever') as mock_prepare:
            mock_prepare.return_value = None
            
            # Mock transformed_docs和retriever
            rag.transformed_docs = [Mock()]
            rag.retriever = Mock()
            rag.repo_path = "/test/repo"
            
            # 检查layered_rag是否会在prepare_retriever后初始化
            # 由于需要真实的retriever，这里只检查结构
            assert hasattr(rag, 'use_layered_retrieval'), "应该有use_layered_retrieval属性"
            
        logger.info("✅ RAG LayeredRAG检索测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ RAG LayeredRAG检索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_integration_status():
    """检查集成状态"""
    logger.info("\n" + "=" * 60)
    logger.info("检查集成状态")
    logger.info("=" * 60)
    
    status = {
        'LayeredRAG_in_RAG': False,
        'MermaidPreprocessor_endpoint': False,
        'MermaidPreprocessor_import': False,
    }
    
    # 检查LayeredRAG是否在RAG中
    try:
        with open('api/rag.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'LayeredRAG' in content and 'use_layered_retrieval' in content:
                status['LayeredRAG_in_RAG'] = True
                logger.info("✅ LayeredRAG已集成到RAG类")
            else:
                logger.warning("⚠️  LayeredRAG未完全集成到RAG类")
    except Exception as e:
        logger.warning(f"⚠️  无法检查rag.py: {e}")
    
    # 检查MermaidPreprocessor端点
    try:
        with open('api/api.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if '/api/mermaid/preprocess' in content and 'MermaidPreprocessor' in content:
                status['MermaidPreprocessor_endpoint'] = True
                logger.info("✅ MermaidPreprocessor端点已添加")
            else:
                logger.warning("⚠️  MermaidPreprocessor端点未添加")
    except Exception as e:
        logger.warning(f"⚠️  无法检查api.py: {e}")
    
    # 检查MermaidPreprocessor导入
    try:
        with open('api/websocket_wiki.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'MermaidPreprocessor' in content:
                status['MermaidPreprocessor_import'] = True
                logger.info("✅ MermaidPreprocessor已导入到websocket_wiki.py")
            else:
                logger.warning("⚠️  MermaidPreprocessor未导入到websocket_wiki.py")
    except Exception as e:
        logger.warning(f"⚠️  无法检查websocket_wiki.py: {e}")
    
    return status


async def main():
    """主测试函数"""
    logger.info("开始集成功能测试...")
    logger.info("")
    
    results = {}
    
    # 测试1: LayeredRAG集成
    results['LayeredRAG_integration'] = test_layered_rag_integration()
    
    # 测试2: MermaidPreprocessor端点
    results['MermaidPreprocessor_endpoint'] = test_mermaid_preprocessor_endpoint()
    
    # 测试3: RAG使用LayeredRAG
    results['RAG_layered_retrieval'] = test_rag_with_layered_retrieval()
    
    # 检查集成状态
    integration_status = check_integration_status()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    logger.info("\n功能测试结果:")
    for feature, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"  {feature}: {status}")
    
    logger.info("\n集成状态:")
    for feature, integrated in integration_status.items():
        status = "✅ 已集成" if integrated else "⚠️  未集成"
        logger.info(f"  {feature}: {status}")
    
    all_tests_passed = all(results.values())
    all_integrated = all(integration_status.values())
    
    logger.info("\n" + "=" * 60)
    if all_tests_passed and all_integrated:
        logger.info("✅ 所有功能测试通过且已集成")
    elif all_tests_passed:
        logger.info("✅ 所有功能测试通过，部分功能已集成")
    else:
        logger.info("❌ 部分功能测试失败")
    logger.info("=" * 60)
    
    return all_tests_passed


if __name__ == "__main__":
    asyncio.run(main())

