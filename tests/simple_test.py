# -*- coding: utf-8 -*-
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*60)
print("Codemap Features Test Suite")
print("="*60)

# Test 1: Imports
print("\n[Test 1] Module Imports...")
try:
    from api.code_analyzer import CodeAnalyzer
    from api.ai_enhanced_analyzer import AIEnhancedCodeAnalyzer
    from api.call_graph_analyzer import CallGraphAnalyzer
    from api.dataflow_analyzer import DataFlowAnalyzer
    from api.codemap_enhanced_rag import CodemapEnhancedRAG
    from api.codemap_endpoints import router
    print("[OK] All modules imported successfully")
except Exception as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Test 2: Basic Code Analysis
print("\n[Test 2] Basic Code Analysis...")
try:
    repo_path = project_root / "api"
    analyzer = CodeAnalyzer(repo_path=str(repo_path))
    analyzer.analyze()
    print(f"[OK] Found {len(analyzer.nodes)} nodes and {len(analyzer.edges)} edges")

    # Show first 3 nodes
    print("  Sample nodes:")
    for i, node in enumerate(analyzer.nodes[:3]):
        print(f"    {i+1}. {node.name} ({node.type})")
except Exception as e:
    print(f"[FAIL] Analysis error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Call Graph
print("\n[Test 3] Call Graph Analysis...")
try:
    call_graph = CallGraphAnalyzer(analyzer)
    call_graph.build_call_graph()
    print(f"[OK] Built call graph with {len(call_graph.function_nodes)} functions")

    hotspots = call_graph.identify_hotspots(top_n=2)
    print(f"  Top hotspot functions:")
    for i, h in enumerate(hotspots):
        print(f"    {i+1}. {h['function_name']} (called {h['call_count']} times)")
except Exception as e:
    print(f"[FAIL] Call graph error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Data Flow
print("\n[Test 4] Data Flow Analysis...")
try:
    dataflow = DataFlowAnalyzer(analyzer)

    # Find a test function
    test_func = None
    for node in analyzer.nodes:
        if node.type == 'function' and node.language == 'python':
            test_func = node
            break

    if test_func:
        # Try to trace a common variable
        flows = dataflow.trace_variable_flow('data', test_func, max_results=3)
        if flows:
            print(f"[OK] Traced variable 'data': found {len(flows)} flow nodes")
        else:
            print("[OK] Data flow analysis working (no flows for 'data' in test function)")
    else:
        print("[SKIP] No Python function found for testing")
except Exception as e:
    print(f"[FAIL] Data flow error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Layout Algorithms
print("\n[Test 5] Layout Algorithms...")
try:
    layout_file = project_root / "src" / "utils" / "codemapLayouts.ts"
    if layout_file.exists():
        content = layout_file.read_text(encoding='utf-8')
        algorithms = ['forceDirectedLayout', 'hierarchicalLayout', 'groupedLayout', 'gridLayout']
        found = [algo for algo in algorithms if algo in content]
        print(f"[OK] Found {len(found)}/4 layout algorithms")
        for algo in found:
            print(f"    - {algo}")
    else:
        print("[FAIL] Layout file not found")
except Exception as e:
    print(f"[FAIL] Layout test error: {e}")

# Test 6: API Routes
print("\n[Test 6] API Routes Registration...")
try:
    from api.api import app
    codemap_routes = [r.path for r in app.routes if 'codemap' in r.path.lower()]
    print(f"[OK] Found {len(codemap_routes)} codemap routes:")
    for route in codemap_routes[:5]:
        print(f"    - {route}")
except Exception as e:
    print(f"[FAIL] API routes error: {e}")

print("\n" + "="*60)
print("Test Suite Complete!")
print("="*60)
