#!/usr/bin/env python3
"""
完整集成测试脚本
测试所有集成功能是否正常工作
"""

import sys
import os
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_mermaid_preprocessor_integration():
    """测试MermaidPreprocessor集成"""
    logger.info("=" * 60)
    logger.info("测试1: MermaidPreprocessor集成")
    logger.info("=" * 60)
    
    try:
        from api.tools.mermaid_preprocessor import MermaidPreprocessor
        
        # 测试用例
        test_cases = [
            {
                "name": "空括号链接",
                "input": "[file.py]()",
                "expected_removed": "[file.py]()"
            },
            {
                "name": "序列图语法错误",
                "input": "autonumber    , [text] description",
                "expected_removed": ", [text]"
            },
            {
                "name": "Markdown链接",
                "input": "User->>Service: Request [file.py]()",
                "expected_removed": "[file.py]()"
            }
        ]
        
        all_passed = True
        for case in test_cases:
            cleaned = MermaidPreprocessor.preprocess(case["input"])
            if case["expected_removed"] in cleaned:
                logger.warning(f"  ⚠️  {case['name']}: 未移除 '{case['expected_removed']}'")
                all_passed = False
            else:
                logger.info(f"  ✅ {case['name']}: 通过")
        
        if all_passed:
            logger.info("✅ MermaidPreprocessor集成测试通过")
        else:
            logger.warning("⚠️  MermaidPreprocessor部分测试未通过")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ MermaidPreprocessor集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_layered_rag_structure():
    """测试LayeredRAG代码结构"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: LayeredRAG代码结构")
    logger.info("=" * 60)
    
    try:
        # 检查RAG类是否有LayeredRAG相关代码
        with open('api/rag.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = {
            'use_layered_retrieval参数': 'use_layered_retrieval' in content,
            'LayeredRAG导入': 'from api.tools.rag_layers import LayeredRAG' in content,
            'layered_rag初始化': 'self.layered_rag = LayeredRAG' in content,
            'call方法中使用LayeredRAG': 'if self.use_layered_retrieval and self.layered_rag' in content,
            'repo_path提取': 'self.repo_path =' in content,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                logger.info(f"  ✅ {check_name}")
            else:
                logger.warning(f"  ⚠️  {check_name}: 未找到")
                all_passed = False
        
        if all_passed:
            logger.info("✅ LayeredRAG代码结构检查通过")
        else:
            logger.warning("⚠️  LayeredRAG代码结构不完整")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ LayeredRAG结构检查失败: {e}")
        return False


def test_mermaid_endpoint_structure():
    """测试Mermaid端点结构"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: Mermaid预处理端点结构")
    logger.info("=" * 60)
    
    try:
        with open('api/api.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = {
            '端点定义': '/api/mermaid/preprocess' in content,
            'MermaidPreprocessor导入': 'from api.tools.mermaid_preprocessor import MermaidPreprocessor' in content,
            '请求模型': 'MermaidPreprocessRequest' in content,
            '响应模型': 'MermaidPreprocessResponse' in content,
            '处理逻辑': 'extract_and_process_mermaid_blocks' in content,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                logger.info(f"  ✅ {check_name}")
            else:
                logger.warning(f"  ⚠️  {check_name}: 未找到")
                all_passed = False
        
        if all_passed:
            logger.info("✅ Mermaid端点结构检查通过")
        else:
            logger.warning("⚠️  Mermaid端点结构不完整")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Mermaid端点结构检查失败: {e}")
        return False


def test_parallel_wiki_generator_availability():
    """测试ParallelWikiGenerator可用性"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: ParallelWikiGenerator可用性")
    logger.info("=" * 60)
    
    try:
        from api.tools.wiki_generator import ParallelWikiGenerator, PageGenerationResult
        
        # 检查类是否存在
        assert ParallelWikiGenerator is not None, "ParallelWikiGenerator类应该存在"
        assert PageGenerationResult is not None, "PageGenerationResult类应该存在"
        
        # 检查关键方法
        assert hasattr(ParallelWikiGenerator, 'generate_pages_parallel'), "应该有generate_pages_parallel方法"
        assert hasattr(ParallelWikiGenerator, '__init__'), "应该有__init__方法"
        
        logger.info("✅ ParallelWikiGenerator可用性检查通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ ParallelWikiGenerator可用性检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_code_quality():
    """检查代码质量"""
    logger.info("\n" + "=" * 60)
    logger.info("检查代码质量")
    logger.info("=" * 60)
    
    issues = []
    
    # 检查是否有语法错误
    try:
        import ast
        files_to_check = [
            'api/rag.py',
            'api/api.py',
            'api/websocket_wiki.py',
            'api/tools/rag_layers.py',
            'api/tools/wiki_generator.py',
            'api/tools/mermaid_preprocessor.py',
        ]
        
        for file_path in files_to_check:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    ast.parse(f.read())
                logger.info(f"  ✅ {file_path}: 语法正确")
            except SyntaxError as e:
                logger.error(f"  ❌ {file_path}: 语法错误 - {e}")
                issues.append(f"{file_path}: {e}")
            except Exception as e:
                logger.warning(f"  ⚠️  {file_path}: 检查失败 - {e}")
        
        if not issues:
            logger.info("✅ 所有文件语法检查通过")
        else:
            logger.warning(f"⚠️  发现 {len(issues)} 个语法问题")
        
        return len(issues) == 0
        
    except Exception as e:
        logger.error(f"❌ 代码质量检查失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("开始完整集成测试...")
    logger.info("")
    
    results = {}
    
    # 测试1: MermaidPreprocessor集成
    results['mermaid_preprocessor'] = test_mermaid_preprocessor_integration()
    
    # 测试2: LayeredRAG结构
    results['layered_rag_structure'] = test_layered_rag_structure()
    
    # 测试3: Mermaid端点结构
    results['mermaid_endpoint'] = test_mermaid_endpoint_structure()
    
    # 测试4: ParallelWikiGenerator可用性
    results['parallel_wiki'] = test_parallel_wiki_generator_availability()
    
    # 代码质量检查
    results['code_quality'] = check_code_quality()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    logger.info("\n测试结果:")
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ 所有集成测试通过")
    else:
        logger.info("⚠️  部分测试未通过，请检查上述输出")
    logger.info("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())

