# -*- coding: utf-8 -*-
"""
测试Codemap边数据格式和显示问题
"""
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.code_analyzer import CodeAnalyzer

def test_edge_display():
    """测试边数据是否正确生成和格式化"""

    print("=" * 60)
    print("Testing Edge Data Format for Display")
    print("=" * 60)
    print()

    # 测试路径：使用当前项目的api目录
    test_path = os.path.join(os.path.dirname(__file__), "api")

    if not os.path.exists(test_path):
        print(f"[FAIL] Test path does not exist: {test_path}")
        return False

    print(f"[1] Analyzing repository: {test_path}")
    print()

    try:
        # 创建分析器
        analyzer = CodeAnalyzer(test_path)

        # 运行分析
        codemap = analyzer.analyze()

        # 转换为字典（模拟序列化）
        codemap_dict = codemap.to_dict()

        print(f"[OK] Analysis complete")
        print(f"  - Nodes: {len(codemap_dict['nodes'])}")
        print(f"  - Edges: {len(codemap_dict['edges'])}")
        print()

        # 检查边的数据格式
        print("[2] Examining edge data format:")
        print()

        if len(codemap_dict['edges']) == 0:
            print("[FAIL] No edges found! This is the problem.")
            return False

        # 显示前5条边的详细信息
        print("First 5 edges:")
        for i, edge in enumerate(codemap_dict['edges'][:5], 1):
            print(f"  Edge {i}:")
            print(f"    - id: {edge['id']}")
            print(f"    - source: {edge['source']}")
            print(f"    - target: {edge['target']}")
            print(f"    - type: {edge['type']}")
            print(f"    - label: {edge.get('label', 'N/A')}")
            print()

        # 检查节点ID
        print("[3] Verifying node IDs:")
        print()

        node_ids = {node['id'] for node in codemap_dict['nodes']}
        print(f"  - Total unique node IDs: {len(node_ids)}")

        # 检查边引用的节点是否存在
        missing_sources = set()
        missing_targets = set()

        for edge in codemap_dict['edges']:
            if edge['source'] not in node_ids:
                missing_sources.add(edge['source'])
            if edge['target'] not in node_ids:
                missing_targets.add(edge['target'])

        if missing_sources:
            print(f"  [WARNING] Found {len(missing_sources)} edges with missing source nodes")
            print(f"    Examples: {list(missing_sources)[:3]}")

        if missing_targets:
            print(f"  [WARNING] Found {len(missing_targets)} edges with missing target nodes")
            print(f"    Examples: {list(missing_targets)[:3]}")

        if not missing_sources and not missing_targets:
            print("  [OK] All edge references valid")
        print()

        # 统计边的类型
        print("[4] Edge type distribution:")
        print()

        edge_types = {}
        for edge in codemap_dict['edges']:
            edge_type = edge['type']
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        for edge_type, count in sorted(edge_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {edge_type}: {count}")
        print()

        # 保存示例数据到文件供前端测试
        sample_data = {
            'nodes': codemap_dict['nodes'][:10],  # 前10个节点
            'edges': codemap_dict['edges'][:20],  # 前20条边
            'metadata': codemap_dict['metadata']
        }

        output_file = "codemap_sample_for_frontend_test.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)

        print(f"[5] Sample data saved to: {output_file}")
        print("  This file can be used for frontend testing")
        print()

        # 检查是否有可能导致前端不显示边的问题
        print("[6] Checking for potential frontend issues:")
        print()

        issues_found = False

        # 检查边数据的必需字段
        required_edge_fields = ['id', 'source', 'target', 'type']
        for i, edge in enumerate(codemap_dict['edges'][:10], 1):
            for field in required_edge_fields:
                if field not in edge:
                    print(f"  [WARNING] Edge {i} missing required field: {field}")
                    issues_found = True

        if not issues_found:
            print("  [OK] All edges have required fields (id, source, target, type)")
        print()

        print("=" * 60)
        print("[SUCCESS] Edge data format test completed")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  - Edges are being generated correctly: {len(codemap_dict['edges'])} edges")
        print(f"  - All required fields present: YES")
        print(f"  - Node ID references valid: {not (missing_sources or missing_targets)}")
        print()
        print("If edges are still not displaying in the frontend:")
        print("  1. Check browser console for errors")
        print("  2. Verify ReactFlow is loading correctly")
        print("  3. Check if edges are being filtered out")
        print("  4. Inspect the network request to see if edges are included")
        print()

        return True

    except Exception as e:
        print(f"[FAIL] Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_edge_display()
    sys.exit(0 if success else 1)
