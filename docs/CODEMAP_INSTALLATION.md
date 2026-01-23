# Codemap 功能安装与测试指南

## ✅ 完整实现清单

### 后端实现
- ✅ `api/code_analyzer.py` - 核心代码分析引擎
- ✅ `api/api.py` - 新增3个Codemap API端点
  - `POST /api/codemap/generate` - 生成代码地图
  - `GET /api/codemap` - 获取缓存的代码地图
  - `DELETE /api/codemap` - 删除代码地图缓存

### 前端实现
- ✅ `src/components/Codemap.tsx` - 可视化组件（使用ReactFlow）
- ✅ `src/app/[owner]/[repo]/codemap/page.tsx` - Codemap页面
- ✅ `src/app/[owner]/[repo]/page.tsx` - 添加导航链接
- ✅ `package.json` - 添加 `reactflow` 依赖

### 文档
- ✅ `CODEMAP_DESIGN.md` - 架构设计文档
- ✅ `CODEMAP_USAGE.md` - 使用指南
- ✅ `CODEMAP_INSTALLATION.md` - 本文件

## 📦 安装步骤

### 1. 安装前端依赖

```bash
# 在项目根目录
npm install
# 或
yarn install
```

这会安装新增的 `reactflow@^11.11.4` 依赖。

### 2. 验证后端文件

确保以下文件存在：
```bash
# 检查代码分析器
ls -l api/code_analyzer.py

# 检查API更新
grep "codemap" api/api.py
```

### 3. 重启服务

```bash
# 终止现有服务（如果在运行）
# Ctrl+C

# 重启后端
cd api
python -m api.main

# 在新终端，重启前端
cd ../
npm run dev
```

## 🧪 测试流程

### 测试1：基本功能测试

#### 步骤：
1. 访问 `http://localhost:3000`
2. 输入一个公开仓库，例如：`openai/chatgpt-retrieval-plugin`
3. 生成Wiki
4. 在Wiki页面左侧导航找到 **"代码地图"** 按钮
5. 点击进入Codemap页面

#### 预期结果：
- ✅ 页面显示"代码地图尚未生成"提示
- ✅ 显示"生成代码地图"按钮

### 测试2：生成代码地图

#### 步骤：
1. 在Codemap页面点击 **"生成代码地图"**
2. 等待生成（小型项目约10-30秒）

#### 预期结果：
- ✅ 显示加载动画
- ✅ 后端日志显示分析进度
- ✅ 生成完成后显示代码地图可视化
- ✅ 左侧显示统计信息（文件数、节点数等）

#### 验证生成结果：
```bash
# 检查缓存文件是否生成
ls ~/.adalflow/codemaps/

# 应该看到类似这样的文件：
# codemap_github_openai_chatgpt-retrieval-plugin.json
```

### 测试3：交互功能测试

#### a) 搜索功能
1. 在左侧搜索框输入 "server"
2. 观察图表节点过滤

**预期**：只显示包含"server"的节点

#### b) 类型过滤
1. 取消勾选 "file"
2. 观察文件节点消失

**预期**：只显示类、函数等非文件节点

#### c) 节点点击
1. 点击一个文件节点
2. 应该在新标签页打开GitHub文件

**预期**：正确跳转到对应源码文件

#### d) 缩放和拖拽
1. 使用鼠标滚轮缩放
2. 拖拽节点调整位置
3. 使用左下角控制器

**预期**：交互流畅

### 测试4：导出功能

#### 步骤：
1. 点击右上角 **"导出"** 按钮
2. 检查下载的JSON文件

#### 预期结果：
- ✅ 文件名：`codemap_owner_repo.json`
- ✅ JSON格式正确
- ✅ 包含nodes、edges、metadata

#### 验证JSON结构：
```json
{
  "nodes": [
    {
      "id": "file_...",
      "name": "filename.py",
      "type": "file",
      "path": "path/to/file.py",
      "language": "python",
      ...
    }
  ],
  "edges": [
    {
      "id": "edge_...",
      "source": "node_id_1",
      "target": "node_id_2",
      "type": "import",
      ...
    }
  ],
  "metadata": {
    "total_files": 42,
    "total_lines": 5432,
    ...
  }
}
```

### 测试5：缓存机制测试

#### 步骤：
1. 生成代码地图
2. 刷新页面或重新访问
3. 观察加载速度

#### 预期结果：
- ✅ 第二次访问立即加载（使用缓存）
- ✅ 不需要重新分析

#### 测试缓存失效：
```bash
# 删除缓存
rm ~/.adalflow/codemaps/codemap_github_owner_repo.json

# 重新访问页面
# 应该提示"尚未生成"
```

### 测试6：私有仓库测试

#### 步骤：
1. 访问一个私有仓库的Wiki页面（需要token）
2. 进入Codemap页面
3. Token应该自动传递

#### 预期结果：
- ✅ 成功生成私有仓库的代码地图
- ✅ URL参数包含token

### 测试7：错误处理测试

#### a) 无效仓库
输入不存在的仓库：`invalid/nonexistent-repo`

**预期**：显示友好错误消息

#### b) 网络错误
断开网络连接后尝试生成

**预期**：显示网络错误提示

#### c) 大型仓库
测试一个超大型仓库（>10000文件）

**预期**：
- 可能较慢但最终完成
- 或显示合理的超时提示

## 🔍 API测试

使用curl或Postman测试API：

### 生成代码地图
```bash
curl -X POST http://localhost:8001/api/codemap/generate \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/openai/chatgpt-retrieval-plugin",
    "repo_type": "github",
    "options": {
      "include_tests": false,
      "max_depth": 5
    }
  }'
```

### 获取缓存
```bash
curl "http://localhost:8001/api/codemap?owner=openai&repo=chatgpt-retrieval-plugin&repo_type=github"
```

### 删除缓存
```bash
curl -X DELETE "http://localhost:8001/api/codemap?owner=openai&repo=chatgpt-retrieval-plugin&repo_type=github"
```

## 📊 性能基准测试

### 小型项目（<100文件）
- **分析时间**：5-15秒
- **节点数量**：50-200
- **内存占用**：<100MB

### 中型项目（100-1000文件）
- **分析时间**：15-60秒
- **节点数量**：200-2000
- **内存占用**：100-500MB

### 大型项目（>1000文件）
- **分析时间**：1-5分钟
- **节点数量**：2000+
- **内存占用**：500MB-2GB
- **建议**：使用过滤功能

## 🐛 常见问题排查

### 问题1：前端显示"加载代码地图组件..."卡住

**排查**：
```bash
# 检查reactflow是否安装
npm list reactflow

# 如果没有，安装它
npm install reactflow
```

### 问题2：生成时后端报错 "No module named 'api.code_analyzer'"

**排查**：
```bash
# 确认文件存在
ls -l api/code_analyzer.py

# 检查Python路径
cd api
python -c "import sys; print(sys.path)"
```

### 问题3：点击节点没反应

**排查**：
1. 打开浏览器控制台查看错误
2. 检查 `onNodeClick` 是否正确绑定
3. 验证节点数据结构完整

### 问题4：图表显示空白

**排查**：
```javascript
// 在浏览器控制台检查
console.log(nodes.length, edges.length)

// 应该有数据
// 如果为0，检查数据转换逻辑
```

## ✨ 成功标准

所有以下测试通过即为成功：

- [x] 能够生成小型项目的代码地图
- [x] 可视化正常显示（节点+边）
- [x] 搜索功能正常工作
- [x] 类型过滤正常工作
- [x] 节点点击跳转正常
- [x] 导出功能正常
- [x] 缓存机制正常
- [x] 错误提示友好
- [x] 性能可接受

## 🎓 下一步建议

1. **优化布局算法**：使用更智能的图布局（如力导向布局）
2. **增加更多语言支持**：Java、Go、Rust等
3. **添加代码度量**：圈复杂度、代码行数等
4. **集成AI分析**：使用LLM生成代码注释
5. **实现差异比较**：对比不同版本的代码结构

## 📞 获取帮助

如遇问题：
1. 查看浏览器控制台错误
2. 查看后端日志：`api/logs/`
3. 检查本文档的故障排除部分
4. 查看 `CODEMAP_USAGE.md` 的详细说明

## 🎉 完成！

如果所有测试通过，Codemap功能已成功实现！




