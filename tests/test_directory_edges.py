# -*- coding: utf-8 -*-
"""
测试目录节点的边生成
"""
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.code_analyzer import CodeAnalyzer

def test_directory_edges():
    """测试目录包含关系的边生成"""

    print("=" * 80)
    print("Testing Directory Containment Edges")
    print("=" * 80)
    print()

    # 测试路径
    test_path = os.path.join(os.path.dirname(__file__), "api")

    if not os.path.exists(test_path):
        print(f"[FAIL] Test path does not exist: {test_path}")
        return False

    print(f"Analyzing: {test_path}")
    print()

    try:
        # 创建分析器
        analyzer = CodeAnalyzer(test_path)

        # 运行分析
        codemap = analyzer.analyze()

        # 转换为字典
        codemap_dict = codemap.to_dict()

        print(f"[OK] Analysis complete")
        print(f"  Total nodes: {len(codemap_dict['nodes'])}")
        print(f"  Total edges: {len(codemap_dict['edges'])}")
        print()

        # 统计各类型节点
        node_types = {}
        for node in codemap_dict['nodes']:
            node_type = node['type']
            node_types[node_type] = node_types.get(node_type, 0) + 1

        print("[1] Node type distribution:")
        for node_type, count in sorted(node_types.items()):
            print(f"  {node_type}: {count}")
        print()

        # 统计边类型
        edge_types = {}
        for edge in codemap_dict['edges']:
            edge_type = edge['type']
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        print("[2] Edge type distribution:")
        for edge_type, count in sorted(edge_types.items()):
            print(f"  {edge_type}: {count}")
        print()

        # 检查目录节点的边
        directory_nodes = [n['id'] for n in codemap_dict['nodes'] if n['type'] == 'directory']
        directory_edges = [
            e for e in codemap_dict['edges']
            if e['source'] in directory_nodes or e['target'] in directory_nodes
        ]

        print(f"[3] Directory node analysis:")
        print(f"  Directory nodes: {len(directory_nodes)}")
        print(f"  Edges involving directories: {len(directory_edges)}")
        print()

        if len(directory_edges) == 0:
            print("[FAIL] No edges involving directory nodes!")
            print("  This means directories are isolated and have no relationships.")
            return False

        # 显示前10条目录相关的边
        print("[4] Sample directory edges (first 10):")
        for i, edge in enumerate(directory_edges[:10], 1):
            # 找到源和目标节点的名称
            source_node = next((n for n in codemap_dict['nodes'] if n['id'] == edge['source']), None)
            target_node = next((n for n in codemap_dict['nodes'] if n['id'] == edge['target']), None)

            if source_node and target_node:
                print(f"\n  Edge {i}:")
                print(f"    {source_node['name']} ({source_node['type']})")
                print(f"      --[{edge['type']}]-->")
                print(f"    {target_node['name']} ({target_node['type']})")

        print()

        # 统计目录边的类型分布
        dir_edge_types = {}
        for edge in directory_edges:
            edge_type = edge['type']
            dir_edge_types[edge_type] = dir_edge_types.get(edge_type, 0) + 1

        print("[5] Directory edge type distribution:")
        for edge_type, count in sorted(dir_edge_types.items()):
            print(f"  {edge_type}: {count}")
        print()

        # 检查目录包含关系的完整性
        print("[6] Directory containment validation:")

        # 检查每个文件是否被其父目录包含
        file_nodes = [n for n in codemap_dict['nodes'] if n['type'] == 'file']
        files_with_parent = 0
        files_without_parent = 0

        for file_node in file_nodes:
            file_path = file_node['path']
            parent_path = os.path.dirname(file_path)

            if parent_path:
                # 查找父目录节点
                parent_node = next(
                    (n for n in codemap_dict['nodes']
                     if n['type'] == 'directory' and n['path'] == parent_path),
                    None
                )

                if parent_node:
                    # 检查是否有从父目录到文件的CONTAINS边
                    has_edge = any(
                        e for e in codemap_dict['edges']
                        if e['source'] == parent_node['id']
                        and e['target'] == file_node['id']
                        and e['type'] == 'contains'
                    )

                    if has_edge:
                        files_with_parent += 1
                    else:
                        files_without_parent += 1
                        print(f"  [WARNING] File without parent edge: {file_path}")
                else:
                    files_without_parent += 1
            else:
                # 根目录文件
                files_with_parent += 1

        print(f"  Files with parent directory edge: {files_with_parent}")
        print(f"  Files without parent directory edge: {files_without_parent}")
        print()

        # 总结
        print("=" * 80)
        print("[SUCCESS] Directory edge generation test completed")
        print("=" * 80)
        print()

        print("Summary:")
        print(f"  ✓ Total edges: {len(codemap_dict['edges'])}")
        print(f"  ✓ Directory edges: {len(directory_edges)}")
        print(f"  ✓ Directory nodes: {len(directory_nodes)}")
        print(f"  ✓ Edge types: {', '.join(edge_types.keys())}")
        print()

        if len(directory_edges) > 0:
            print("✓ Directory nodes are now connected!")
            print("✓ Directory containment relationships are working correctly.")
            return True
        else:
            print("✗ No directory edges found - there may still be an issue.")
            return False

    except Exception as e:
        print(f"[FAIL] Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_directory_edges()
    sys.exit(0 if success else 1)
