# Sources 链接修复总结

## 问题描述

项目 wiki 中的 Sources 链接都是空的，例如：
```markdown
Sources: [values.yaml:40-48](), [ads-log-monitor/src/main/resources/bootstrap.yml:3]()
```

括号内没有 URL，导致用户无法点击跳转到源文件。

## 根本原因

1. **提示模板要求 LLM 生成空链接**（`src/app/[owner]/[repo]/page.tsx:596`）：
   ```
   Use the exact format: `Sources: [filename.ext:start_line-end_line]()`
   ```

2. **没有后处理逻辑填充这些空链接**：
   - LLM 遵循指示，生成空括号的链接
   - 内容生成后直接存储，没有 URL 填充步骤
   - 虽然已有 `generateFileUrl()` 函数可以生成正确的 URL，但未被使用

## 修复方案

### 1. 新增 `fillSourceUrls()` 函数

在 `src/app/[owner]/[repo]/page.tsx:330-406` 添加函数：

```typescript
const fillSourceUrls = useCallback((content: string): string => {
  // 匹配形如 [filename.ext:lines]() 的空链接
  const sourcePattern = /\[([^\]]+?\.[\w]+(?::\d+(?:-\d+)?)?)\]\(\)/g;

  return content.replace(sourcePattern, (match, fileRef) => {
    // 提取文件路径和行号信息
    const colonIndex = fileRef.indexOf(':');
    const filePath = colonIndex >= 0 ? fileRef.substring(0, colonIndex) : fileRef;
    const lineInfo = colonIndex >= 0 ? fileRef.substring(colonIndex) : '';

    // 生成文件 URL
    const fileUrl = generateFileUrl(filePath);

    // 添加行号锚点（根据仓库类型）
    let fullUrl = fileUrl;
    if (lineInfo && effectiveRepoInfo.type !== 'local') {
      const lineMatch = lineInfo.match(/:(\d+)(?:-(\d+))?/);
      if (lineMatch) {
        const startLine = lineMatch[1];
        const endLine = lineMatch[2] || startLine;

        try {
          const url = new URL(effectiveRepoInfo.repoUrl || '');
          const hostname = url.hostname;

          if (hostname === 'github.com' || hostname.includes('github')) {
            // GitHub: #L40-L48
            fullUrl = `${fileUrl}#L${startLine}${endLine !== startLine ? `-L${endLine}` : ''}`;
          } else if (hostname === 'gitlab.com' || hostname.includes('gitlab')) {
            // GitLab: #L40-48
            fullUrl = `${fileUrl}#L${startLine}${endLine !== startLine ? `-${endLine}` : ''}`;
          } else if (hostname === 'bitbucket.org' || hostname.includes('bitbucket')) {
            // Bitbucket: #lines-40:48
            fullUrl = `${fileUrl}#lines-${startLine}${endLine !== startLine ? `:${endLine}` : ''}`;
          }
        } catch (error) {
          console.warn('Error adding line anchors:', error);
        }
      }
    }

    return `[${fileRef}](${fullUrl})`;
  });
}, [generateFileUrl, effectiveRepoInfo]);
```

### 2. 在内容处理流程中调用

在 `src/app/[owner]/[repo]/page.tsx:822` 添加调用：

```typescript
// Clean up markdown delimiters
content = content.replace(/^```markdown\s*/i, '').replace(/```\s*$/i, '');

// Fill empty source citation URLs with proper repository file links
content = fillSourceUrls(content);

console.log(`Received content for ${page.title}, length: ${content.length} characters`);
```

### 3. 更新 React Hook 依赖

修复 `useCallback` 依赖警告（第 827 行）：

```typescript
}, [generatedPages, currentToken, effectiveRepoInfo, ..., fillSourceUrls, codemapSummary]);
```

## 修复效果

### 修复前
```markdown
Sources: [values.yaml:40-48](), [bootstrap.yml:3]()
```
**问题**：括号为空，无法点击跳转

### 修复后

#### GitHub 仓库
```markdown
Sources: [values.yaml:40-48](https://github.com/owner/repo/blob/main/values.yaml#L40-L48),
         [bootstrap.yml:3](https://github.com/owner/repo/blob/main/bootstrap.yml#L3)
```

#### GitLab 仓库
```markdown
Sources: [values.yaml:40-48](https://gitlab.com/owner/repo/-/blob/main/values.yaml#L40-48),
         [bootstrap.yml:3](https://gitlab.com/owner/repo/-/blob/main/bootstrap.yml#L3)
```

#### Bitbucket 仓库
```markdown
Sources: [values.yaml:40-48](https://bitbucket.org/owner/repo/src/main/values.yaml#lines-40:48),
         [bootstrap.yml:3](https://bitbucket.org/owner/repo/src/main/bootstrap.yml#lines-3)
```

## 支持的链接格式

函数能正确处理以下所有格式：

1. **带行号范围**：`[file.ext:10-20]()` → 带锚点的 URL
2. **单行号**：`[file.ext:15]()` → 带单行锚点的 URL
3. **无行号**：`[file.ext]()` → 基础文件 URL
4. **嵌套路径**：`[dir/subdir/file.ext:5-10]()` → 完整路径 + 锚点

## 行号锚点格式

不同代码托管平台有不同的行号锚点格式：

| 平台 | 单行 | 范围 |
|------|------|------|
| **GitHub** | `#L10` | `#L10-L20` |
| **GitLab** | `#L10` | `#L10-20` |
| **Bitbucket** | `#lines-10` | `#lines-10:20` |

## 测试验证

测试用例验证：

```javascript
Input:  "Sources: [values.yaml:40-48](), [bootstrap.yml:3]()"

Output: "Sources: [values.yaml:40-48](https://github.com/owner/repo/blob/main/values.yaml#L40-L48),
                   [bootstrap.yml:3](https://github.com/owner/repo/blob/main/bootstrap.yml#L3)"
```

✅ 所有格式正确匹配和转换
✅ 行号锚点正确生成
✅ 路径正确处理（包括嵌套目录）

## 相关文件

- `src/app/[owner]/[repo]/page.tsx` - Wiki 页面组件
  - 第 330-406 行：`fillSourceUrls()` 函数
  - 第 822 行：调用点
  - 第 292-329 行：`generateFileUrl()` 辅助函数

## 影响范围

- ✅ 所有新生成的 wiki 页面
- ✅ 支持 GitHub、GitLab、Bitbucket 仓库
- ✅ 自动识别行号并添加正确的锚点格式
- ✅ 本地仓库降级处理（不生成 web URL）
