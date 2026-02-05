#!/usr/bin/env python3
"""
前端集成测试脚本
测试并行wiki生成和Mermaid预处理集成
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_websocket_endpoint_exists():
    """测试websocket端点是否存在"""
    logger.info("=" * 60)
    logger.info("测试1: 检查并行wiki生成websocket端点")
    logger.info("=" * 60)
    
    try:
        with open('api/api.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = {
            '导入websocket_wiki_parallel': 'from api.websocket_wiki_parallel import handle_websocket_wiki_generate' in content,
            '添加websocket路由': 'app.add_websocket_route("/ws/wiki/generate"' in content,
            '端点路径': '/ws/wiki/generate' in content,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                logger.info(f"  ✅ {check_name}")
            else:
                logger.warning(f"  ⚠️  {check_name}: 未找到")
                all_passed = False
        
        if all_passed:
            logger.info("✅ Websocket端点检查通过")
        else:
            logger.warning("⚠️  Websocket端点检查未完全通过")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Websocket端点检查失败: {e}")
        return False


def test_frontend_integration():
    """测试前端集成"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 检查前端并行生成集成")
    logger.info("=" * 60)
    
    try:
        with open('src/app/[owner]/[repo]/page.tsx', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = {
            '并行生成逻辑': 'generatePagesParallel' in content or 'parallel generation' in content.lower(),
            'WebSocket连接': 'getWebSocketUrl(\'/ws/wiki/generate\')' in content,
            'Mermaid预处理': 'mermaidBlockRegex' in content or 'Preprocess Mermaid' in content,
            '响应处理': 'data.stage === \'complete\'' in content,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                logger.info(f"  ✅ {check_name}")
            else:
                logger.warning(f"  ⚠️  {check_name}: 未找到")
                all_passed = False
        
        if all_passed:
            logger.info("✅ 前端集成检查通过")
        else:
            logger.warning("⚠️  前端集成检查未完全通过")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ 前端集成检查失败: {e}")
        return False


def test_mermaid_preprocessing():
    """测试Mermaid预处理"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 检查Mermaid预处理集成")
    logger.info("=" * 60)
    
    try:
        # 检查后端端点
        with open('api/websocket_wiki_parallel.py', 'r', encoding='utf-8') as f:
            backend_content = f.read()
        
        # 检查前端处理
        with open('src/app/[owner]/[repo]/page.tsx', 'r', encoding='utf-8') as f:
            frontend_content = f.read()
        
        checks = {
            '后端Mermaid预处理': 'MermaidPreprocessor.extract_and_process_mermaid_blocks' in backend_content,
            '前端Mermaid预处理': 'mermaidBlockRegex' in frontend_content or 'Preprocess Mermaid' in frontend_content,
            'Mermaid导入': 'from api.tools.mermaid_preprocessor import MermaidPreprocessor' in backend_content,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                logger.info(f"  ✅ {check_name}")
            else:
                logger.warning(f"  ⚠️  {check_name}: 未找到")
                all_passed = False
        
        if all_passed:
            logger.info("✅ Mermaid预处理检查通过")
        else:
            logger.warning("⚠️  Mermaid预处理检查未完全通过")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Mermaid预处理检查失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("开始前端集成测试...")
    logger.info("")
    
    results = {}
    
    # 测试1: Websocket端点
    results['websocket_endpoint'] = test_websocket_endpoint_exists()
    
    # 测试2: 前端集成
    results['frontend_integration'] = test_frontend_integration()
    
    # 测试3: Mermaid预处理
    results['mermaid_preprocessing'] = test_mermaid_preprocessing()
    
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
        logger.info("✅ 所有前端集成测试通过")
    else:
        logger.info("⚠️  部分测试未通过，请检查上述输出")
    logger.info("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    main()

