# 项目删除功能分析报告

## 📋 当前删除流程

### 1. 前端删除操作

**位置**: `src/components/ProcessedProjects.tsx`

**删除函数**: `handleDelete`
```typescript
const handleDelete = async (project: ProcessedProject) => {
  // 调用 DELETE /api/wiki/projects
  const response = await fetch('/api/wiki/projects', {
    method: 'DELETE',
    body: JSON.stringify({
      owner: project.owner,
      repo: project.repo,
      repo_type: project.repo_type,
      language: project.language,
    }),
  });
}
```

### 2. 前端API路由

**位置**: `src/app/api/wiki/projects/route.ts`

**DELETE处理**: 转发到后端 `/api/wiki_cache` 接口
```typescript
export async function DELETE(request: Request) {
  const { owner, repo, repo_type, language } = body;
  const params = new URLSearchParams({ owner, repo, repo_type, language });
  const response = await fetch(`${CACHE_API_ENDPOINT}?${params}`, {
    method: 'DELETE',
  });
}
```

### 3. 后端删除实现

**位置**: `api/api.py`

**删除函数**: `delete_wiki_cache` (第550-584行)

**当前实现**:
```python
@app.delete("/api/wiki_cache")
async def delete_wiki_cache(
    owner: str, repo: str, repo_type: str, language: str
):
    """
    Deletes a specific wiki cache from the file system.
    """
    cache_path = get_wiki_cache_path(owner, repo, repo_type, language)
    if os.path.exists(cache_path):
        os.remove(cache_path)  # 只删除wiki缓存文件
        return {"message": "Wiki cache deleted successfully"}
```

## ❌ 当前问题

### 删除不完整

**只删除**:
- ✅ Wiki缓存文件: `~/.adalflow/wikicache/deepwiki_cache_{type}_{owner}_{repo}_{language}.json`

**不删除**:
- ❌ Codemap缓存: `~/.adalflow/codemaps/codemap_{type}_{owner}_{repo}.json`
- ❌ Repos目录: `~/.adalflow/repos/{owner}_{repo}/`
- ❌ Databases文件: `~/.adalflow/databases/{owner}_{repo}.pkl`

## 📁 .adalflow目录结构

```
~/.adalflow/
├── wikicache/          # ✅ 当前会删除
│   └── deepwiki_cache_{type}_{owner}_{repo}_{language}.json
├── codemaps/            # ❌ 不会删除
│   └── codemap_{type}_{owner}_{repo}.json
├── repos/               # ❌ 不会删除
│   └── {owner}_{repo}/  # 完整的仓库克隆
└── databases/           # ❌ 不会删除
    └── {owner}_{repo}.pkl  # 向量数据库文件
```

## 🔍 相关API端点

### 1. Codemap删除端点（已存在但未调用）

**位置**: `api/api.py` 第1355-1382行

**端点**: `DELETE /api/codemap`

**功能**: 删除codemap缓存
```python
@app.delete("/api/codemap")
async def delete_codemap_cache(owner, repo, repo_type):
    cache_path = get_codemap_cache_path(owner, repo, repo_type)
    if os.path.exists(cache_path):
        os.remove(cache_path)
```

### 2. 没有repos和databases删除端点

**当前状态**: 
- ❌ 没有删除repos目录的API端点
- ❌ 没有删除databases文件的API端点

## 💡 建议改进方案

### 方案1: 增强删除API（推荐）

**修改**: `api/api.py` 的 `delete_wiki_cache` 函数

**实现**:
```python
@app.delete("/api/wiki_cache")
async def delete_wiki_cache(
    owner: str, repo: str, repo_type: str, language: str,
    delete_all: bool = False  # 新增参数：是否删除所有相关数据
):
    """
    Deletes wiki cache and optionally all related data.
    
    Args:
        delete_all: If True, also deletes codemap, repos, and databases
    """
    # 1. 删除wiki缓存
    wiki_cache_path = get_wiki_cache_path(owner, repo, repo_type, language)
    if os.path.exists(wiki_cache_path):
        os.remove(wiki_cache_path)
    
    # 2. 如果delete_all=True，删除所有相关数据
    if delete_all:
        # 删除codemap缓存
        codemap_path = get_codemap_cache_path(owner, repo, repo_type)
        if os.path.exists(codemap_path):
            os.remove(codemap_path)
        
        # 删除repos目录
        repo_name = f"{owner}_{repo}"
        repo_dir = os.path.join(get_adalflow_default_root_path(), "repos", repo_name)
        if os.path.exists(repo_dir):
            import shutil
            shutil.rmtree(repo_dir)
        
        # 删除databases文件
        db_file = os.path.join(get_adalflow_default_root_path(), "databases", f"{repo_name}.pkl")
        if os.path.exists(db_file):
            os.remove(db_file)
```

### 方案2: 创建统一的项目删除端点

**新增端点**: `DELETE /api/project`

**功能**: 删除项目的所有相关数据
```python
@app.delete("/api/project")
async def delete_project(
    owner: str, repo: str, repo_type: str
):
    """
    Deletes all data related to a project:
    - Wiki caches (all languages)
    - Codemap cache
    - Repos directory
    - Databases file
    """
    repo_name = f"{owner}_{repo}"
    root_path = get_adalflow_default_root_path()
    
    deleted_items = []
    
    # 1. 删除所有语言的wiki缓存
    wiki_cache_dir = os.path.join(root_path, "wikicache")
    if os.path.exists(wiki_cache_dir):
        pattern = f"deepwiki_cache_{repo_type}_{owner}_{repo}_*.json"
        for filename in os.listdir(wiki_cache_dir):
            if filename.startswith(f"deepwiki_cache_{repo_type}_{owner}_{repo}_"):
                cache_path = os.path.join(wiki_cache_dir, filename)
                os.remove(cache_path)
                deleted_items.append(f"wiki_cache:{filename}")
    
    # 2. 删除codemap缓存
    codemap_path = get_codemap_cache_path(owner, repo, repo_type)
    if os.path.exists(codemap_path):
        os.remove(codemap_path)
        deleted_items.append("codemap_cache")
    
    # 3. 删除repos目录
    repo_dir = os.path.join(root_path, "repos", repo_name)
    if os.path.exists(repo_dir):
        import shutil
        shutil.rmtree(repo_dir)
        deleted_items.append("repos_directory")
    
    # 4. 删除databases文件
    db_file = os.path.join(root_path, "databases", f"{repo_name}.pkl")
    if os.path.exists(db_file):
        os.remove(db_file)
        deleted_items.append("database_file")
    
    return {
        "message": f"Project {owner}/{repo} deleted successfully",
        "deleted_items": deleted_items
    }
```

## 📊 影响分析

### 当前问题的影响

1. **磁盘空间浪费**: 
   - Repos目录可能占用大量空间（完整仓库克隆）
   - Databases文件可能很大（向量嵌入）

2. **数据不一致**:
   - 删除wiki后，codemap仍存在
   - 删除wiki后，repos和databases仍存在

3. **用户体验**:
   - 用户期望"删除项目"会清理所有相关数据
   - 当前行为不符合用户预期

### 改进后的优势

1. **完整清理**: 删除项目时清理所有相关数据
2. **节省空间**: 释放磁盘空间
3. **数据一致性**: 避免孤立数据
4. **用户友好**: 符合用户预期

## 🎯 推荐实现

**建议采用方案2**，创建统一的项目删除端点，因为：

1. **职责清晰**: 专门的项目删除端点，职责明确
2. **向后兼容**: 不影响现有的wiki缓存删除功能
3. **易于扩展**: 未来可以添加更多删除选项
4. **用户友好**: 提供明确的删除选项（仅wiki vs 全部）

## 📝 实施步骤

1. ✅ 分析当前删除流程（已完成）
2. ⏳ 实现统一的项目删除端点
3. ⏳ 更新前端调用新端点
4. ⏳ 添加删除确认对话框（区分部分删除和完全删除）
5. ⏳ 测试删除功能

## 🔒 安全考虑

1. **确认对话框**: 删除前必须确认
2. **权限检查**: 如果启用授权模式，需要验证授权码
3. **错误处理**: 删除失败时提供详细错误信息
4. **日志记录**: 记录所有删除操作

## ✨ 总结

**当前状态**: 
- ❌ 删除项目时只删除wiki缓存
- ❌ 不会删除codemap、repos、databases

**建议改进**:
- ✅ 创建统一的项目删除端点
- ✅ 支持删除所有相关数据
- ✅ 提供用户选择（部分删除 vs 完全删除）

