#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析wiki数据中的mermaid语法错误
"""
import json
import re
import sys

def analyze_mermaid_errors(wiki_url):
    """分析mermaid错误"""
    import urllib.request

    # 下载数据
    print(f"Fetching data from {wiki_url}...")
    with urllib.request.urlopen(wiki_url) as response:
        data = json.loads(response.read().decode('utf-8'))

    pages = data.get('structure', {}).get('pages', [])
    print(f"Total pages: {len(pages)}")

    # 提取mermaid块
    mermaid_blocks = []
    for page in pages:
        content = page.get('content', '')
        # 匹配mermaid代码块
        blocks = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)
        for block in blocks:
            mermaid_blocks.append({
                'page_id': page.get('id', ''),
                'page_title': page.get('title', 'Unknown'),
                'code': block
            })

    print(f"Total mermaid blocks: {len(mermaid_blocks)}")
    print()

    # 查找常见错误模式
    error_patterns = [
        (r'autonumber.*,', 'autonumber followed by comma'),
        (r'participant.*,\s*\[', 'participant with comma before bracket'),
        (r'->>.*,\s*\[', 'arrow with comma before bracket'),
        (r'\s+,\s+\[', 'comma before bracket (generic)'),
    ]

    errors_found = []

    for i, block in enumerate(mermaid_blocks):
        lines = block['code'].split('\n')

        for line_no, line in enumerate(lines, 1):
            for pattern, desc in error_patterns:
                if re.search(pattern, line):
                    errors_found.append({
                        'block_index': i,
                        'page': block['page_title'],
                        'line_no': line_no,
                        'line': line.strip(),
                        'error_type': desc,
                        'context': '\n'.join(lines[max(0,line_no-2):min(len(lines),line_no+2)])
                    })

    print(f"=== Found {len(errors_found)} potential errors ===\n")

    # 显示前10个错误
    for error in errors_found[:10]:
        print(f"Error in '{error['page']}' (Block #{error['block_index']+1}, Line {error['line_no']})")
        print(f"  Type: {error['error_type']}")
        print(f"  Line: {error['line'][:120]}")
        print(f"  Context:")
        for ctx_line in error['context'].split('\n'):
            print(f"    {ctx_line[:100]}")
        print()

    # 统计错误类型
    error_type_counts = {}
    for error in errors_found:
        error_type = error['error_type']
        error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

    print("=== Error Type Statistics ===")
    for error_type, count in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type}: {count}")

if __name__ == '__main__':
    wiki_url = "http://xxxxm/api/wiki_cache"
    analyze_mermaid_errors(wiki_url)
