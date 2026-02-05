"""
数据流追踪分析器
追踪变量和数据在代码中的流动路径
"""
import logging
import ast
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from api.code_analyzer import CodeAnalyzer, CodeNode, NodeType

logger = logging.getLogger(__name__)


class DataFlowType(str, Enum):
    """数据流类型"""
    DEFINITION = "definition"  # 变量定义
    ASSIGNMENT = "assignment"  # 赋值
    USAGE = "usage"  # 使用
    RETURN = "return"  # 返回
    PARAMETER = "parameter"  # 参数传递
    ATTRIBUTE_ACCESS = "attribute_access"  # 属性访问


@dataclass
class DataFlowNode:
    """数据流节点"""
    node_id: str
    flow_type: DataFlowType
    variable_name: str
    line_number: int
    file_path: str
    code_snippet: Optional[str] = None
    context: Optional[str] = None


class DataFlowAnalyzer:
    """数据流追踪分析器

    分析变量和数据在代码中的流动
    """

    def __init__(self, code_analyzer: CodeAnalyzer):
        """初始化数据流分析器

        Args:
            code_analyzer: 代码分析器实例
        """
        self.analyzer = code_analyzer
        self.data_flows: Dict[str, List[DataFlowNode]] = {}  # variable_name -> flow_nodes

    def trace_variable_flow(
        self,
        var_name: str,
        start_node: CodeNode,
        max_results: int = 50
    ) -> List[DataFlowNode]:
        """追踪变量的数据流

        Args:
            var_name: 变量名
            start_node: 起始节点（函数或类）
            max_results: 最大结果数

        Returns:
            数据流节点列表
        """
        logger.info(f"Tracing variable flow: {var_name} in {start_node.name}")

        flow_nodes = []

        if start_node.language == 'python':
            flow_nodes = self._trace_python_variable(var_name, start_node)
        elif start_node.language in ['javascript', 'typescript']:
            flow_nodes = self._trace_js_variable(var_name, start_node)
        else:
            logger.warning(f"Variable tracing not supported for {start_node.language}")

        # 按行号排序
        flow_nodes.sort(key=lambda n: n.line_number)

        return flow_nodes[:max_results]

    def _trace_python_variable(self, var_name: str, func_node: CodeNode) -> List[DataFlowNode]:
        """追踪Python变量的数据流"""
        flow_nodes = []

        # 获取文件路径
        file_path = self.analyzer.repo_path / func_node.path

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                content = ''.join(lines)

            # 解析AST
            tree = ast.parse(content)

            # 找到目标函数
            target_func = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (node.name == func_node.name and
                        hasattr(node, 'lineno') and
                        node.lineno == func_node.start_line):
                        target_func = node
                        break

            if not target_func:
                return flow_nodes

            # 遍历函数体，查找变量使用
            for node in ast.walk(target_func):
                # 1. 检查赋值
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == var_name:
                            flow_nodes.append(DataFlowNode(
                                node_id=f"{func_node.id}_assign_{node.lineno}",
                                flow_type=DataFlowType.ASSIGNMENT,
                                variable_name=var_name,
                                line_number=node.lineno,
                                file_path=func_node.path,
                                code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None
                            ))

                # 2. 检查参数定义
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args:
                        if arg.arg == var_name:
                            flow_nodes.append(DataFlowNode(
                                node_id=f"{func_node.id}_param_{node.lineno}",
                                flow_type=DataFlowType.PARAMETER,
                                variable_name=var_name,
                                line_number=node.lineno,
                                file_path=func_node.path,
                                code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None,
                                context="function parameter"
                            ))

                # 3. 检查变量使用
                elif isinstance(node, ast.Name) and node.id == var_name:
                    # 区分是Load（使用）还是Store（定义）
                    if isinstance(node.ctx, ast.Load):
                        if hasattr(node, 'lineno'):
                            flow_nodes.append(DataFlowNode(
                                node_id=f"{func_node.id}_usage_{node.lineno}",
                                flow_type=DataFlowType.USAGE,
                                variable_name=var_name,
                                line_number=node.lineno,
                                file_path=func_node.path,
                                code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None
                            ))

                # 4. 检查返回语句
                elif isinstance(node, ast.Return):
                    if hasattr(node.value, 'id') and node.value.id == var_name:
                        flow_nodes.append(DataFlowNode(
                            node_id=f"{func_node.id}_return_{node.lineno}",
                            flow_type=DataFlowType.RETURN,
                            variable_name=var_name,
                            line_number=node.lineno,
                            file_path=func_node.path,
                            code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None,
                            context="return statement"
                        ))

                # 5. 检查属性访问
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id == var_name:
                        if hasattr(node, 'lineno'):
                            flow_nodes.append(DataFlowNode(
                                node_id=f"{func_node.id}_attr_{node.lineno}",
                                flow_type=DataFlowType.ATTRIBUTE_ACCESS,
                                variable_name=var_name,
                                line_number=node.lineno,
                                file_path=func_node.path,
                                code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None,
                                context=f"accessing .{node.attr}"
                            ))

        except Exception as e:
            logger.error(f"Error tracing Python variable {var_name}: {e}")

        return flow_nodes

    def _trace_js_variable(self, var_name: str, func_node: CodeNode) -> List[DataFlowNode]:
        """追踪JavaScript变量的数据流（简化版，使用正则）"""
        flow_nodes = []

        # 获取文件路径
        file_path = self.analyzer.repo_path / func_node.path

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 只分析函数体内的行
            if func_node.start_line and func_node.end_line:
                func_lines = lines[func_node.start_line - 1:func_node.end_line]
                start_line_offset = func_node.start_line
            else:
                func_lines = lines
                start_line_offset = 1

            # 使用正则表达式查找变量使用
            for idx, line in enumerate(func_lines):
                line_num = start_line_offset + idx

                # 检查变量定义/赋值
                if re.search(rf'\b(?:var|let|const)\s+{var_name}\s*=', line):
                    flow_nodes.append(DataFlowNode(
                        node_id=f"{func_node.id}_def_{line_num}",
                        flow_type=DataFlowType.DEFINITION,
                        variable_name=var_name,
                        line_number=line_num,
                        file_path=func_node.path,
                        code_snippet=line.strip()
                    ))
                elif re.search(rf'\b{var_name}\s*=', line):
                    flow_nodes.append(DataFlowNode(
                        node_id=f"{func_node.id}_assign_{line_num}",
                        flow_type=DataFlowType.ASSIGNMENT,
                        variable_name=var_name,
                        line_number=line_num,
                        file_path=func_node.path,
                        code_snippet=line.strip()
                    ))

                # 检查变量使用
                elif re.search(rf'\b{var_name}\b', line):
                    # 检查是否是return语句
                    if 'return' in line:
                        flow_nodes.append(DataFlowNode(
                            node_id=f"{func_node.id}_return_{line_num}",
                            flow_type=DataFlowType.RETURN,
                            variable_name=var_name,
                            line_number=line_num,
                            file_path=func_node.path,
                            code_snippet=line.strip()
                        ))
                    else:
                        flow_nodes.append(DataFlowNode(
                            node_id=f"{func_node.id}_usage_{line_num}",
                            flow_type=DataFlowType.USAGE,
                            variable_name=var_name,
                            line_number=line_num,
                            file_path=func_node.path,
                            code_snippet=line.strip()
                        ))

        except Exception as e:
            logger.error(f"Error tracing JS variable {var_name}: {e}")

        return flow_nodes

    def analyze_api_data_flow(self, endpoint: str) -> Dict[str, Any]:
        """分析API端点的数据流

        Args:
            endpoint: API端点路径（如 /api/users）

        Returns:
            数据流分析结果
        """
        logger.info(f"Analyzing API data flow for {endpoint}")

        # 1. 找到端点处理函数
        handler = self._find_endpoint_handler(endpoint)

        if not handler:
            logger.warning(f"No handler found for endpoint {endpoint}")
            return {
                'endpoint': endpoint,
                'handler': None,
                'error': 'Handler not found'
            }

        # 2. 追踪请求数据
        request_flow = self._trace_request_data(handler)

        # 3. 追踪响应数据
        response_flow = self._trace_response_data(handler)

        # 4. 识别数据库操作
        db_operations = self._identify_db_operations(handler)

        return {
            'endpoint': endpoint,
            'handler': {
                'name': handler.name,
                'file': handler.path,
                'line': handler.start_line
            },
            'request_flow': request_flow,
            'response_flow': response_flow,
            'db_operations': db_operations
        }

    def _find_endpoint_handler(self, endpoint: str) -> Optional[CodeNode]:
        """查找API端点的处理函数"""
        # 查找所有函数，检查是否有装饰器或注释包含endpoint
        for node in self.analyzer.nodes:
            if node.type != NodeType.FUNCTION:
                continue

            # 检查元数据中是否有装饰器信息
            if node.metadata and 'decorators' in node.metadata:
                decorators = node.metadata['decorators']
                for decorator in decorators:
                    if endpoint in decorator:
                        return node

            # 也可以通过函数名推断（如get_users -> /api/users）
            # 这里简化处理
            if endpoint.replace('/', '_').replace('-', '_').lower() in node.name.lower():
                return node

        return None

    def _trace_request_data(self, handler: CodeNode) -> List[Dict[str, Any]]:
        """追踪请求数据流"""
        # 查找常见的请求参数名
        request_vars = ['request', 'req', 'data', 'body', 'params', 'query']

        flows = []
        for var in request_vars:
            var_flows = self.trace_variable_flow(var, handler, max_results=10)
            if var_flows:
                flows.append({
                    'variable': var,
                    'flow': [
                        {
                            'type': node.flow_type.value,
                            'line': node.line_number,
                            'snippet': node.code_snippet
                        }
                        for node in var_flows
                    ]
                })

        return flows

    def _trace_response_data(self, handler: CodeNode) -> List[Dict[str, Any]]:
        """追踪响应数据流"""
        # 查找return语句和response变量
        response_vars = ['response', 'res', 'result', 'data']

        flows = []
        for var in response_vars:
            var_flows = self.trace_variable_flow(var, handler, max_results=10)
            if var_flows:
                flows.append({
                    'variable': var,
                    'flow': [
                        {
                            'type': node.flow_type.value,
                            'line': node.line_number,
                            'snippet': node.code_snippet
                        }
                        for node in var_flows
                    ]
                })

        return flows

    def _identify_db_operations(self, handler: CodeNode) -> List[Dict[str, Any]]:
        """识别数据库操作"""
        # 获取文件内容
        file_path = self.analyzer.repo_path / handler.path

        operations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 在处理函数范围内查找数据库操作关键词
            if handler.start_line and handler.end_line:
                func_lines = lines[handler.start_line - 1:handler.end_line]
                start_offset = handler.start_line
            else:
                func_lines = lines
                start_offset = 1

            # 数据库操作关键词
            db_keywords = [
                'SELECT', 'INSERT', 'UPDATE', 'DELETE',  # SQL
                '.find(', '.findOne(', '.insert(', '.update(', '.delete(',  # MongoDB
                '.query(', '.execute(', '.save(', '.get(', '.filter(',  # ORM
                'db.', 'collection.', 'model.'  # 通用
            ]

            for idx, line in enumerate(func_lines):
                line_num = start_offset + idx
                for keyword in db_keywords:
                    if keyword.lower() in line.lower():
                        operations.append({
                            'line': line_num,
                            'operation': self._classify_db_operation(line),
                            'snippet': line.strip()
                        })
                        break

        except Exception as e:
            logger.error(f"Error identifying DB operations: {e}")

        return operations

    def _classify_db_operation(self, line: str) -> str:
        """分类数据库操作类型"""
        line_lower = line.lower()

        if 'select' in line_lower or '.find(' in line_lower or '.get(' in line_lower:
            return 'READ'
        elif 'insert' in line_lower or '.insert(' in line_lower or '.save(' in line_lower:
            return 'CREATE'
        elif 'update' in line_lower or '.update(' in line_lower:
            return 'UPDATE'
        elif 'delete' in line_lower or '.delete(' in line_lower or '.remove(' in line_lower:
            return 'DELETE'
        else:
            return 'UNKNOWN'

    def export_dataflow_analysis(self) -> Dict[str, Any]:
        """导出数据流分析结果

        Returns:
            数据流分析数据字典
        """
        return {
            'tracked_variables': list(self.data_flows.keys()),
            'total_flow_nodes': sum(len(flows) for flows in self.data_flows.values()),
            'data_flows': {
                var: [
                    {
                        'type': node.flow_type.value,
                        'line': node.line_number,
                        'file': node.file_path,
                        'snippet': node.code_snippet
                    }
                    for node in flows
                ]
                for var, flows in self.data_flows.items()
            }
        }
