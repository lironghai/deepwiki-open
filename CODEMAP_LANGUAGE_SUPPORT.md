# Codemap 语言支持详解

本文档详细说明Codemap功能对不同编程语言的支持程度和提取的代码结构信息。

## 📋 支持语言总览

| 语言 | 支持级别 | 解析方式 | 提取内容 |
|------|---------|---------|---------|
| Python | ⭐⭐⭐ 深度支持 | AST (内置) | 类、函数、导入、继承 |
| Java | ⭐⭐⭐ 深度支持 | 自定义解析器 | 类、接口、枚举、方法、字段、继承、实现 |
| Go | ⭐⭐⭐ 深度支持 | 自定义解析器 | 结构体、接口、函数、方法、字段标签 |
| JavaScript | ⭐⭐ 基础支持 | 文件级别 | 文件结构 |
| TypeScript | ⭐⭐ 基础支持 | 文件级别 | 文件结构 |
| 其他语言 | ⭐ 识别支持 | 文件级别 | 文件结构 |

---

## 🐍 Python 支持

### 解析方式
使用Python内置的 `ast` (Abstract Syntax Tree) 模块进行深度语法分析。

### 提取内容

#### 1. 类定义 (Class)
```python
class MyClass(BaseClass):
    """类文档字符串"""
    pass
```
**提取信息**：
- 类名
- 基类（继承关系）
- 文档字符串
- 起止行号

#### 2. 函数定义 (Function)
```python
def my_function(param1: str, param2: int) -> bool:
    """函数文档字符串"""
    return True
```
**提取信息**：
- 函数名
- 参数列表
- 返回类型（如果有类型注解）
- 文档字符串
- 起止行号

#### 3. 导入语句 (Import)
```python
import os
from typing import List, Dict
```
**提取信息**：
- 导入的模块名
- 建立模块间依赖关系

#### 4. 关系边 (Edges)
- **继承关系** (INHERITS): 类 -> 基类
- **导入关系** (IMPORTS): 文件 -> 模块
- **包含关系** (CONTAINS): 类 -> 方法, 文件 -> 类/函数

---

## ☕ Java 支持

### 解析方式
使用自定义正则表达式解析器 (`api/parsers/java_parser.py`)，基于语法模式匹配。

### 提取内容

#### 1. 包声明
```java
package com.example.myapp;
```
**提取信息**：包名

#### 2. 导入语句
```java
import java.util.List;
import com.example.Utils;
```
**提取信息**：
- 导入的类/包
- 建立依赖关系

#### 3. 类定义
```java
public class MyClass extends BaseClass implements Interface1, Interface2 {
    // ...
}
```
**提取信息**：
- 类名
- 修饰符 (public, abstract, final, static)
- 继承的父类
- 实现的接口
- 包名
- 起止行号

#### 4. 接口定义
```java
public interface MyInterface {
    void method();
}
```
**提取信息**：
- 接口名
- 修饰符
- 方法签名

#### 5. 枚举定义
```java
public enum Status {
    ACTIVE, INACTIVE, PENDING
}
```
**提取信息**：
- 枚举名
- 修饰符
- 枚举值（作为字段）

#### 6. 方法定义
```java
public static String myMethod(int param1, String param2) throws IOException {
    return "result";
}
```
**提取信息**：
- 方法名
- 修饰符 (public, private, static, final, synchronized等)
- 返回类型
- 参数列表（类型和名称）
- 抛出的异常
- 起止行号
- 是否为构造函数

#### 7. 字段定义
```java
private static final String CONSTANT = "value";
private List<String> items;
```
**提取信息**：
- 字段名
- 修饰符
- 类型
- 默认值（如果有）

#### 8. 关系边
- **继承关系** (INHERITS): 类 -> 父类
- **实现关系** (IMPLEMENTS): 类 -> 接口
- **导入关系** (IMPORTS): 文件 -> 导入的类
- **包含关系** (CONTAINS): 类 -> 方法

### Java解析器能力

✅ **支持**：
- 类、接口、枚举、注解类型
- 方法和构造函数
- 字段
- 泛型类型（基本识别）
- 修饰符
- 继承和实现关系
- 异常声明

⚠️ **限制**：
- 不解析方法体内的调用关系
- 不处理复杂的泛型嵌套
- 不解析注解的详细内容

---

## 🔷 Go 支持

### 解析方式
使用自定义正则表达式解析器 (`api/parsers/go_parser.py`)，基于Go语法模式。

### 提取内容

#### 1. 包声明
```go
package main
```
**提取信息**：包名

#### 2. 导入语句
```go
import (
    "fmt"
    "github.com/user/package"
)
```
**提取信息**：
- 导入的包路径
- 建立依赖关系

#### 3. 结构体定义
```go
type MyStruct struct {
    Name string `json:"name"`
    Age  int    `json:"age"`
}
```
**提取信息**：
- 结构体名
- 字段名、类型
- 字段标签 (struct tags)
- 起止行号

#### 4. 接口定义
```go
type MyInterface interface {
    Method1(param string) error
    Method2() int
}
```
**提取信息**：
- 接口名
- 方法签名
- 起止行号

#### 5. 函数定义
```go
func MyFunction(param1 string, param2 int) (string, error) {
    return "result", nil
}
```
**提取信息**：
- 函数名
- 参数列表（名称和类型）
- 返回值类型
- 起止行号

#### 6. 方法定义（带Receiver）
```go
func (s *MyStruct) MyMethod(param string) error {
    return nil
}
```
**提取信息**：
- 方法名
- Receiver（名称和类型）
- 参数列表
- 返回值类型
- 起止行号

#### 7. 关系边
- **导入关系** (IMPORTS): 文件 -> 包
- **包含关系** (CONTAINS): 结构体 -> 方法

### Go解析器能力

✅ **支持**：
- 结构体和接口
- 函数和方法
- 字段和标签
- 单/多返回值
- Receiver类型识别

⚠️ **限制**：
- 不解析函数体内的调用
- 不处理类型别名的复杂情况
- 不解析嵌入字段的详细关系

---

## 🎯 扩展支持计划

### 短期计划
- **TypeScript/JavaScript**: 使用 `@babel/parser` 进行AST解析
  - 类、函数、导入/导出
  - ES6模块系统
  - JSX/TSX支持

### 中期计划
- **C/C++**: 使用 `libclang` 或 `tree-sitter`
  - 类、函数、头文件
  - 命名空间
  - 模板

- **Rust**: 使用 `syn` crate或正则解析
  - 结构体、trait、impl
  - 模块系统
  - 生命周期标注

### 长期计划
- **Kotlin**, **Swift**, **C#** 等语言支持
- 更深入的语义分析（调用图、数据流）

---

## 🔧 如何添加新语言支持

### 方法1: 使用正则表达式解析器（简单）

1. 在 `api/parsers/` 目录创建 `{language}_parser.py`
2. 定义数据模型（使用 `@dataclass`）：
   ```python
   @dataclass
   class LanguageClass:
       name: str
       fields: List[Field]
       methods: List[Method]
   ```

3. 实现解析器类：
   ```python
   class LanguageParser:
       def __init__(self, content: str, file_path: str):
           self.content = content
           self.file_path = file_path
       
       def parse(self) -> Dict[str, Any]:
           # 提取类、函数、导入等
           return {...}
   ```

4. 在 `code_analyzer.py` 中集成：
   ```python
   elif language == 'your_language':
       self._analyze_your_language_file(file_path, content, file_node)
   ```

### 方法2: 使用AST解析器（复杂但精确）

1. 安装语言的AST解析库
2. 遍历AST节点提取结构
3. 转换为标准的 `CodeNode` 和 `CodeEdge`

---

## 📚 参考资料

- **Python AST**: https://docs.python.org/3/library/ast.html
- **Java语法**: https://docs.oracle.com/javase/specs/
- **Go语法**: https://golang.org/ref/spec
- **ReactFlow文档**: https://reactflow.dev/

---

## 🤝 贡献

欢迎提交PR添加新语言支持或改进现有解析器！

提交前请确保：
1. 添加单元测试
2. 更新本文档
3. 测试实际项目的解析效果

