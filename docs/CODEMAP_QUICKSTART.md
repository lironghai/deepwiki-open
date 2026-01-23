# Codemap 快速启动指南 ⚡

## 🚀 30秒快速开始

```bash
# 1. 安装依赖
npm install

# 2. 启动后端（新终端）
python -m api.main

# 3. 启动前端（新终端）
npm run dev

# 4. 访问浏览器
# http://localhost:3000
```

## 📸 第一次使用

### 步骤1：生成Wiki
1. 访问 `http://localhost:3000`
2. 输入仓库：`openai/chatgpt-retrieval-plugin`
3. 点击"生成Wiki"

### 步骤2：打开Codemap
1. Wiki生成后，在左侧导航找到 **"代码地图"** 按钮
2. 点击进入Codemap页面

### 步骤3：生成代码地图
1. 点击 **"生成代码地图"** 按钮
2. 等待10-30秒（首次生成）
3. 代码地图自动显示！

### 步骤4：探索功能
- 🔍 **搜索**：在搜索框输入关键词过滤节点
- 🎯 **过滤**：勾选节点类型筛选显示
- 🖱️ **交互**：
  - 点击节点 → 跳转到源码
  - 拖拽节点 → 调整位置
  - 滚轮 → 缩放视图
- 💾 **导出**：点击右上角"导出"保存JSON

## 🎨 节点颜色说明

| 颜色 | 类型 | 说明 |
|-----|------|-----|
| 🔵 蓝色 | File | 源代码文件 |
| 🟡 黄色 | Directory | 目录文件夹 |
| 🟣 紫色 | Function | 函数/方法 |
| 🔴 粉色 | Class | 类定义 |
| 🟢 绿色 | Module | 模块/包 |

## 📂 项目结构

```
deepwiki-open/
├── api/
│   ├── code_analyzer.py     ← 代码分析引擎
│   └── api.py              ← 添加了3个新API
├── src/
│   ├── components/
│   │   └── Codemap.tsx     ← 可视化组件
│   └── app/[owner]/[repo]/
│       ├── page.tsx        ← 添加了导航链接
│       └── codemap/
│           └── page.tsx    ← Codemap页面
└── CODEMAP_*.md            ← 文档
```

## 🔧 调试技巧

### 查看后端日志
```bash
# 后端运行的终端会显示分析进度
# 看到类似输出说明正常：
# INFO - Starting code analysis for /path/to/repo
# INFO - Found 42 documents
# INFO - Analysis complete: 156 nodes, 234 edges
```

### 查看前端日志
按`F12`打开浏览器控制台，查看：
```javascript
// 正常情况会看到：
Generating codemap for https://github.com/...
Repository prepared, using server-side file list
```

### 清除缓存
```bash
# 删除所有代码地图缓存
rm -rf ~/.adalflow/codemaps/*

# 或在Windows:
del /s /q %USERPROFILE%\.adalflow\codemaps\*
```

## ❓ 常见问题

### Q: 点击"生成代码地图"没反应？
**A**: 检查后端是否运行：访问 `http://localhost:8001/` 应该看到API信息

### Q: 显示"加载代码地图组件..."一直转圈？
**A**: 确认依赖已安装：
```bash
npm list reactflow
# 应该显示: reactflow@11.11.4
```

### Q: 节点太多看不清？
**A**: 使用过滤功能：
1. 取消勾选不需要的节点类型
2. 在搜索框输入关键词
3. 使用缩放控制器

### Q: 想要更快的生成速度？
**A**: 添加限制选项：
- 在API请求中设置 `max_depth: 5`
- 或设置 `include_tests: false`

## 📚 完整文档

- **设计文档**：`CODEMAP_DESIGN.md` - 了解架构
- **使用指南**：`CODEMAP_USAGE.md` - 详细功能说明
- **安装测试**：`CODEMAP_INSTALLATION.md` - 完整测试流程
- **功能总结**：`CODEMAP_SUMMARY.md` - 实现清单

## 💡 推荐试验仓库

| 仓库 | 规模 | 特点 |
|-----|------|-----|
| `openai/chatgpt-retrieval-plugin` | 小 | 快速测试 |
| `microsoft/autogen` | 中 | 复杂依赖 |
| `deepseek-ai/DeepSeek-Coder` | 大 | 大型项目 |

## 🎯 下一步

1. ✅ 完成快速启动
2. 📖 阅读 `CODEMAP_USAGE.md` 了解高级功能
3. 🔧 根据需求自定义配置
4. 🚀 集成到你的工作流程

---

**遇到问题？** 查看完整文档或在项目中提issue！

**功能建议？** 欢迎贡献代码或反馈！

🎉 **开始探索你的代码地图吧！**




