"""
调用图分析器
构建精确的函数调用关系图，识别调用链和热点函数
"""
import logging
import ast
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, deque

from api.code_analyzer import CodeAnalyzer, CodeNode, CodeEdge, NodeType, EdgeType

logger = logging.getLogger(__name__)


class CallGraphAnalyzer:
    """调用图分析器

    分析函数/方法之间的调用关系，构建调用图
    """

    def __init__(self, code_analyzer: CodeAnalyzer):
        """初始化调用图分析器

        Args:
            code_analyzer: 代码分析器实例
        """
        self.analyzer = code_analyzer
        self.call_graph: Dict[str, Set[str]] = defaultdict(set)  # caller -> [callees]
        self.reverse_call_graph: Dict[str, Set[str]] = defaultdict(set)  # callee -> [callers]
        self.function_nodes: Dict[str, CodeNode] = {}  # 函数节点映射

    def build_call_graph(self):
        """构建完整的调用图"""
        logger.info("Building call graph...")

        # 1. 收集所有函数/方法节点
        self._collect_function_nodes()

        # 2. 分析每个函数的调用关系
        for func_node in self.function_nodes.values():
            try:
                called_functions = self._extract_function_calls(func_node)
                self.call_graph[func_node.id] = called_functions

                # 更新反向调用图
                for callee in called_functions:
                    self.reverse_call_graph[callee].add(func_node.id)

                # 为每个调用创建边
                for callee in called_functions:
                    self.analyzer.edges.append(CodeEdge(
                        id=f"call_{func_node.id}_to_{callee}",
                        source=func_node.id,
                        target=callee,
                        type=EdgeType.CALL,
                        weight=1
                    ))

            except Exception as e:
                logger.warning(f"Error analyzing calls in {func_node.name}: {e}")
                continue

        logger.info(f"Call graph built: {len(self.call_graph)} functions, "
                   f"{sum(len(v) for v in self.call_graph.values())} calls")

    def _collect_function_nodes(self):
        """收集所有函数和方法节点"""
        for node in self.analyzer.nodes:
            if node.type in [NodeType.FUNCTION, NodeType.METHOD]:
                self.function_nodes[node.id] = node

                # 同时按名称索引（用于解析调用）
                # 注意：可能有同名函数，这里只保留第一个
                if node.name not in self.function_nodes:
                    self.function_nodes[node.name] = node

    def _extract_function_calls(self, func_node: CodeNode) -> Set[str]:
        """从函数节点中提取函数调用

        Args:
            func_node: 函数节点

        Returns:
            被调用函数的ID集合
        """
        if func_node.language == 'python':
            return self._extract_python_calls(func_node)
        elif func_node.language in ['javascript', 'typescript']:
            return self._extract_js_calls(func_node)
        elif func_node.language == 'java':
            return self._extract_java_calls(func_node)
        elif func_node.language == 'go':
            return self._extract_go_calls(func_node)
        else:
            return set()

    def _extract_python_calls(self, func_node: CodeNode) -> Set[str]:
        """提取Python函数中的调用"""
        called_funcs = set()

        # 获取文件路径
        file_path = self.analyzer.repo_path / func_node.path

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content)

            # 找到对应的函数定义
            target_func = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (node.name == func_node.name and
                        node.lineno == func_node.start_line):
                        target_func = node
                        break

            if not target_func:
                return called_funcs

            # 遍历函数体，查找调用
            for node in ast.walk(target_func):
                if isinstance(node, ast.Call):
                    # 获取被调用的函数名
                    func_name = None

                    if isinstance(node.func, ast.Name):
                        # 简单调用: func()
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        # 方法调用: obj.method()
                        func_name = node.func.attr
                    elif isinstance(node.func, ast.Call):
                        # 链式调用: func()()
                        # 暂不处理
                        pass

                    if func_name:
                        # 尝试解析到节点ID
                        resolved_id = self._resolve_function_name(func_name, func_node)
                        if resolved_id:
                            called_funcs.add(resolved_id)

        except Exception as e:
            logger.warning(f"Error parsing Python calls in {func_node.name}: {e}")

        return called_funcs

    def _extract_js_calls(self, func_node: CodeNode) -> Set[str]:
        """提取JavaScript/TypeScript函数中的调用（简化版）"""
        called_funcs = set()

        # 获取文件路径
        file_path = self.analyzer.repo_path / func_node.path

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 使用正则表达式提取函数调用（简化方法）
            # 匹配 functionName( 或 object.methodName(
            call_pattern = r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\('
            matches = re.findall(call_pattern, content)

            for func_name in matches:
                # 过滤常见的关键字和内置函数
                if func_name not in ['if', 'for', 'while', 'switch', 'catch', 'function']:
                    resolved_id = self._resolve_function_name(func_name, func_node)
                    if resolved_id:
                        called_funcs.add(resolved_id)

        except Exception as e:
            logger.warning(f"Error parsing JS calls in {func_node.name}: {e}")

        return called_funcs

    def _extract_java_calls(self, func_node: CodeNode) -> Set[str]:
        """提取Java方法中的调用（简化版）"""
        # 类似JS的简化实现
        return self._extract_js_calls(func_node)

    def _extract_go_calls(self, func_node: CodeNode) -> Set[str]:
        """提取Go函数中的调用（简化版）"""
        # 类似JS的简化实现
        return self._extract_js_calls(func_node)

    def _resolve_function_name(self, func_name: str, caller_node: CodeNode) -> Optional[str]:
        """解析函数名到节点ID

        Args:
            func_name: 函数名
            caller_node: 调用者节点

        Returns:
            被调用函数的节点ID，如果找不到返回None
        """
        # 1. 首先在同一文件中查找
        for node in self.analyzer.nodes:
            if (node.type in [NodeType.FUNCTION, NodeType.METHOD] and
                node.name == func_name and
                node.path == caller_node.path):
                return node.id

        # 2. 在同一模块/包中查找
        caller_dir = '/'.join(caller_node.path.split('/')[:-1])
        for node in self.analyzer.nodes:
            if (node.type in [NodeType.FUNCTION, NodeType.METHOD] and
                node.name == func_name):
                node_dir = '/'.join(node.path.split('/')[:-1])
                if node_dir == caller_dir:
                    return node.id

        # 3. 全局查找（可能有多个同名函数，返回第一个）
        if func_name in self.function_nodes:
            return self.function_nodes[func_name].id

        return None

    def find_call_chain(self, start_func: str, end_func: str, max_depth: int = 10) -> List[List[str]]:
        """找到从start_func到end_func的所有调用链

        Args:
            start_func: 起始函数ID或名称
            end_func: 目标函数ID或名称
            max_depth: 最大搜索深度

        Returns:
            调用链列表，每个调用链是函数ID列表
        """
        # 解析函数名到ID
        start_id = self._resolve_func_identifier(start_func)
        end_id = self._resolve_func_identifier(end_func)

        if not start_id or not end_id:
            logger.warning(f"Cannot resolve function: {start_func} or {end_func}")
            return []

        paths = []
        self._dfs_find_paths(start_id, end_id, [], paths, max_depth)

        return paths

    def _resolve_func_identifier(self, identifier: str) -> Optional[str]:
        """解析函数标识符（ID或名称）到ID"""
        # 如果是ID
        if identifier in self.function_nodes:
            return identifier

        # 如果是名称，查找对应的ID
        for node_id, node in self.function_nodes.items():
            if node.name == identifier:
                return node_id

        return None

    def _dfs_find_paths(
        self,
        current: str,
        target: str,
        path: List[str],
        all_paths: List[List[str]],
        max_depth: int
    ):
        """深度优先搜索查找调用路径"""
        if len(path) >= max_depth:
            return

        path.append(current)

        if current == target:
            all_paths.append(path.copy())
        else:
            # 继续搜索
            if current in self.call_graph:
                for callee in self.call_graph[current]:
                    if callee not in path:  # 避免循环
                        self._dfs_find_paths(callee, target, path, all_paths, max_depth)

        path.pop()

    def identify_hotspots(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """识别被频繁调用的函数（热点）

        Args:
            top_n: 返回前N个热点

        Returns:
            热点函数列表
        """
        call_count = {}

        # 统计每个函数被调用的次数
        for callers in self.reverse_call_graph.values():
            for caller in callers:
                call_count[caller] = call_count.get(caller, 0) + 1

        # 排序
        hotspots = sorted(call_count.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # 构建结果
        result = []
        for func_id, count in hotspots:
            if func_id in self.function_nodes:
                node = self.function_nodes[func_id]
                result.append({
                    'function_id': func_id,
                    'function_name': node.name,
                    'file_path': node.path,
                    'call_count': count,
                    'callers': list(self.reverse_call_graph.get(func_id, []))[:5]
                })

        return result

    def identify_entry_points(self) -> List[Dict[str, Any]]:
        """识别入口点函数（不被其他函数调用的函数）

        Returns:
            入口点列表
        """
        entry_points = []

        for func_id in self.function_nodes:
            # 如果函数不在反向调用图中，或者没有调用者
            if func_id not in self.reverse_call_graph or not self.reverse_call_graph[func_id]:
                node = self.function_nodes[func_id]

                # 统计该函数调用了多少其他函数
                outgoing_calls = len(self.call_graph.get(func_id, set()))

                entry_points.append({
                    'function_id': func_id,
                    'function_name': node.name,
                    'file_path': node.path,
                    'outgoing_calls': outgoing_calls
                })

        # 按出度排序（调用越多的入口点越重要）
        entry_points.sort(key=lambda x: x['outgoing_calls'], reverse=True)

        return entry_points

    def identify_leaf_functions(self) -> List[Dict[str, Any]]:
        """识别叶子函数（不调用其他函数的函数）

        Returns:
            叶子函数列表
        """
        leaf_functions = []

        for func_id, callees in self.call_graph.items():
            if not callees:  # 没有调用其他函数
                node = self.function_nodes.get(func_id)
                if node:
                    # 统计被调用次数
                    incoming_calls = len(self.reverse_call_graph.get(func_id, set()))

                    leaf_functions.append({
                        'function_id': func_id,
                        'function_name': node.name,
                        'file_path': node.path,
                        'incoming_calls': incoming_calls
                    })

        # 按入度排序（被调用越多的叶子函数越重要）
        leaf_functions.sort(key=lambda x: x['incoming_calls'], reverse=True)

        return leaf_functions

    def calculate_function_complexity(self, func_id: str) -> Dict[str, Any]:
        """计算函数的复杂度指标

        Args:
            func_id: 函数ID

        Returns:
            复杂度指标字典
        """
        if func_id not in self.function_nodes:
            return {}

        node = self.function_nodes[func_id]

        # 1. 调用复杂度（调用了多少其他函数）
        outgoing_calls = len(self.call_graph.get(func_id, set()))

        # 2. 被调用复杂度（被多少函数调用）
        incoming_calls = len(self.reverse_call_graph.get(func_id, set()))

        # 3. 代码行数
        if node.start_line and node.end_line:
            line_count = node.end_line - node.start_line + 1
        else:
            line_count = 0

        # 4. 依赖深度（最深调用链长度）
        max_depth = self._calculate_max_call_depth(func_id)

        return {
            'function_id': func_id,
            'function_name': node.name,
            'outgoing_calls': outgoing_calls,
            'incoming_calls': incoming_calls,
            'line_count': line_count,
            'max_call_depth': max_depth,
            'complexity_score': outgoing_calls * 2 + line_count / 10.0 + max_depth
        }

    def _calculate_max_call_depth(self, func_id: str, visited: Optional[Set[str]] = None, depth: int = 0) -> int:
        """计算函数的最大调用深度"""
        if visited is None:
            visited = set()

        if func_id in visited or depth > 20:  # 防止无限递归
            return depth

        visited.add(func_id)

        if func_id not in self.call_graph or not self.call_graph[func_id]:
            return depth

        max_depth = depth
        for callee in self.call_graph[func_id]:
            callee_depth = self._calculate_max_call_depth(callee, visited.copy(), depth + 1)
            max_depth = max(max_depth, callee_depth)

        return max_depth

    def export_call_graph(self) -> Dict[str, Any]:
        """导出调用图数据

        Returns:
            调用图数据字典
        """
        # 转换set为list以便JSON序列化
        call_graph_dict = {
            func_id: list(callees)
            for func_id, callees in self.call_graph.items()
        }

        return {
            'call_graph': call_graph_dict,
            'hotspots': self.identify_hotspots(top_n=20),
            'entry_points': self.identify_entry_points()[:20],
            'leaf_functions': self.identify_leaf_functions()[:20],
            'statistics': {
                'total_functions': len(self.function_nodes),
                'total_calls': sum(len(v) for v in self.call_graph.values()),
                'average_calls_per_function': sum(len(v) for v in self.call_graph.values()) / max(len(self.function_nodes), 1)
            }
        }
