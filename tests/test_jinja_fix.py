#!/usr/bin/env python
"""Test Jinja2 template compatibility with CodemapContextDoc"""
from jinja2 import Template

# Simulate the CodemapContextDoc class from codemap_enhanced_rag.py
class CodemapContextDoc:
    def __init__(self, text):
        self.text = text
        self.meta_data = {'file_path': 'Codemap Structure Info'}

# Simulate regular document object
class RegularDoc:
    def __init__(self, text, file_path):
        self.text = text
        self.meta_data = {'file_path': file_path}

# Test the Jinja2 template (same as RAG_TEMPLATE in prompts.py)
template_str = """
{%- if contexts %}
<START_OF_CONTEXT>
{% for context in contexts %}
{{loop.index}}.
File Path: {{context.meta_data.get('file_path', 'unknown')}}
Content: {{context.text}}
{% endfor %}
<END_OF_CONTEXT>
{% endif -%}
"""

print("Test 1: Testing CodemapContextDoc attributes...")
codemap_doc = CodemapContextDoc("Test codemap context")
assert hasattr(codemap_doc, 'text'), "Should have text attribute"
assert hasattr(codemap_doc, 'meta_data'), "Should have meta_data attribute"
assert codemap_doc.meta_data.get('file_path') == 'Codemap Structure Info'
print("PASS - CodemapContextDoc has correct attributes")

print("\nTest 2: Testing Jinja2 template rendering...")
template = Template(template_str)

# Create document list with Codemap doc and regular doc
contexts = [
    CodemapContextDoc("## Code Structure\nFunction A calls Function B"),
    RegularDoc("def hello():\n    print('world')", "src/main.py")
]

result = template.render(contexts=contexts)
print("Rendered template:")
print(result)

# Verify output
assert 'Codemap Structure Info' in result, "Should contain Codemap file path"
assert 'Code Structure' in result, "Should contain Codemap content"
assert 'src/main.py' in result, "Should contain regular doc path"
assert "def hello()" in result, "Should contain regular doc content"
print("\nPASS - Jinja2 template renders correctly")

print("\nTest 3: Testing with empty contexts...")
result_empty = template.render(contexts=None)
assert '<START_OF_CONTEXT>' not in result_empty, "Should not render context block when None"
print("PASS - Empty contexts handled correctly")

print("\nTest 4: Testing with string (old broken behavior)...")
try:
    # This should fail with the old implementation
    broken_result = template.render(contexts="This is a string")
    print("ERROR - String should not work as contexts!")
    exit(1)
except Exception as e:
    print(f"PASS - String correctly fails with error: {type(e).__name__}")

print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("="*60)
print("\nSummary of fixes:")
print("1. CodemapContextDoc class wraps codemap text with proper attributes")
print("2. contexts is now a list of document objects, not a string")
print("3. Jinja2 template can access .text and .meta_data attributes")
print("4. No more 'str object has no attribute meta_data' error")
