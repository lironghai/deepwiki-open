"""
Go代码解析器
使用正则表达式解析Go代码结构
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GoStruct:
    """Go结构体信息"""
    name: str
    fields: List['GoField']
    start_line: int
    end_line: int
    is_interface: bool


@dataclass
class GoFunction:
    """Go函数/方法信息"""
    name: str
    receiver: Optional[Tuple[str, str]]  # (receiver_name, receiver_type)
    parameters: List[Tuple[str, str]]  # (name, type)
    returns: List[str]  # return types
    start_line: int
    end_line: int


@dataclass
class GoField:
    """Go字段信息"""
    name: str
    field_type: str
    tag: Optional[str]


class GoParser:
    """Go代码解析器"""
    
    def __init__(self, content: str, file_path: str):
        """
        初始化Go解析器
        
        Args:
            content: Go源代码内容
            file_path: 文件路径
        """
        self.content = content
        self.file_path = file_path
        self.lines = content.splitlines()
        self.package = ""
        self.imports = []
        self.structs = []
        self.functions = []
    
    def parse(self) -> Dict[str, Any]:
        """
        解析Go代码
        
        Returns:
            解析结果字典
        """
        try:
            # 提取package声明
            self._extract_package()
            
            # 提取imports
            self._extract_imports()
            
            # 提取结构体
            self._extract_structs()
            
            # 提取函数
            self._extract_functions()
            
            return {
                'package': self.package,
                'imports': self.imports,
                'structs': [self._struct_to_dict(s) for s in self.structs],
                'functions': [self._function_to_dict(f) for f in self.functions]
            }
        except Exception as e:
            logger.error(f"Error parsing Go file {self.file_path}: {e}")
            return {
                'package': '',
                'imports': [],
                'structs': [],
                'functions': []
            }
    
    def _extract_package(self):
        """提取package声明"""
        package_pattern = r'package\s+(\w+)'
        for line in self.lines:
            match = re.match(package_pattern, line.strip())
            if match:
                self.package = match.group(1)
                break
    
    def _extract_imports(self):
        """提取import语句"""
        in_import_block = False
        import_pattern = r'import\s+"([^"]+)"'
        import_block_pattern = r'import\s+\('
        
        for line in self.lines:
            line = line.strip()
            
            # 检测import块开始
            if re.match(import_block_pattern, line):
                in_import_block = True
                continue
            
            # 检测import块结束
            if in_import_block and line == ')':
                in_import_block = False
                continue
            
            # 在import块中
            if in_import_block:
                match = re.match(r'"([^"]+)"', line)
                if match:
                    self.imports.append(match.group(1))
            else:
                # 单行import
                match = re.match(import_pattern, line)
                if match:
                    self.imports.append(match.group(1))
    
    def _extract_structs(self):
        """提取结构体和接口定义"""
        # 匹配: type StructName struct {
        struct_pattern = r'type\s+(\w+)\s+(struct|interface)\s*\{'
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            match = re.match(struct_pattern, line)
            if match:
                struct_name = match.group(1)
                is_interface = match.group(2) == 'interface'
                start_line = i + 1
                
                # 找到结构体结束位置
                end_line = self._find_block_end(i)
                
                # 提取字段
                fields = self._extract_struct_fields(i + 1, end_line, is_interface)
                
                go_struct = GoStruct(
                    name=struct_name,
                    fields=fields,
                    start_line=start_line,
                    end_line=end_line,
                    is_interface=is_interface
                )
                
                self.structs.append(go_struct)
                i = end_line
            else:
                i += 1
    
    def _extract_struct_fields(self, start: int, end: int, is_interface: bool) -> List[GoField]:
        """提取结构体字段或接口方法"""
        fields = []
        
        for i in range(start, end):
            line = self.lines[i].strip()
            
            # 跳过空行和注释
            if not line or line.startswith('//'):
                continue
            
            if is_interface:
                # 接口方法: MethodName(params) returns
                method_pattern = r'(\w+)\s*\(([^\)]*)\)(?:\s*\(([^\)]*)\)|(?:\s+(\w+))?)'
                match = re.match(method_pattern, line)
                if match:
                    method_name = match.group(1)
                    # 接口方法作为特殊字段存储
                    field = GoField(
                        name=method_name,
                        field_type='method',
                        tag=None
                    )
                    fields.append(field)
            else:
                # 结构体字段: FieldName FieldType `tag`
                field_pattern = r'(\w+)\s+([\w\.\[\]\*]+)(?:\s+`([^`]*)`)?'
                match = re.match(field_pattern, line)
                if match:
                    field_name = match.group(1)
                    field_type = match.group(2)
                    field_tag = match.group(3)
                    
                    field = GoField(
                        name=field_name,
                        field_type=field_type,
                        tag=field_tag
                    )
                    fields.append(field)
        
        return fields
    
    def _extract_functions(self):
        """提取函数和方法定义"""
        # 函数模式: func (receiver) FuncName(params) (returns) {
        # 或: func FuncName(params) returns {
        func_pattern = r'func\s+(?:\((\w+)\s+\*?(\w+)\)\s+)?(\w+)\s*\(([^\)]*)\)(?:\s*\(([^\)]*)\)|(?:\s+(\w+))?)'
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            match = re.match(func_pattern, line)
            if match:
                receiver_name = match.group(1)
                receiver_type = match.group(2)
                func_name = match.group(3)
                params_str = match.group(4)
                returns_paren = match.group(5)  # 多返回值
                returns_single = match.group(6)  # 单返回值
                
                start_line = i + 1
                
                # 解析接收者
                receiver = None
                if receiver_name and receiver_type:
                    receiver = (receiver_name, receiver_type)
                
                # 解析参数
                parameters = self._parse_parameters(params_str)
                
                # 解析返回值
                if returns_paren:
                    returns = [r.strip() for r in returns_paren.split(',') if r.strip()]
                elif returns_single:
                    returns = [returns_single]
                else:
                    returns = []
                
                # 找到函数结束位置
                end_line = self._find_block_end(i)
                
                go_function = GoFunction(
                    name=func_name,
                    receiver=receiver,
                    parameters=parameters,
                    returns=returns,
                    start_line=start_line,
                    end_line=end_line
                )
                
                self.functions.append(go_function)
                i = end_line
            else:
                i += 1
    
    def _parse_parameters(self, params_str: str) -> List[Tuple[str, str]]:
        """解析函数参数"""
        if not params_str or not params_str.strip():
            return []
        
        parameters = []
        # Go参数格式: name1, name2 type 或 name type
        
        # 简单处理：按逗号分割
        parts = params_str.split(',')
        for part in parts:
            part = part.strip()
            if part:
                # 最后一个空格分隔名称和类型
                tokens = part.rsplit(None, 1)
                if len(tokens) == 2:
                    name, param_type = tokens
                    parameters.append((name, param_type))
                elif len(tokens) == 1:
                    # 只有类型，没有名称
                    parameters.append(('', tokens[0]))
        
        return parameters
    
    def _find_block_end(self, start_line: int) -> int:
        """找到代码块的结束位置（匹配花括号）"""
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
    
    def _struct_to_dict(self, go_struct: GoStruct) -> Dict[str, Any]:
        """将GoStruct转换为字典"""
        return {
            'name': go_struct.name,
            'fields': [self._field_to_dict(f) for f in go_struct.fields],
            'start_line': go_struct.start_line,
            'end_line': go_struct.end_line,
            'is_interface': go_struct.is_interface
        }
    
    def _function_to_dict(self, go_function: GoFunction) -> Dict[str, Any]:
        """将GoFunction转换为字典"""
        return {
            'name': go_function.name,
            'receiver': {
                'name': go_function.receiver[0],
                'type': go_function.receiver[1]
            } if go_function.receiver else None,
            'parameters': [{'name': n, 'type': t} for n, t in go_function.parameters],
            'returns': go_function.returns,
            'start_line': go_function.start_line,
            'end_line': go_function.end_line
        }
    
    def _field_to_dict(self, field: GoField) -> Dict[str, Any]:
        """将GoField转换为字典"""
        return {
            'name': field.name,
            'type': field.field_type,
            'tag': field.tag
        }


def parse_go_file(content: str, file_path: str) -> Dict[str, Any]:
    """
    解析Go文件的便捷函数
    
    Args:
        content: Go源代码内容
        file_path: 文件路径
        
    Returns:
        解析结果字典
    """
    parser = GoParser(content, file_path)
    return parser.parse()

