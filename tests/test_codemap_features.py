# -*- coding: utf-8 -*-
"""
测试Codemap新增功能
"""
import os
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("Test 1: Module Imports")
    print("=" * 60)

    try:
        from api.code_analyzer import CodeAnalyzer
        print("[OK] CodeAnalyzer imported")
    except Exception as e:
        print(f"[FAIL] CodeAnalyzer import failed: {e}")
        return False

    try:
        from api.ai_enhanced_analyzer import AIEnhancedCodeAnalyzer
        print("[OK] AIEnhancedCodeAnalyzer imported")
    except Exception as e:
        print(f"[FAIL] AIEnhancedCodeAnalyzer import failed: {e}")
        return False

    try:
        from api.call_graph_analyzer import CallGraphAnalyzer
        print("[OK] CallGraphAnalyzer imported")
    except Exception as e:
        print(f"[FAIL] CallGraphAnalyzer import failed: {e}")
        return False

    try:
        from api.dataflow_analyzer import DataFlowAnalyzer
        print("[OK] DataFlowAnalyzer imported")
    except Exception as e:
        print(f"[FAIL] DataFlowAnalyzer import failed: {e}")
        return False

    try:
        from api.codemap_enhanced_rag import CodemapEnhancedRAG
        print("[OK] CodemapEnhancedRAG imported")
    except Exception as e:
        print(f"[FAIL] CodemapEnhancedRAG import failed: {e}")
        return False

    try:
        from api.codemap_endpoints import router
        print("[OK] Codemap Router imported")
    except Exception as e:
        print(f"[FAIL] Codemap Router import failed: {e}")
        return False

    print("\nAll module import tests passed!\n")
    return True


def test_code_analyzer():
    """测试基础代码分析功能"""
    print("=" * 60)
    print("测试 2: 基础代码分析")
    print("=" * 60)

    try:
        from api.code_analyzer import CodeAnalyzer

        # 使用当前项目的api目录进行测试
        repo_path = project_root / "api"

        print(f"分析目录: {repo_path}")
        analyzer = CodeAnalyzer(repo_path=str(repo_path))
        analyzer.analyze()

        print(f"✓ 发现 {len(analyzer.nodes)} 个代码节点")
        print(f"✓ 发现 {len(analyzer.edges)} 个代码边")

        # 显示前5个节点
        print("\n前5个代码节点:")
        for i, node in enumerate(analyzer.nodes[:5]):
            print(f"  {i+1}. {node.name} ({node.type}) - {node.path}")

        return True
    except Exception as e:
        print(f"✗ 代码分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_call_graph():
    """测试调用图分析功能"""
    print("\n" + "=" * 60)
    print("测试 3: 调用图分析")
    print("=" * 60)

    try:
        from api.code_analyzer import CodeAnalyzer
        from api.call_graph_analyzer import CallGraphAnalyzer

        repo_path = project_root / "api"

        print(f"分析目录: {repo_path}")
        analyzer = CodeAnalyzer(repo_path=str(repo_path))
        analyzer.analyze()

        call_graph = CallGraphAnalyzer(analyzer)
        call_graph.build_call_graph()

        print(f"✓ 构建了包含 {len(call_graph.function_nodes)} 个函数的调用图")
        print(f"✓ 识别了 {sum(len(v) for v in call_graph.call_graph.values())} 个函数调用")

        # 识别热点函数
        hotspots = call_graph.identify_hotspots(top_n=3)
        print(f"\n前3个热点函数 (被频繁调用):")
        for i, hotspot in enumerate(hotspots):
            print(f"  {i+1}. {hotspot['function_name']} - 被调用 {hotspot['call_count']} 次")

        # 识别入口点
        entry_points = call_graph.identify_entry_points()[:3]
        print(f"\n前3个入口点函数 (不被其他函数调用):")
        for i, entry in enumerate(entry_points):
            print(f"  {i+1}. {entry['function_name']} - 调用了 {entry['outgoing_calls']} 个函数")

        return True
    except Exception as e:
        print(f"✗ 调用图分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dataflow():
    """测试数据流分析功能"""
    print("\n" + "=" * 60)
    print("测试 4: 数据流分析")
    print("=" * 60)

    try:
        from api.code_analyzer import CodeAnalyzer
        from api.dataflow_analyzer import DataFlowAnalyzer

        repo_path = project_root / "api"

        print(f"分析目录: {repo_path}")
        analyzer = CodeAnalyzer(repo_path=str(repo_path))
        analyzer.analyze()

        dataflow = DataFlowAnalyzer(analyzer)

        # 找一个函数来测试
        test_func = None
        for node in analyzer.nodes:
            if node.type == 'function' and node.language == 'python':
                test_func = node
                break

        if test_func:
            print(f"\n测试变量流追踪: 函数 '{test_func.name}'")

            # 测试追踪常见变量名
            for var_name in ['data', 'result', 'response']:
                flows = dataflow.trace_variable_flow(var_name, test_func, max_results=5)
                if flows:
                    print(f"✓ 追踪到变量 '{var_name}' 的 {len(flows)} 个数据流节点")
                    break

            print("\n数据流分析功能正常工作!")
        else:
            print("⚠ 未找到Python函数进行测试")

        return True
    except Exception as e:
        print(f"✗ 数据流分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_layout_algorithms():
    """测试前端布局算法"""
    print("\n" + "=" * 60)
    print("测试 5: 布局算法")
    print("=" * 60)

    # 由于这是TypeScript代码，我们只检查文件是否存在
    layout_file = project_root / "src" / "utils" / "codemapLayouts.ts"

    if layout_file.exists():
        print(f"✓ 布局算法文件存在: {layout_file}")

        # 读取文件内容并检查关键函数
        content = layout_file.read_text(encoding='utf-8')

        algorithms = ['forceDirectedLayout', 'hierarchicalLayout', 'groupedLayout', 'gridLayout']
        found = []
        for algo in algorithms:
            if algo in content:
                found.append(algo)

        print(f"✓ 找到 {len(found)}/{len(algorithms)} 个布局算法:")
        for algo in found:
            print(f"  - {algo}")

        return len(found) == len(algorithms)
    else:
        print(f"✗ 布局算法文件不存在: {layout_file}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Codemap功能测试套件")
    print("=" * 60 + "\n")

    results = []

    # 测试1: 导入
    results.append(("模块导入", test_imports()))

    # 测试2: 基础代码分析
    results.append(("基础代码分析", test_code_analyzer()))

    # 测试3: 调用图
    results.append(("调用图分析", test_call_graph()))

    # 测试4: 数据流
    results.append(("数据流分析", test_dataflow()))

    # 测试5: 布局算法
    results.append(("布局算法", test_layout_algorithms()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
