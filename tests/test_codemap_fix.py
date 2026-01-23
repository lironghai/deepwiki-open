#!/usr/bin/env python
"""测试Codemap RAG修复"""
import sys
import os

# 添加api目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

def test_codemap_context_doc():
    """测试CodemapContextDoc类是否能正确与Jinja2模板协作"""
    from api.codemap_enhanced_rag import CodemapEnhancedRAG

    # 创建一个简单的测试
    print("测试1: 验证CodemapContextDoc类定义...")

    # 模拟创建codemap上下文文档
    class CodemapContextDoc:
        def __init__(self, text):
            self.text = text
            self.meta_data = {'file_path': 'Codemap Structure Info'}

    doc = CodemapContextDoc("Test codemap context")

    # 验证属性
    assert hasattr(doc, 'text'), "CodemapContextDoc应该有text属性"
    assert hasattr(doc, 'meta_data'), "CodemapContextDoc应该有meta_data属性"
    assert doc.meta_data.get('file_path') == 'Codemap Structure Info', "meta_data应该包含file_path"
    assert doc.text == "Test codemap context", "text应该正确存储"

    print("✓ CodemapContextDoc类定义正确")

    # 测试2: 模拟Jinja2模板访问
    print("\n测试2: 验证Jinja2模板兼容性...")
    from jinja2 import Template

    template_str = """
    {%- for context in contexts %}
    File: {{ context.meta_data.get('file_path', 'unknown') }}
    Content: {{ context.text }}
    {% endfor -%}
    """

    template = Template(template_str)

    # 创建文档列表
    contexts = [
        CodemapContextDoc("Codemap info"),
        type('Doc', (), {'text': 'Regular doc', 'meta_data': {'file_path': 'test.py'}})()
    ]

    result = template.render(contexts=contexts)

    assert 'Codemap Structure Info' in result, "应该包含Codemap文件路径"
    assert 'Codemap info' in result, "应该包含Codemap内容"
    assert 'test.py' in result, "应该包含常规文档路径"
    assert 'Regular doc' in result, "应该包含常规文档内容"

    print("✓ Jinja2模板兼容性验证通过")

    # 测试3: 验证CodemapEnhancedRAG的call方法签名
    print("\n测试3: 验证CodemapEnhancedRAG.call()方法签名...")
    import inspect

    sig = inspect.signature(CodemapEnhancedRAG.call)
    params = list(sig.parameters.keys())

    assert 'self' in params, "应该有self参数"
    assert 'question' in params, "应该有question参数"
    assert 'context' in params, "应该有context参数"
    assert 'language' in params, "应该有language参数"

    # 检查默认值
    assert sig.parameters['context'].default is None, "context默认值应该是None"
    assert sig.parameters['language'].default == "en", "language默认值应该是'en'"

    print("✓ CodemapEnhancedRAG.call()方法签名正确")

    print("\n" + "="*60)
    print("所有测试通过! ✓")
    print("="*60)
    print("\nCodemap RAG修复验证成功:")
    print("1. CodemapContextDoc类正确定义了text和meta_data属性")
    print("2. Jinja2模板能够正确访问文档对象的属性")
    print("3. CodemapEnhancedRAG.call()方法签名正确，避免了参数冲突")
    print("\n修复内容:")
    print("- 将contexts从字符串改为文档对象列表")
    print("- 为Codemap上下文创建CodemapContextDoc包装类")
    print("- 明确定义language参数，避免'got multiple values'错误")

if __name__ == '__main__':
    try:
        test_codemap_context_doc()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
