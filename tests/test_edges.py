# -*- coding: utf-8 -*-
"""Test edges generation"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing edge generation...")

from api.code_analyzer import CodeAnalyzer

# Analyze api directory
repo_path = project_root / "api"
print(f"Analyzing: {repo_path}")

analyzer = CodeAnalyzer(repo_path=str(repo_path))
codemap = analyzer.analyze()

print(f"\nResults:")
print(f"  Nodes: {len(codemap.nodes)}")
print(f"  Edges: {len(codemap.edges)}")

# Count edges by type
edge_types = {}
for edge in codemap.edges:
    edge_type = str(edge.type)
    edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

print(f"\nEdge types:")
for edge_type, count in sorted(edge_types.items()):
    print(f"  {edge_type}: {count}")

# Show some sample edges
print(f"\nSample edges (first 10):")
for i, edge in enumerate(codemap.edges[:10]):
    source_node = next((n for n in codemap.nodes if n.id == edge.source), None)
    target_node = next((n for n in codemap.nodes if n.id == edge.target), None)
    if source_node and target_node:
        print(f"  {i+1}. {source_node.name} --[{edge.type}]--> {target_node.name}")

print("\nTest complete!")
