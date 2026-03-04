"""
代码分析引擎 - 提取代码结构和依赖关系
"""
import os
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """代码节点类型"""
    FILE = "file"
    DIRECTORY = "directory"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    MODULE = "module"
    INTERFACE = "interface"


class EdgeType(str, Enum):
    """依赖关系类型"""
    IMPORT = "import"
    CALL = "call"
    INHERIT = "inherit"
    IMPLEMENT = "implement"
    REFERENCE = "reference"
    CONTAINS = "contains"


@dataclass
class CodeNode:
    """代码节点"""
    id: str
    name: str
    type: NodeType
    path: str
    language: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self):
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        return data


@dataclass
class CodeEdge:
    """代码依赖关系"""
    id: str
    source: str
    target: str
    type: EdgeType
    label: Optional[str] = None
    weight: int = 1

    def to_dict(self):
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        return data


@dataclass
class CodeMap:
    """完整的代码地图"""
    nodes: List[CodeNode]
    edges: List[CodeEdge]
    metadata: Dict[str, Any]

    def to_dict(self):
        """转换为字典"""
        return {
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': [edge.to_dict() for edge in self.edges],
            'metadata': self.metadata
        }


class CodeAnalyzer:
    """代码分析器基类"""
    
    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',      # 深度支持
        '.go': 'go',          # 深度支持
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.cs': 'csharp',
        # 文档文件（只统计，不进行深度分析）
        '.md': 'markdown',
        '.txt': 'text',
        '.rst': 'restructuredtext',
    }
    
    # 只统计但不进行深度分析的文件类型
    DOCUMENT_ONLY_TYPES = {'markdown', 'text', 'restructuredtext'}
    
    # 默认排除的目录
    DEFAULT_EXCLUDED_DIRS = {
        'node_modules', '.git', '__pycache__', 'venv', '.venv',
        'dist', 'build', 'target', '.next', '.nuxt', 'coverage',
        '.pytest_cache', '.idea', '.vscode', 'vendor'
    }
    
    # 默认排除的文件
    DEFAULT_EXCLUDED_FILES = {
        '.DS_Store', 'package-lock.json', 'yarn.lock', 'Pipfile.lock',
        '*.min.js', '*.bundle.js'
    }
    
    def __init__(self, repo_path: str, options: Optional[Dict[str, Any]] = None):
        """
        初始化代码分析器
        
        Args:
            repo_path: 仓库路径
            options: 分析选项
        """
        self.repo_path = Path(repo_path)
        self.options = options or {}
        self.nodes: List[CodeNode] = []
        self.edges: List[CodeEdge] = []
        self.node_id_map: Dict[str, str] = {}  # path -> node_id
        self.language_stats: Dict[str, int] = {}
        self.total_files = 0
        self.total_lines = 0
        
        # 分析选项
        self.include_tests = self.options.get('include_tests', True)
        self.max_depth = self.options.get('max_depth', None)
        self.target_languages = self.options.get('languages', None)
        
        logger.info(f"Initialized CodeAnalyzer for {repo_path}")
    
    def analyze(self) -> CodeMap:
        """
        分析整个代码库

        Returns:
            CodeMap: 代码地图
        """
        logger.info(f"Starting code analysis for {self.repo_path}")

        try:
            # 遍历文件系统
            self._traverse_directory(self.repo_path)

            # 分析依赖关系
            self._analyze_dependencies()

            # 添加包含关系（文件包含类和函数）
            self._add_containment_edges()

            # 添加继承关系
            self._add_inheritance_edges()

            # 构建调用图（添加函数调用关系）
            self._build_call_graph()

            # 创建元数据
            metadata = {
                'repo_path': str(self.repo_path),
                'total_files': self.total_files,
                'total_lines': self.total_lines,
                'languages': self.language_stats,
                'node_count': len(self.nodes),
                'edge_count': len(self.edges)
            }

            logger.info(f"Analysis complete: {len(self.nodes)} nodes, {len(self.edges)} edges")

            return CodeMap(
                nodes=self.nodes,
                edges=self.edges,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error during code analysis: {e}")
            raise
    
    def _traverse_directory(self, directory: Path, depth: int = 0):
        """
        遍历目录
        
        Args:
            directory: 目录路径
            depth: 当前深度
        """
        # 检查深度限制
        if self.max_depth is not None and depth > self.max_depth:
            return
        
        try:
            for item in directory.iterdir():
                # 跳过排除的目录
                if item.is_dir():
                    if item.name in self.DEFAULT_EXCLUDED_DIRS:
                        continue
                    
                    # 创建目录节点
                    dir_node = self._create_directory_node(item)
                    if dir_node:
                        self.nodes.append(dir_node)
                    
                    # 递归遍历子目录
                    self._traverse_directory(item, depth + 1)
                
                elif item.is_file():
                    # 跳过不包含测试文件的情况
                    if not self.include_tests and 'test' in item.name.lower():
                        continue
                    
                    # 分析文件
                    self._analyze_file(item)
                    
        except PermissionError:
            logger.warning(f"Permission denied: {directory}")
        except Exception as e:
            logger.error(f"Error traversing {directory}: {e}")
    
    def _create_directory_node(self, directory: Path) -> Optional[CodeNode]:
        """
        创建目录节点
        
        Args:
            directory: 目录路径
            
        Returns:
            CodeNode: 目录节点
        """
        rel_path = str(directory.relative_to(self.repo_path))
        node_id = f"dir_{rel_path.replace(os.sep, '_')}"
        
        return CodeNode(
            id=node_id,
            name=directory.name,
            type=NodeType.DIRECTORY,
            path=rel_path,
            metadata={'full_path': str(directory)}
        )
    
    def _analyze_file(self, file_path: Path):
        """
        分析单个文件
        
        Args:
            file_path: 文件路径
        """
        # 获取文件扩展名和语言
        ext = file_path.suffix.lower()
        language = self.SUPPORTED_EXTENSIONS.get(ext)
        
        # 如果指定了目标语言，检查是否匹配
        if self.target_languages and language not in self.target_languages:
            return
        
        # 如果没有扩展名，检查是否是常见的无扩展名文件（如README）
        if not language:
            file_name_lower = file_path.name.lower()
            # 常见的无扩展名文档文件
            if file_name_lower in ['readme', 'license', 'changelog', 'contributing', 'authors', 'copying']:
                language = 'text'
            else:
                return  # 不支持的文件类型
        
        # 更新统计
        self.total_files += 1
        self.language_stats[language] = self.language_stats.get(language, 0) + 1
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                line_count = len(content.splitlines())
                self.total_lines += line_count
            
            # 创建文件节点
            rel_path = str(file_path.relative_to(self.repo_path))
            node_id = f"file_{rel_path.replace(os.sep, '_').replace('.', '_')}"
            
            file_node = CodeNode(
                id=node_id,
                name=file_path.name,
                type=NodeType.FILE,
                path=rel_path,
                language=language,
                metadata={
                    'size': line_count,
                    'full_path': str(file_path)
                }
            )
            
            self.nodes.append(file_node)
            self.node_id_map[rel_path] = node_id
            
            # 如果是文档文件，只统计不进行深度分析
            if language in self.DOCUMENT_ONLY_TYPES:
                return
            
            # 根据语言进行深度分析
            if language == 'python':
                self._analyze_python_file(file_path, content, file_node)
            elif language in ['javascript', 'typescript']:
                self._analyze_javascript_file(file_path, content, file_node)
            elif language == 'java':
                self._analyze_java_file(file_path, content, file_node)
            elif language == 'go':
                self._analyze_go_file(file_path, content, file_node)
            
        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {e}")
    
    def _analyze_python_file(self, file_path: Path, content: str, parent_node: CodeNode):
        """
        分析Python文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            parent_node: 父节点（文件节点）
        """
        import ast
        
        try:
            tree = ast.parse(content)
            
            # 提取导入
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # 更新文件节点的元数据
            if parent_node.metadata is None:
                parent_node.metadata = {}
            parent_node.metadata['imports'] = imports
            
            # 提取类和函数
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    self._extract_python_class(node, parent_node, file_path)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    self._extract_python_function(node, parent_node, file_path)
                    
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error analyzing Python file {file_path}: {e}")
    
    def _extract_python_class(self, node: Any, parent_node: CodeNode, file_path: Path):
        """提取Python类"""
        rel_path = str(file_path.relative_to(self.repo_path))
        class_id = f"class_{parent_node.id}_{node.name}"
        
        class_node = CodeNode(
            id=class_id,
            name=node.name,
            type=NodeType.CLASS,
            path=rel_path,
            language='python',
            start_line=node.lineno,
            end_line=node.end_lineno,
            description=self._get_docstring(node),
            metadata={
                'parent_file': parent_node.id,
                'bases': [base.id if hasattr(base, 'id') else str(base) for base in node.bases[:3]]
            }
        )
        
        self.nodes.append(class_node)
        
        # 创建包含关系
        self.edges.append(CodeEdge(
            id=f"edge_{parent_node.id}_contains_{class_id}",
            source=parent_node.id,
            target=class_id,
            type=EdgeType.CONTAINS
        ))
        
        # 提取方法
        import ast
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_python_method(item, class_node, file_path)
    
    def _extract_python_function(self, node: Any, parent_node: CodeNode, file_path: Path):
        """提取Python函数"""
        rel_path = str(file_path.relative_to(self.repo_path))
        func_id = f"func_{parent_node.id}_{node.name}"
        
        func_node = CodeNode(
            id=func_id,
            name=node.name,
            type=NodeType.FUNCTION,
            path=rel_path,
            language='python',
            start_line=node.lineno,
            end_line=node.end_lineno,
            description=self._get_docstring(node),
            metadata={'parent_file': parent_node.id}
        )
        
        self.nodes.append(func_node)
        
        # 创建包含关系
        self.edges.append(CodeEdge(
            id=f"edge_{parent_node.id}_contains_{func_id}",
            source=parent_node.id,
            target=func_id,
            type=EdgeType.CONTAINS
        ))
    
    def _extract_python_method(self, node: Any, parent_node: CodeNode, file_path: Path):
        """提取Python方法"""
        rel_path = str(file_path.relative_to(self.repo_path))
        method_id = f"method_{parent_node.id}_{node.name}"
        
        method_node = CodeNode(
            id=method_id,
            name=node.name,
            type=NodeType.METHOD,
            path=rel_path,
            language='python',
            start_line=node.lineno,
            end_line=node.end_lineno,
            description=self._get_docstring(node),
            metadata={'parent_class': parent_node.id}
        )
        
        self.nodes.append(method_node)
        
        # 创建包含关系
        self.edges.append(CodeEdge(
            id=f"edge_{parent_node.id}_contains_{method_id}",
            source=parent_node.id,
            target=method_id,
            type=EdgeType.CONTAINS
        ))
    
    def _analyze_javascript_file(self, file_path: Path, content: str, parent_node: CodeNode):
        """
        分析JavaScript/TypeScript文件（基础版本）
        
        Args:
            file_path: 文件路径
            content: 文件内容
            parent_node: 父节点
        """
        # 简单的正则匹配，提取import和function/class
        import re
        
        # 提取import语句
        import_pattern = r'import\s+.*?from\s+[\'"](.+?)[\'"]'
        imports = re.findall(import_pattern, content)
        
        # 提取函数
        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)'
        functions = re.findall(func_pattern, content)
        
        # 提取类
        class_pattern = r'(?:export\s+)?class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        
        # 更新元数据
        if parent_node.metadata is None:
            parent_node.metadata = {}
        parent_node.metadata['imports'] = imports
        parent_node.metadata['functions'] = functions
        parent_node.metadata['classes'] = classes
        
        # 创建简单的节点（不深入分析）
        rel_path = str(file_path.relative_to(self.repo_path))
        
        for cls_name in classes:
            class_id = f"class_{parent_node.id}_{cls_name}"
            class_node = CodeNode(
                id=class_id,
                name=cls_name,
                type=NodeType.CLASS,
                path=rel_path,
                language=parent_node.language,
                metadata={'parent_file': parent_node.id}
            )
            self.nodes.append(class_node)
            
            self.edges.append(CodeEdge(
                id=f"edge_{parent_node.id}_contains_{class_id}",
                source=parent_node.id,
                target=class_id,
                type=EdgeType.CONTAINS
            ))
        
        for func_name in functions:
            func_id = f"func_{parent_node.id}_{func_name}"
            func_node = CodeNode(
                id=func_id,
                name=func_name,
                type=NodeType.FUNCTION,
                path=rel_path,
                language=parent_node.language,
                metadata={'parent_file': parent_node.id}
            )
            self.nodes.append(func_node)
            
            self.edges.append(CodeEdge(
                id=f"edge_{parent_node.id}_contains_{func_id}",
                source=parent_node.id,
                target=func_id,
                type=EdgeType.CONTAINS
            ))
    
    def _analyze_dependencies(self):
        """
        分析依赖关系（导入关系）
        """
        logger.info("Analyzing dependencies...")
        
        for node in self.nodes:
            if node.type != NodeType.FILE:
                continue
            
            if not node.metadata or 'imports' not in node.metadata:
                continue
            
            imports = node.metadata['imports']
            
            for imp in imports:
                # 尝试解析导入路径
                target_node_id = self._resolve_import(imp, node.path)
                
                if target_node_id:
                    edge_id = f"edge_{node.id}_imports_{target_node_id}"
                    self.edges.append(CodeEdge(
                        id=edge_id,
                        source=node.id,
                        target=target_node_id,
                        type=EdgeType.IMPORT,
                        label=imp
                    ))
    
    def _resolve_import(self, import_path: str, current_file: str) -> Optional[str]:
        """
        解析导入路径到节点ID（增强版）
        
        Args:
            import_path: 导入路径
            current_file: 当前文件路径
            
        Returns:
            目标节点ID，如果找不到则返回None
        """
        import os
        
        # 1. 处理相对路径导入
        if import_path.startswith('.'):
            # 计算相对路径的绝对路径
            current_dir = os.path.dirname(current_file)
            # 移除开头的点
            rel_path = import_path.lstrip('.')
            # 处理 .. 和 . 路径
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
            
            # 构建可能的路径
            if import_path.startswith('..'):
                # 父目录
                parent_dir = os.path.dirname(current_dir)
                target_path = os.path.normpath(os.path.join(parent_dir, rel_path))
            else:
                # 当前目录
                target_path = os.path.normpath(os.path.join(current_dir, rel_path))
            
            # 尝试匹配文件路径
            for path, node_id in self.node_id_map.items():
                normalized_path = os.path.normpath(path)
                # 检查是否匹配（支持 .py, .js, .ts 等扩展名）
                if (normalized_path == target_path or 
                    normalized_path.startswith(target_path + os.sep) or
                    normalized_path.startswith(target_path + '.')):
                    return node_id
                
                # 检查是否是 __init__.py 的情况
                if target_path.endswith('__init__'):
                    init_path = target_path + '.py'
                    if normalized_path == init_path:
                        return node_id
        
        # 2. 处理绝对导入（项目内模块）
        # 将导入路径转换为文件路径格式
        import_parts = import_path.split('.')
        
        # 尝试多种匹配策略
        for path, node_id in self.node_id_map.items():
            path_normalized = path.replace('\\', '/').replace('/', '.')
            
            # 策略1: 直接匹配
            if import_path in path or path_normalized.endswith(import_path):
                return node_id
            
            # 策略2: 部分匹配（处理子模块）
            path_parts = path_normalized.split('.')
            if len(import_parts) <= len(path_parts):
                if path_parts[-len(import_parts):] == import_parts:
                    return node_id
            
            # 策略3: 文件名匹配（处理 from module import Class 的情况）
            file_name = os.path.basename(path).replace('.py', '').replace('.js', '').replace('.ts', '')
            if file_name in import_parts:
                return node_id
        
        # 3. 处理别名导入（如 import numpy as np）
        # 这里只返回 None，因为别名导入需要更复杂的解析
        
        return None
    
    def _get_docstring(self, node: Any) -> Optional[str]:
        """获取节点的文档字符串"""
        import ast
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                # 只返回第一行
                return docstring.split('\n')[0].strip()
        return None
    
    def _analyze_java_file(self, file_path: Path, content: str, parent_node: CodeNode):
        """
        分析Java文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            parent_node: 父节点（文件节点）
        """
        try:
            from api.parsers.java_parser import parse_java_file
            
            # 解析Java文件
            result = parse_java_file(content, str(file_path))
            
            # 更新文件节点元数据
            if parent_node.metadata is None:
                parent_node.metadata = {}
            parent_node.metadata['package'] = result.get('package', '')
            parent_node.metadata['imports'] = result.get('imports', [])
            
            rel_path = str(file_path.relative_to(self.repo_path))
            
            # 处理类定义
            for java_class in result.get('classes', []):
                class_id = f"class_{parent_node.id}_{java_class['name']}"
                
                # 创建类节点
                class_node = CodeNode(
                    id=class_id,
                    name=java_class['name'],
                    type=NodeType.INTERFACE if java_class.get('is_interface') else NodeType.CLASS,
                    path=rel_path,
                    language='java',
                    start_line=java_class.get('start_line'),
                    end_line=java_class.get('end_line'),
                    metadata={
                        'parent_file': parent_node.id,
                        'modifiers': java_class.get('modifiers', []),
                        'extends': java_class.get('extends'),
                        'implements': java_class.get('implements', []),
                        'is_enum': java_class.get('is_enum', False),
                        'is_annotation': java_class.get('is_annotation', False),
                        'package': result.get('package', '')
                    }
                )
                
                self.nodes.append(class_node)
                
                # 创建继承边
                if java_class.get('extends'):
                    parent_class_id = self._resolve_java_type(java_class['extends'], result.get('imports', []))
                    if parent_class_id:
                        edge_id = f"edge_{class_id}_inherits_{parent_class_id}"
                        self.edges.append(CodeEdge(
                            id=edge_id,
                            source=class_id,
                            target=parent_class_id,
                            type=EdgeType.INHERIT,
                            label=java_class['extends']
                        ))
                
                # 创建实现接口边
                for interface in java_class.get('implements', []):
                    interface_id = self._resolve_java_type(interface, result.get('imports', []))
                    if interface_id:
                        edge_id = f"edge_{class_id}_implements_{interface_id}"
                        self.edges.append(CodeEdge(
                            id=edge_id,
                            source=class_id,
                            target=interface_id,
                            type=EdgeType.IMPLEMENT,
                            label=interface
                        ))
                
                # 处理方法
                for method in java_class.get('methods', []):
                    method_id = f"method_{class_id}_{method['name']}"
                    
                    method_node = CodeNode(
                        id=method_id,
                        name=method['name'],
                        type=NodeType.FUNCTION,
                        path=rel_path,
                        language='java',
                        start_line=method.get('start_line'),
                        end_line=method.get('end_line'),
                        metadata={
                            'parent_class': class_id,
                            'modifiers': method.get('modifiers', []),
                            'return_type': method.get('return_type'),
                            'parameters': method.get('parameters', []),
                            'is_constructor': method.get('is_constructor', False),
                            'throws': method.get('throws', [])
                        }
                    )
                    
                    self.nodes.append(method_node)
                    
                    # 创建包含边（类包含方法）
                    edge_id = f"edge_{class_id}_contains_{method_id}"
                    self.edges.append(CodeEdge(
                        id=edge_id,
                        source=class_id,
                        target=method_id,
                        type=EdgeType.CONTAINS
                    ))
                
                # 处理字段
                for field in java_class.get('fields', []):
                    # 可以选择创建字段节点，或只记录在类元数据中
                    # 这里我们将字段信息添加到类元数据
                    if 'fields' not in class_node.metadata:
                        class_node.metadata['fields'] = []
                    class_node.metadata['fields'].append({
                        'name': field['name'],
                        'type': field['type'],
                        'modifiers': field.get('modifiers', [])
                    })
            
            # 创建import边
            for import_item in result.get('imports', []):
                target_id = self._resolve_import(import_item, str(file_path))
                if target_id:
                    edge_id = f"edge_{parent_node.id}_imports_{target_id}"
                    self.edges.append(CodeEdge(
                        id=edge_id,
                        source=parent_node.id,
                        target=target_id,
                        type=EdgeType.IMPORT,
                        label=import_item
                    ))

        except Exception as e:
            logger.warning(f"Error analyzing Java file {file_path}: {e}")
    
    def _analyze_go_file(self, file_path: Path, content: str, parent_node: CodeNode):
        """
        分析Go文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            parent_node: 父节点（文件节点）
        """
        try:
            from api.parsers.go_parser import parse_go_file
            
            # 解析Go文件
            result = parse_go_file(content, str(file_path))
            
            # 更新文件节点元数据
            if parent_node.metadata is None:
                parent_node.metadata = {}
            parent_node.metadata['package'] = result.get('package', '')
            parent_node.metadata['imports'] = result.get('imports', [])
            
            rel_path = str(file_path.relative_to(self.repo_path))
            
            # 处理结构体/接口
            for struct in result.get('structs', []):
                struct_id = f"struct_{parent_node.id}_{struct['name']}"
                
                struct_node = CodeNode(
                    id=struct_id,
                    name=struct['name'],
                    type=NodeType.INTERFACE if struct.get('is_interface') else NodeType.CLASS,
                    path=rel_path,
                    language='go',
                    start_line=struct.get('start_line'),
                    end_line=struct.get('end_line'),
                    metadata={
                        'parent_file': parent_node.id,
                        'is_interface': struct.get('is_interface', False),
                        'fields': struct.get('fields', []),
                        'package': result.get('package', '')
                    }
                )
                
                self.nodes.append(struct_node)
            
            # 处理函数/方法
            for function in result.get('functions', []):
                # 判断是函数还是方法
                receiver = function.get('receiver')
                if receiver:
                    # 这是一个方法，找到对应的结构体
                    receiver_type = receiver['type']
                    receiver_struct_id = f"struct_{parent_node.id}_{receiver_type}"
                    func_id = f"method_{receiver_struct_id}_{function['name']}"
                    parent_id = receiver_struct_id
                else:
                    # 这是一个函数
                    func_id = f"func_{parent_node.id}_{function['name']}"
                    parent_id = parent_node.id
                
                func_node = CodeNode(
                    id=func_id,
                    name=function['name'],
                    type=NodeType.FUNCTION,
                    path=rel_path,
                    language='go',
                    start_line=function.get('start_line'),
                    end_line=function.get('end_line'),
                    metadata={
                        'parent': parent_id,
                        'receiver': receiver,
                        'parameters': function.get('parameters', []),
                        'returns': function.get('returns', [])
                    }
                )
                
                self.nodes.append(func_node)
                
                # 如果是方法，创建包含边
                if receiver:
                    edge_id = f"edge_{parent_id}_contains_{func_id}"
                    self.edges.append(CodeEdge(
                        id=edge_id,
                        source=parent_id,
                        target=func_id,
                        type=EdgeType.CONTAINS
                    ))
            
            # 创建import边
            for import_item in result.get('imports', []):
                target_id = self._resolve_import(import_item, str(file_path))
                if target_id:
                    edge_id = f"edge_{parent_node.id}_imports_{target_id}"
                    self.edges.append(CodeEdge(
                        id=edge_id,
                        source=parent_node.id,
                        target=target_id,
                        type=EdgeType.IMPORT,
                        label=import_item
                    ))

        except Exception as e:
            logger.warning(f"Error analyzing Go file {file_path}: {e}")
    
    def _resolve_java_type(self, type_name: str, imports: List[str]) -> Optional[str]:
        """
        解析Java类型到节点ID
        
        Args:
            type_name: 类型名称
            imports: 导入列表
            
        Returns:
            节点ID，如果找不到则返回None
        """
        # 简化的类型解析：检查已知节点
        for node in self.nodes:
            if node.type in [NodeType.CLASS, NodeType.INTERFACE]:
                # 检查简单名称匹配
                if node.name == type_name:
                    return node.id
                # 检查完全限定名匹配
                if node.metadata and node.metadata.get('package'):
                    fqn = f"{node.metadata['package']}.{node.name}"
                    if fqn == type_name:
                        return node.id
        
        return None
    
    def generate_codemap_summary(self) -> Dict[str, Any]:
        """
        生成Codemap摘要，用于Wiki生成
        提供精简的结构化代码信息
        
        Returns:
            包含代码结构摘要的字典
        """
        summary = {
            'total_files': self.total_files,
            'total_classes': 0,
            'total_functions': 0,
            'total_lines': self.total_lines,
            'languages': list(self.language_stats.keys()),
            'language_distribution': dict(self.language_stats),
            'key_modules': [],
            'architecture_layers': {},
            'dependencies': [],
            'architecture_modules': [],
            'inter_module_relationships': []
        }
        
        # 统计类和函数
        class_nodes = []
        function_nodes = []
        
        for node in self.nodes:
            if node.type in [NodeType.CLASS, NodeType.INTERFACE]:
                summary['total_classes'] += 1
                class_nodes.append(node)
            elif node.type == NodeType.FUNCTION:
                summary['total_functions'] += 1
                function_nodes.append(node)
        
        # 提取关键模块信息（前50个重要的类）
        for node in class_nodes[:50]:
            module_info = {
                'name': node.name,
                'type': 'interface' if node.type == NodeType.INTERFACE else 'class',
                'file': node.path,
                'language': node.language or 'unknown'
            }
            
            # 提取方法列表
            methods = []
            for n in self.nodes:
                if (n.type == NodeType.FUNCTION and 
                    n.metadata and 
                    (n.metadata.get('parent_class') == node.id or 
                     n.metadata.get('parent') == node.id)):
                    methods.append(n.name)
            
            if methods:
                module_info['methods'] = methods[:10]  # 限制为前10个方法
            
            # 提取继承和实现信息
            if node.metadata:
                extends = node.metadata.get('extends')
                if extends:
                    module_info['extends'] = extends
                
                implements = node.metadata.get('implements')
                if implements:
                    module_info['implements'] = implements if isinstance(implements, list) else [implements]
                
                # 添加字段信息
                fields = node.metadata.get('fields')
                if fields:
                    module_info['field_count'] = len(fields)
            
            summary['key_modules'].append(module_info)
        
        # 识别架构层次
        summary['architecture_layers'] = self._identify_architecture_layers(class_nodes)
        
        # 提取重要依赖关系（限制为前100个）
        summary['dependencies'] = self._extract_key_dependencies(limit=100)

        # 识别模块化架构（优先 Maven pom.xml 多模块）
        module_architecture = self._identify_architecture_modules(class_nodes, function_nodes)
        summary['architecture_modules'] = module_architecture.get('modules', [])
        summary['inter_module_relationships'] = module_architecture.get('relationships', [])
        summary['module_system'] = module_architecture.get('module_system')
        summary['module_count'] = len(summary['architecture_modules'])
        summary['has_multi_module_architecture'] = summary['module_count'] > 1
        
        logger.info(f"Generated codemap summary: {summary['total_classes']} classes, "
                   f"{summary['total_functions']} functions in {summary['total_files']} files")
        
        return summary

    def _identify_architecture_modules(
        self,
        class_nodes: List[CodeNode],
        function_nodes: List[CodeNode]
    ) -> Dict[str, Any]:
        """
        识别仓库的架构模块信息。
        优先从 Maven pom.xml 读取模块定义，并结合代码依赖构建模块关系。
        """
        root_pom = self.repo_path / "pom.xml"
        if not root_pom.exists():
            return {
                "module_system": "none",
                "modules": [],
                "relationships": [],
            }

        root_meta = self._parse_pom_metadata(root_pom)
        module_paths = root_meta.get("modules", [])
        if not module_paths:
            return {
                "module_system": "maven-single",
                "modules": [],
                "relationships": [],
            }

        file_nodes = [n for n in self.nodes if n.type == NodeType.FILE]
        class_count_by_path: Dict[str, int] = {}
        function_count_by_path: Dict[str, int] = {}
        for n in class_nodes:
            class_count_by_path[n.path] = class_count_by_path.get(n.path, 0) + 1
        for n in function_nodes:
            function_count_by_path[n.path] = function_count_by_path.get(n.path, 0) + 1

        modules: List[Dict[str, Any]] = []
        artifact_to_module: Dict[str, str] = {}

        for module_path in module_paths:
            module_dir = self.repo_path / module_path
            module_pom = module_dir / "pom.xml"
            module_meta = self._parse_pom_metadata(module_pom)

            module_name = module_meta.get("artifact_id") or module_path.replace("/", "-")
            module_type = module_meta.get("packaging") or "jar"
            artifact_id = module_meta.get("artifact_id")
            if artifact_id:
                artifact_to_module[artifact_id] = module_name

            file_count = 0
            class_count = 0
            function_count = 0
            language_distribution: Dict[str, int] = {}

            module_prefix = module_path.replace("\\", "/").rstrip("/") + "/"
            for file_node in file_nodes:
                file_path = (file_node.path or "").replace("\\", "/")
                if not file_path.startswith(module_prefix):
                    continue
                file_count += 1
                if file_node.language:
                    language_distribution[file_node.language] = language_distribution.get(file_node.language, 0) + 1
                class_count += class_count_by_path.get(file_node.path, 0)
                function_count += function_count_by_path.get(file_node.path, 0)

            module_info = {
                "id": f"module_{module_path.replace('/', '_')}",
                "name": module_name,
                "path": module_path,
                "artifact_id": artifact_id,
                "packaging": module_type,
                "declared_dependencies": module_meta.get("dependencies", []),
                "file_count": file_count,
                "class_count": class_count,
                "function_count": function_count,
                "languages": sorted(list(language_distribution.keys())),
                "language_distribution": language_distribution,
            }
            modules.append(module_info)

        relationships = self._extract_inter_module_relationships(modules, artifact_to_module)
        return {
            "module_system": "maven-multi",
            "modules": modules,
            "relationships": relationships,
        }

    def _parse_pom_metadata(self, pom_path: Path) -> Dict[str, Any]:
        """解析 pom.xml 元数据（兼容 namespace）。"""
        if not pom_path.exists():
            return {"artifact_id": None, "packaging": None, "modules": [], "dependencies": []}

        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()

            def tag_endswith(elem, name: str) -> bool:
                return isinstance(elem.tag, str) and elem.tag.endswith(name)

            def first_child_text(parent, child_name: str) -> Optional[str]:
                for child in list(parent):
                    if tag_endswith(child, child_name):
                        text = (child.text or "").strip()
                        return text or None
                return None

            artifact_id = first_child_text(root, "artifactId")
            packaging = first_child_text(root, "packaging") or "jar"

            modules: List[str] = []
            dependencies: List[str] = []

            for child in list(root):
                if tag_endswith(child, "modules"):
                    for module_el in list(child):
                        if tag_endswith(module_el, "module"):
                            module_name = (module_el.text or "").strip()
                            if module_name:
                                modules.append(module_name)
                elif tag_endswith(child, "dependencies"):
                    for dep_el in list(child):
                        if not tag_endswith(dep_el, "dependency"):
                            continue
                        dep_artifact = first_child_text(dep_el, "artifactId")
                        if dep_artifact:
                            dependencies.append(dep_artifact)

            return {
                "artifact_id": artifact_id,
                "packaging": packaging,
                "modules": modules,
                "dependencies": dependencies,
            }
        except Exception as e:
            logger.warning(f"Failed to parse pom.xml {pom_path}: {e}")
            return {"artifact_id": None, "packaging": None, "modules": [], "dependencies": []}

    def _extract_inter_module_relationships(
        self,
        modules: List[Dict[str, Any]],
        artifact_to_module: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """提取跨模块关系：pom 依赖 + 代码层 import/call 关系。"""
        if not modules:
            return []

        module_name_by_path = {m["path"].replace("\\", "/").rstrip("/"): m["name"] for m in modules}
        module_paths = sorted(module_name_by_path.keys(), key=len, reverse=True)

        def resolve_module_name(file_path: str) -> Optional[str]:
            normalized = (file_path or "").replace("\\", "/")
            for module_path in module_paths:
                prefix = module_path + "/"
                if normalized == module_path or normalized.startswith(prefix):
                    return module_name_by_path[module_path]
            return None

        rel_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for module in modules:
            source_name = module["name"]
            for dep_artifact in module.get("declared_dependencies", []):
                target_name = artifact_to_module.get(dep_artifact)
                if not target_name or target_name == source_name:
                    continue
                key = (source_name, target_name)
                if key not in rel_map:
                    rel_map[key] = {
                        "from_module": source_name,
                        "to_module": target_name,
                        "pom_dependency": False,
                        "code_edges": 0,
                        "edge_types": {},
                    }
                rel_map[key]["pom_dependency"] = True

        node_by_id = {n.id: n for n in self.nodes}
        for edge in self.edges:
            source_node = node_by_id.get(edge.source)
            target_node = node_by_id.get(edge.target)
            if not source_node or not target_node:
                continue

            source_module = resolve_module_name(source_node.path)
            target_module = resolve_module_name(target_node.path)
            if not source_module or not target_module or source_module == target_module:
                continue

            key = (source_module, target_module)
            if key not in rel_map:
                rel_map[key] = {
                    "from_module": source_module,
                    "to_module": target_module,
                    "pom_dependency": False,
                    "code_edges": 0,
                    "edge_types": {},
                }

            rel_map[key]["code_edges"] += 1
            edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
            edge_types = rel_map[key]["edge_types"]
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        relationships = list(rel_map.values())
        relationships.sort(key=lambda r: (r["code_edges"], r["pom_dependency"]), reverse=True)
        return relationships[:100]
    
    def _identify_architecture_layers(self, class_nodes: List[CodeNode]) -> Dict[str, List[str]]:
        """
        识别常见的架构层次（增强版：结合命名规则和依赖关系）
        
        Args:
            class_nodes: 类节点列表
            
        Returns:
            架构层次字典
        """
        layers = {
            'controllers': [],
            'services': [],
            'models': [],
            'repositories': [],
            'utils': [],
            'middleware': [],
            'config': [],
            'views': [],
            'handlers': []
        }
        
        # 构建节点ID到节点的映射
        node_map = {node.id: node for node in class_nodes}
        
        # 统计每个节点的依赖关系
        node_dependencies = {node.id: {'imports': 0, 'imported_by': 0, 'depends_on_models': False, 
                                       'depends_on_services': False, 'depends_on_repos': False} 
                            for node in class_nodes}
        
        # 分析依赖关系
        for edge in self.edges:
            if edge.type == EdgeType.IMPORT:
                source_node = next((n for n in self.nodes if n.id == edge.source), None)
                target_node = next((n for n in self.nodes if n.id == edge.target), None)
                
                if source_node and target_node and source_node.id in node_map and target_node.id in node_map:
                    node_dependencies[source_node.id]['imports'] += 1
                    node_dependencies[target_node.id]['imported_by'] += 1
                    
                    # 检查依赖类型
                    target_name_lower = target_node.name.lower()
                    target_path_lower = target_node.path.lower() if target_node.path else ''
                    
                    if 'model' in target_name_lower or 'entity' in target_name_lower or 'model' in target_path_lower:
                        node_dependencies[source_node.id]['depends_on_models'] = True
                    if 'service' in target_name_lower or 'service' in target_path_lower:
                        node_dependencies[source_node.id]['depends_on_services'] = True
                    if 'repository' in target_name_lower or 'repo' in target_name_lower or 'dao' in target_name_lower:
                        node_dependencies[source_node.id]['depends_on_repos'] = True
        
        # 基于命名、路径和依赖关系识别层次
        for node in class_nodes:
            name_lower = node.name.lower()
            path_lower = node.path.lower() if node.path else ''
            deps = node_dependencies.get(node.id, {})
            
            # Controllers: 通常导入 services，很少被导入
            if (('controller' in name_lower or 'controller' in path_lower) or
                (deps.get('depends_on_services') and deps.get('imported_by', 0) > 2)):
                layers['controllers'].append(node.name)
            # Services: 通常导入 models/repos，被 controllers 导入
            elif (('service' in name_lower or 'service' in path_lower) or
                  (deps.get('depends_on_models') or deps.get('depends_on_repos'))):
                layers['services'].append(node.name)
            # Models: 很少导入其他类，被 services/repos 导入
            elif (('model' in name_lower or 'entity' in name_lower or 'model' in path_lower or 'entity' in path_lower) or
                  (deps.get('imports', 0) < 3 and deps.get('imported_by', 0) > 2)):
                layers['models'].append(node.name)
            # Repositories: 通常导入 models，被 services 导入
            elif (('repository' in name_lower or 'dao' in name_lower or 'repo' in path_lower) or
                  (deps.get('depends_on_models') and deps.get('imported_by', 0) > 1)):
                layers['repositories'].append(node.name)
            # Utils: 被多个模块导入，但很少导入其他模块
            elif (('util' in path_lower or 'helper' in name_lower or 'utils' in path_lower) or
                  (deps.get('imports', 0) < 2 and deps.get('imported_by', 0) > 3)):
                layers['utils'].append(node.name)
            # Middleware: 在特定路径
            elif 'middleware' in path_lower or 'middleware' in name_lower:
                layers['middleware'].append(node.name)
            # Config: 在配置路径
            elif 'config' in path_lower or 'configuration' in name_lower:
                layers['config'].append(node.name)
            # Views: 视图层
            elif 'view' in name_lower or 'views' in path_lower:
                layers['views'].append(node.name)
            # Handlers: 处理器
            elif 'handler' in name_lower or 'handlers' in path_lower:
                layers['handlers'].append(node.name)
        
        # 移除空层次
        return {k: v for k, v in layers.items() if v}
    
    def _extract_key_dependencies(self, limit: int = 100) -> List[Dict[str, str]]:
        """
        提取关键依赖关系
        
        Args:
            limit: 最大返回数量
            
        Returns:
            依赖关系列表
        """
        deps = []
        
        for edge in self.edges[:limit]:
            # 找到源和目标节点
            source_node = next((n for n in self.nodes if n.id == edge.source), None)
            target_node = next((n for n in self.nodes if n.id == edge.target), None)
            
            if source_node and target_node:
                dep = {
                    'from': source_node.name,
                    'to': target_node.name,
                    'type': edge.type.value if hasattr(edge.type, 'value') else str(edge.type),
                    'from_file': source_node.path,
                    'to_file': target_node.path
                }
                
                # 添加语言信息
                if source_node.language:
                    dep['from_language'] = source_node.language
                if target_node.language:
                    dep['to_language'] = target_node.language
                
                deps.append(dep)
        
        return deps

    def _add_containment_edges(self):
        """添加包含关系边（目录包含文件/子目录，文件包含类和函数）"""
        logger.info("Adding containment edges...")

        # 1. 处理目录包含关系
        directory_nodes = {node.path: node for node in self.nodes if node.type == NodeType.DIRECTORY}
        file_nodes = {node.path: node for node in self.nodes if node.type == NodeType.FILE}

        # 目录包含文件和子目录
        for node in self.nodes:
            if node.type in [NodeType.DIRECTORY, NodeType.FILE]:
                # 获取节点的父目录路径
                node_path = node.path
                # 查找直接父目录（不是递归查找所有祖先）
                parent_path = os.path.dirname(node_path)

                # 如果有父目录且父目录存在于节点中
                if parent_path and parent_path in directory_nodes:
                    parent_node = directory_nodes[parent_path]
                    edge_id = f"edge_{parent_node.id}_contains_{node.id}"

                    # 避免重复边
                    if not any(e.id == edge_id for e in self.edges):
                        self.edges.append(CodeEdge(
                            id=edge_id,
                            source=parent_node.id,
                            target=node.id,
                            type=EdgeType.CONTAINS,
                            label="contains"
                        ))

        # 2. 处理文件包含类和函数
        for node in self.nodes:
            # 类和函数应该被它们的文件包含
            if node.type in [NodeType.CLASS, NodeType.FUNCTION, NodeType.METHOD, NodeType.INTERFACE]:
                # 找到包含此节点的文件
                file_node = file_nodes.get(node.path)

                if file_node:
                    edge_id = f"edge_{file_node.id}_contains_{node.id}"

                    # 避免重复边
                    if not any(e.id == edge_id for e in self.edges):
                        self.edges.append(CodeEdge(
                            id=edge_id,
                            source=file_node.id,
                            target=node.id,
                            type=EdgeType.CONTAINS,
                            label="contains"
                        ))

        logger.info(f"Added containment edges (including directory containment)")

    def _add_inheritance_edges(self):
        """添加继承关系边"""
        logger.info("Adding inheritance edges...")

        for node in self.nodes:
            if node.type != NodeType.CLASS:
                continue

            # 检查元数据中的基类信息
            if not node.metadata or 'base_classes' not in node.metadata:
                continue

            base_classes = node.metadata['base_classes']

            for base_class in base_classes:
                # 查找基类节点
                base_node = None
                for n in self.nodes:
                    if n.type == NodeType.CLASS and n.name == base_class:
                        base_node = n
                        break

                if base_node:
                    edge_id = f"edge_{node.id}_inherits_{base_node.id}"
                    self.edges.append(CodeEdge(
                        id=edge_id,
                        source=node.id,
                        target=base_node.id,
                        type=EdgeType.INHERIT,
                        label="inherits"
                    ))

        logger.info(f"Added inheritance edges")

    def _build_call_graph(self):
        """构建调用图，添加函数调用关系边"""
        logger.info("Building call graph for edges...")

        try:
            from api.call_graph_analyzer import CallGraphAnalyzer

            # 创建调用图分析器
            call_analyzer = CallGraphAnalyzer(self)

            # 构建调用图
            call_analyzer.build_call_graph()

            # 注意：CallGraphAnalyzer.build_call_graph() 已经将边添加到 self.edges
            # 所以我们不需要手动添加

            logger.info(f"Call graph built and edges added")

        except Exception as e:
            logger.warning(f"Failed to build call graph: {e}")
            # 即使调用图构建失败，也继续其他分析


def analyze_repository(repo_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    分析代码仓库
    
    Args:
        repo_path: 仓库路径
        options: 分析选项
        
    Returns:
        代码地图字典
    """
    analyzer = CodeAnalyzer(repo_path, options)
    codemap = analyzer.analyze()
    return codemap.to_dict()


def save_codemap(codemap: Dict[str, Any], output_path: str):
    """
    保存代码地图到文件
    
    Args:
        codemap: 代码地图
        output_path: 输出路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(codemap, f, indent=2, ensure_ascii=False)
    
    logger.info(f"CodeMap saved to {output_path}")


def load_codemap(input_path: str) -> Dict[str, Any]:
    """
    从文件加载代码地图
    
    Args:
        input_path: 输入路径
        
    Returns:
        代码地图字典
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)

