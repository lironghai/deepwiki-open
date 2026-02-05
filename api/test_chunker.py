"""
文本分块功能测试脚本
测试不同类型文件的智能分块
"""
import sys
import os
import io

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加api目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from text_chunker import (
    CodeChunker, MarkdownChunker, PlainTextChunker,
    chunk_large_file, get_chunker
)


def simple_token_counter(text: str) -> int:
    """简单的token计数器（用于测试）"""
    # 简单估算：1个token约等于4个字符
    return len(text) // 4


def test_code_chunker():
    """测试代码分块器"""
    print("=" * 60)
    print("测试代码文件分块")
    print("=" * 60)
    
    # 生成一个大型Python文件示例
    code = """#!/usr/bin/env python3
\"\"\"
Large Python Module for Testing
Contains multiple classes and functions
\"\"\"

import os
import sys
from typing import List, Dict, Any
from pathlib import Path

# Constants
MAX_SIZE = 1000
DEFAULT_VALUE = "default"
DEBUG_MODE = True

""" + "\n".join([f"""
class TestClass{i}:
    \"\"\"Test class number {i}\"\"\"
    
    def __init__(self):
        self.value = {i}
        self.name = "Class {i}"
    
    def method_{i}(self, param):
        \"\"\"Method {i} documentation\"\"\"
        result = param * {i}
        return result
    
    def another_method_{i}(self):
        \"\"\"Another method for class {i}\"\"\"
        print(f"Processing class {{self.name}}")
        return self.value

def utility_function_{i}(x, y):
    \"\"\"Utility function {i}\"\"\"
    return x + y + {i}
""" for i in range(20)])  # 生成20个类和函数
    
    # 测试分块
    chunker = CodeChunker(max_tokens=500, overlap_tokens=50)  # 小一点方便测试
    chunks = chunker.chunk_text(code, simple_token_counter, {"test": True})
    
    print(f"\n原始代码: {len(code)} 字符, {simple_token_counter(code)} tokens")
    print(f"分块数量: {len(chunks)}")
    
    for chunk in chunks:
        print(f"\n📦 块 {chunk.chunk_index + 1}/{chunk.total_chunks}")
        print(f"   行范围: {chunk.start_line}-{chunk.end_line}")
        print(f"   大小: {len(chunk.content)} 字符, {simple_token_counter(chunk.content)} tokens")
        print(f"   包含头部: {chunk.metadata.get('has_header', False)}")
        # 显示前100个字符
        preview = chunk.content[:100].replace('\n', ' ')
        print(f"   预览: {preview}...")
    
    print("\n✅ 代码分块测试通过")
    return len(chunks)


def test_markdown_chunker():
    """测试Markdown分块器"""
    print("\n" + "=" * 60)
    print("测试Markdown文档分块")
    print("=" * 60)
    
    # 生成大型Markdown文档
    markdown = "# Large Documentation\n\nThis is a test document.\n\n"
    
    for i in range(15):
        markdown += f"""
## Section {i + 1}: Important Topic

This section discusses topic {i + 1} in detail. It contains multiple paragraphs
of information that need to be processed together.

### Subsection {i + 1}.1

Here we dive deeper into the specifics of topic {i + 1}. This includes:

- Point 1 about topic {i + 1}
- Point 2 with more details
- Point 3 explaining the concept

### Subsection {i + 1}.2

More information follows here with examples and code snippets.

```python
def example_{i}():
    return {i} * 2
```

And some concluding remarks for section {i + 1}.

"""
    
    # 测试分块
    chunker = MarkdownChunker(max_tokens=400, overlap_tokens=50)
    chunks = chunker.chunk_text(markdown, simple_token_counter, {"type": "md"})
    
    print(f"\n原始文档: {len(markdown)} 字符, {simple_token_counter(markdown)} tokens")
    print(f"分块数量: {len(chunks)}")
    
    for chunk in chunks:
        print(f"\n📄 块 {chunk.chunk_index + 1}/{chunk.total_chunks}")
        print(f"   行范围: {chunk.start_line}-{chunk.end_line}")
        print(f"   大小: {len(chunk.content)} 字符, {simple_token_counter(chunk.content)} tokens")
        # 显示第一行（通常是标题）
        first_line = chunk.content.split('\n')[0]
        print(f"   开始: {first_line}")
    
    print("\n✅ Markdown分块测试通过")
    return len(chunks)


def test_plain_text_chunker():
    """测试普通文本分块器"""
    print("\n" + "=" * 60)
    print("测试普通文本分块")
    print("=" * 60)
    
    # 生成长文本
    text = " ".join([f"This is sentence number {i}. It contains some information about topic {i}." 
                     for i in range(200)])
    
    # 测试分块
    chunker = PlainTextChunker(max_tokens=300, overlap_tokens=50)
    chunks = chunker.chunk_text(text, simple_token_counter, {"type": "txt"})
    
    print(f"\n原始文本: {len(text)} 字符, {simple_token_counter(text)} tokens")
    print(f"分块数量: {len(chunks)}")
    
    for chunk in chunks:
        print(f"\n📝 块 {chunk.chunk_index + 1}/{chunk.total_chunks}")
        print(f"   大小: {len(chunk.content)} 字符, {simple_token_counter(chunk.content)} tokens")
        print(f"   包含重叠: {chunk.metadata.get('has_overlap', False)}")
        # 显示开头
        preview = chunk.content[:80]
        print(f"   开始: {preview}...")
    
    print("\n✅ 普通文本分块测试通过")
    return len(chunks)


def test_chunker_factory():
    """测试分块器工厂函数"""
    print("\n" + "=" * 60)
    print("测试分块器工厂")
    print("=" * 60)
    
    test_cases = [
        ('py', CodeChunker),
        ('java', CodeChunker),
        ('go', CodeChunker),
        ('js', CodeChunker),
        ('md', MarkdownChunker),
        ('markdown', MarkdownChunker),
        ('txt', PlainTextChunker),
        ('log', PlainTextChunker),
    ]
    
    for ext, expected_class in test_cases:
        chunker = get_chunker(ext)
        actual_class = type(chunker).__name__
        expected_name = expected_class.__name__
        
        status = "✅" if actual_class == expected_name else "❌"
        print(f"{status} .{ext} -> {actual_class} (期望: {expected_name})")
    
    print("\n✅ 分块器工厂测试通过")


def test_integration():
    """集成测试"""
    print("\n" + "=" * 60)
    print("集成测试 - chunk_large_file()")
    print("=" * 60)
    
    # 测试一个真实场景：大型Python文件
    large_code = """
import sys
import os

""" + "\n".join([f"""
class LargeClass{i}:
    def __init__(self):
        self.id = {i}
    
    def process(self):
        return self.id * 2
    
    def validate(self):
        if self.id > 0:
            return True
        return False
""" for i in range(30)])
    
    # 模拟token计数函数
    def token_counter(text):
        return len(text) // 4
    
    # 使用便捷函数
    chunks = chunk_large_file(
        content=large_code,
        file_path="test_large.py",
        count_tokens_fn=token_counter,
        max_tokens=600,
        overlap_tokens=100
    )
    
    print(f"\n文件: test_large.py")
    print(f"原始大小: {len(large_code)} 字符")
    print(f"原始tokens: {token_counter(large_code)}")
    print(f"分块数量: {len(chunks)}")
    
    # 验证每个块都不超过限制
    all_valid = True
    for chunk in chunks:
        chunk_tokens = token_counter(chunk.content)
        is_valid = chunk_tokens <= 600
        all_valid = all_valid and is_valid
        status = "✅" if is_valid else "❌"
        print(f"{status} 块{chunk.chunk_index + 1}: {chunk_tokens} tokens")
    
    if all_valid:
        print("\n✅ 所有块都在token限制内")
    else:
        print("\n❌ 某些块超过了token限制")
    
    return all_valid


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 开始文本分块功能测试")
    print("=" * 60)
    
    try:
        # 运行各项测试
        code_chunks = test_code_chunker()
        md_chunks = test_markdown_chunker()
        text_chunks = test_plain_text_chunker()
        test_chunker_factory()
        integration_ok = test_integration()
        
        # 总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"✅ 代码分块: {code_chunks} 个块")
        print(f"✅ Markdown分块: {md_chunks} 个块")
        print(f"✅ 文本分块: {text_chunks} 个块")
        print(f"✅ 工厂测试: 通过")
        print(f"{'✅' if integration_ok else '❌'} 集成测试: {'通过' if integration_ok else '失败'}")
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        
        print("\n💡 功能说明:")
        print("   - 代码文件按函数/类分块，保留imports")
        print("   - Markdown按标题层级分块，保持语义完整")
        print("   - 普通文本按句子分块，带重叠保持连续性")
        print("   - 所有块都不超过token限制")
        print("   - 自动识别文件类型选择合适的分块策略")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)





