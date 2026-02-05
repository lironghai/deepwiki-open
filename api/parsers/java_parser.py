"""
Java代码解析器
使用正则表达式和简单的语法分析解析Java代码
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JavaClass:
    """Java类信息"""
    name: str
    package: str
    modifiers: List[str]
    extends: Optional[str]
    implements: List[str]
    start_line: int
    end_line: int
    is_interface: bool
    is_enum: bool
    is_annotation: bool
    methods: List['JavaMethod']
    fields: List['JavaField']


@dataclass
class JavaMethod:
    """Java方法信息"""
    name: str
    modifiers: List[str]
    return_type: str
    parameters: List[Tuple[str, str]]  # (type, name)
    start_line: int
    end_line: int
    is_constructor: bool
    throws: List[str]


@dataclass
class JavaField:
    """Java字段信息"""
    name: str
    modifiers: List[str]
    field_type: str
    start_line: int
    default_value: Optional[str]


class JavaParser:
    """Java代码解析器"""
    
    # 修饰符关键字
    MODIFIERS = {'public', 'private', 'protected', 'static', 'final', 'abstract', 
                 'synchronized', 'volatile', 'transient', 'native', 'strictfp'}
    
    # 基本类型
    PRIMITIVE_TYPES = {'byte', 'short', 'int', 'long', 'float', 'double', 'char', 'boolean', 'void'}
    
    def __init__(self, content: str, file_path: str):
        """
        初始化Java解析器
        
        Args:
            content: Java源代码内容
            file_path: 文件路径
        """
        self.content = content
        self.file_path = file_path
        self.lines = content.splitlines()
        self.package = ""
        self.imports = []
        self.classes = []
        
    def parse(self) -> Dict[str, Any]:
        """
        解析Java代码
        
        Returns:
            解析结果字典
        """
        try:
            # 提取package声明
            self._extract_package()
            
            # 提取imports
            self._extract_imports()
            
            # 提取类定义
            self._extract_classes()
            
            return {
                'package': self.package,
                'imports': self.imports,
                'classes': [self._class_to_dict(cls) for cls in self.classes]
            }
        except Exception as e:
            logger.error(f"Error parsing Java file {self.file_path}: {e}")
            return {
                'package': '',
                'imports': [],
                'classes': []
            }
    
    def _extract_package(self):
        """提取package声明"""
        package_pattern = r'package\s+([\w\.]+)\s*;'
        for line in self.lines:
            match = re.match(package_pattern, line.strip())
            if match:
                self.package = match.group(1)
                break
    
    def _extract_imports(self):
        """提取import语句"""
        import_pattern = r'import\s+(?:static\s+)?([\w\.\*]+)\s*;'
        for line in self.lines:
            match = re.match(import_pattern, line.strip())
            if match:
                self.imports.append(match.group(1))
    
    def _extract_classes(self):
        """提取类定义"""
        # 匹配类/接口/枚举/注解声明
        class_pattern = r'((?:public|private|protected|static|final|abstract)\s+)*' + \
                       r'(class|interface|enum|@interface)\s+' + \
                       r'(\w+)' + \
                       r'(?:\s+extends\s+([\w\.<>, ]+))?' + \
                       r'(?:\s+implements\s+([\w\.<>, ]+))?'
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            # 跳过注释和空行
            if not line or line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                i += 1
                continue
            
            match = re.search(class_pattern, line)
            if match:
                modifiers_str = match.group(1) or ''
                modifiers = [m for m in modifiers_str.split() if m in self.MODIFIERS]
                
                class_type = match.group(2)
                class_name = match.group(3)
                extends = match.group(4).strip() if match.group(4) else None
                implements_str = match.group(5)
                implements = [impl.strip() for impl in implements_str.split(',')] if implements_str else []
                
                # 找到类的结束位置
                start_line = i + 1
                end_line = self._find_class_end(i)
                
                # 提取方法和字段
                methods = self._extract_methods(i, end_line)
                fields = self._extract_fields(i, end_line)
                
                java_class = JavaClass(
                    name=class_name,
                    package=self.package,
                    modifiers=modifiers,
                    extends=extends,
                    implements=implements,
                    start_line=start_line,
                    end_line=end_line,
                    is_interface=class_type == 'interface',
                    is_enum=class_type == 'enum',
                    is_annotation=class_type == '@interface',
                    methods=methods,
                    fields=fields
                )
                
                self.classes.append(java_class)
                i = end_line
            else:
                i += 1
    
    def _find_class_end(self, start_line: int) -> int:
        """
        找到类定义的结束行
        通过匹配花括号
        """
        brace_count = 0
        found_opening = False
        
        for i in range(start_line, len(self.lines)):
            line = self.lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return i + 1
        
        return len(self.lines)
    
    def _extract_methods(self, class_start: int, class_end: int) -> List[JavaMethod]:
        """提取方法定义"""
        methods = []
        
        # 方法模式：修饰符 返回类型 方法名(参数) throws 异常
        method_pattern = r'((?:public|private|protected|static|final|abstract|synchronized|native)\s+)*' + \
                        r'(?:<[\w\s,<>?]+>\s+)?' + \
                        r'([\w\.<>\[\]]+)\s+' + \
                        r'(\w+)\s*\(' + \
                        r'([^\)]*)\)' + \
                        r'(?:\s+throws\s+([\w\s,]+))?'
        
        i = class_start
        while i < class_end:
            line = self.lines[i].strip()
            
            # 跳过注释
            if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                i += 1
                continue
            
            match = re.search(method_pattern, line)
            if match and ('{' in line or (i + 1 < len(self.lines) and '{' in self.lines[i + 1])):
                modifiers_str = match.group(1) or ''
                modifiers = [m for m in modifiers_str.split() if m in self.MODIFIERS]
                
                return_type = match.group(2)
                method_name = match.group(3)
                params_str = match.group(4)
                throws_str = match.group(5)
                
                # 解析参数
                parameters = self._parse_parameters(params_str)
                
                # 解析throws
                throws = [t.strip() for t in throws_str.split(',')] if throws_str else []
                
                # 找到方法结束行
                method_start = i + 1
                method_end = self._find_method_end(i, class_end)
                
                # 判断是否为构造函数
                is_constructor = return_type == method_name
                
                method = JavaMethod(
                    name=method_name,
                    modifiers=modifiers,
                    return_type=return_type if not is_constructor else '',
                    parameters=parameters,
                    start_line=method_start,
                    end_line=method_end,
                    is_constructor=is_constructor,
                    throws=throws
                )
                
                methods.append(method)
                i = method_end
            else:
                i += 1
        
        return methods
    
    def _parse_parameters(self, params_str: str) -> List[Tuple[str, str]]:
        """解析方法参数"""
        if not params_str or not params_str.strip():
            return []
        
        parameters = []
        # 简单分割（不处理泛型中的逗号）
        for param in params_str.split(','):
            param = param.strip()
            if param:
                # 移除注解
                param = re.sub(r'@\w+(?:\([^\)]*\))?\s+', '', param)
                # 移除final
                param = param.replace('final ', '')
                
                parts = param.rsplit(None, 1)
                if len(parts) == 2:
                    param_type, param_name = parts
                    # 移除可变参数的...
                    param_type = param_type.replace('...', '[]')
                    parameters.append((param_type, param_name))
        
        return parameters
    
    def _find_method_end(self, start_line: int, class_end: int) -> int:
        """找到方法的结束行"""
        brace_count = 0
        found_opening = False
        
        for i in range(start_line, class_end):
            line = self.lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return i + 1
        
        return class_end
    
    def _extract_fields(self, class_start: int, class_end: int) -> List[JavaField]:
        """提取字段定义"""
        fields = []
        
        # 字段模式：修饰符 类型 字段名 = 默认值;
        field_pattern = r'((?:public|private|protected|static|final|volatile|transient)\s+)+' + \
                       r'([\w\.<>\[\]]+)\s+' + \
                       r'(\w+)' + \
                       r'(?:\s*=\s*([^;]+))?' + \
                       r'\s*;'
        
        for i in range(class_start, class_end):
            line = self.lines[i].strip()
            
            # 跳过注释和方法定义
            if line.startswith('//') or line.startswith('/*') or line.startswith('*') or '(' in line:
                continue
            
            match = re.search(field_pattern, line)
            if match:
                modifiers_str = match.group(1)
                modifiers = [m for m in modifiers_str.split() if m in self.MODIFIERS]
                
                field_type = match.group(2)
                field_name = match.group(3)
                default_value = match.group(4).strip() if match.group(4) else None
                
                field = JavaField(
                    name=field_name,
                    modifiers=modifiers,
                    field_type=field_type,
                    start_line=i + 1,
                    default_value=default_value
                )
                
                fields.append(field)
        
        return fields
    
    def _class_to_dict(self, java_class: JavaClass) -> Dict[str, Any]:
        """将JavaClass转换为字典"""
        return {
            'name': java_class.name,
            'package': java_class.package,
            'modifiers': java_class.modifiers,
            'extends': java_class.extends,
            'implements': java_class.implements,
            'start_line': java_class.start_line,
            'end_line': java_class.end_line,
            'is_interface': java_class.is_interface,
            'is_enum': java_class.is_enum,
            'is_annotation': java_class.is_annotation,
            'methods': [self._method_to_dict(m) for m in java_class.methods],
            'fields': [self._field_to_dict(f) for f in java_class.fields]
        }
    
    def _method_to_dict(self, method: JavaMethod) -> Dict[str, Any]:
        """将JavaMethod转换为字典"""
        return {
            'name': method.name,
            'modifiers': method.modifiers,
            'return_type': method.return_type,
            'parameters': [{'type': t, 'name': n} for t, n in method.parameters],
            'start_line': method.start_line,
            'end_line': method.end_line,
            'is_constructor': method.is_constructor,
            'throws': method.throws
        }
    
    def _field_to_dict(self, field: JavaField) -> Dict[str, Any]:
        """将JavaField转换为字典"""
        return {
            'name': field.name,
            'modifiers': field.modifiers,
            'type': field.field_type,
            'start_line': field.start_line,
            'default_value': field.default_value
        }


def parse_java_file(content: str, file_path: str) -> Dict[str, Any]:
    """
    解析Java文件的便捷函数
    
    Args:
        content: Java源代码内容
        file_path: 文件路径
        
    Returns:
        解析结果字典
    """
    parser = JavaParser(content, file_path)
    return parser.parse()

