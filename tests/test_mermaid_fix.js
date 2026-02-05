/**
 * 测试Mermaid语法修复逻辑
 */

// 测试用例集合
const testCases = [
  {
    name: 'Case 1: autonumber with comma and bracket',
    code: `sequenceDiagram
    participant User
    participant Service
    autonumber    , [item-circulation-service] 查询流转记录
    User->>+Service: 发起请求`,
    expected: /^sequenceDiagram[\s\S]*autonumber\s*$/m
  },
  {
    name: 'Case 2: arrow with comma and bracket',
    code: `sequenceDiagram
    User->>Service: Request, [note] some comment
    Service->>User, [backend] Response`,
    expected: /User->>Service: Request\s*\n/
  },
  {
    name: 'Case 3: deactivate with comma',
    code: `sequenceDiagram
    activate Service
    deactivate, [cleanup] Service`,
    expected: /deactivate\s*$/m
  }
];

// 应用清理逻辑（从Mermaid.tsx复制最新版本）
function cleanMermaidCode(chart) {
  return chart
    // 移除 Sources: [filename]() 格式的引用
    .replace(/Sources:\s*\[[^\]]+\]\(\)/g, '')
    // 移除单独的 Markdown 链接格式
    .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
    // 移除可能的中文括号和特殊字符导致的解析问题
    .replace(/[（(]Sources:[^）)]+[）)]/g, '')

    // === 修复序列图常见语法错误 ===
    // 修复: autonumber 后面跟逗号和方括号
    .replace(/(\s*autonumber\s*),\s*\[.*$/gm, '$1')
    // 修复: participant 后面跟逗号
    .replace(/(participant\s+\w+)\s*,\s*\[.*$/gm, '$1')
    // 修复: 箭头后面跟逗号
    .replace(/(->>[\+\-]?[^:]*):([^,]*),\s*\[[^\]]*\](.*)$/gm, '$1:$2')
    // 更简单的箭头修复
    .replace(/(->>[\+\-]?\s*\w+\s*:\s*[^,\n]*),\s*\[[^\]]*\]/g, '$1')
    // 修复: 任何Mermaid关键字后跟 ", [" 的错误模式
    .replace(/(activate|deactivate|loop|alt|opt|par|and|else|end)\s*,\s*\[.*$/gm, '$1')

    // === 修复箭头语法错误 ===
    .replace(/([A-Za-z0-9_]+)\s*,\s*(->>?[\+\-]?)/g, '$1$2')

    // === 清理孤立的方括号残留 ===
    .replace(/^\s*[^\s\w-]+\].*/gm, '')
    .replace(/^\s*\w+\]\s+.*/gm, '')

    // === 清理方括号内的无效内容 ===
    .replace(/^\s*,?\s*\[.*?\].*$/gm, '')
    .replace(/,\s*\[[^\]]+\]/g, '')

    // === 清理无效的逗号 ===
    .replace(/,\s*$/gm, '')
    .replace(/^\s*,/gm, '')

    // === 最终清理 ===
    .replace(/^\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// 运行测试
console.log('=== Running Mermaid Syntax Fix Tests ===\n');

let passedTests = 0;
let failedTests = 0;

testCases.forEach((testCase, index) => {
  console.log(`--- Test ${index + 1}: ${testCase.name} ---`);
  console.log('Original:');
  console.log(testCase.code);
  console.log('\nCleaned:');

  const cleaned = cleanMermaidCode(testCase.code);
  console.log(cleaned);

  // 验证
  const issues = [];
  const lines = cleaned.split('\n');
  lines.forEach((line, idx) => {
    if (/,\s*\[/.test(line)) {
      issues.push(`Line ${idx + 1}: comma before bracket: "${line}"`);
    }
    if (/^\s*\w+\]/.test(line)) {
      issues.push(`Line ${idx + 1}: orphaned bracket: "${line}"`);
    }
  });

  if (issues.length === 0) {
    console.log('✅ PASSED: No syntax issues');
    passedTests++;
  } else {
    console.log('❌ FAILED: Issues found:');
    issues.forEach(issue => console.log('  -', issue));
    failedTests++;
  }
  console.log('\n');
});

console.log('=== Summary ===');
console.log(`Passed: ${passedTests}/${testCases.length}`);
console.log(`Failed: ${failedTests}/${testCases.length}`);

if (failedTests === 0) {
  console.log('\n🎉 All tests passed!');
} else {
  console.log('\n⚠️  Some tests failed. Review the logic.');
}
