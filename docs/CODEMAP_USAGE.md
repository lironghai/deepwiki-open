# Codemap 功能使用指南

## 📦 安装依赖

首先安装前端依赖：

```bash
# 在项目根目录运行
npm install
# 或
yarn install
```

这会安装 `reactflow` 依赖用于可视化。

## 🚀 启动服务

### 1. 启动后端 API

```bash
cd api
python -m api.main
```

后端将在 `http://localhost:8001` 运行。

### 2. 启动前端

```bash
npm run dev
# 或
yarn dev
```

前端将在 `http://localhost:3000` 运行。

## 📖 使用流程

### 方法一：通过Wiki页面访问

1. 访问任意仓库的Wiki页面：`http://localhost:3000/owner/repo`
2. 在左侧导航栏找到 **"代码地图"** 链接
3. 点击进入Codemap页面

### 方法二：直接访问

直接访问URL：`http://localhost:3000/owner/repo/codemap`

例如：
- `http://localhost:3000/AsyncFuncAI/deepwiki-open/codemap`
- `http://localhost:3000/openai/chatgpt-retrieval-plugin/codemap?token=YOUR_TOKEN`

## 🎨 功能说明

### 1. 自动生成代码地图

首次访问Codemap页面时，如果没有缓存：
- 点击 **"生成代码地图"** 按钮
- 后端将分析代码结构（文件、类、函数等）
- 生成结果会自动缓存，下次访问直接加载

### 2. 可视化元素

**节点类型**：
- 🗂️ **Directory** (目录) - 黄色
- 📄 **File** (文件) - 蓝色
- 🧩 **Class** (类) - 粉色
- ⚙️ **Function** (函数) - 紫色
- 🔧 **Method** (方法) - 靛蓝色
- 📦 **Module** (模块) - 绿色

**关系类型**：
- ➡️ **Import** (导入) - 蓝色
- 🔗 **Call** (调用) - 紫色，带动画
- 🧬 **Inherit** (继承) - 粉色
- ✅ **Implement** (实现) - 绿色
- 📌 **Reference** (引用) - 灰色
- 📁 **Contains** (包含) - 浅灰色

### 3. 交互功能

#### 搜索节点
在左侧搜索框输入关键词，实时过滤节点：
- 支持按节点名称搜索
- 支持按文件路径搜索
- 支持按描述搜索

#### 类型过滤
勾选/取消勾选节点类型来过滤显示：
- ☑️ file
- ☑️ class
- ☑️ function
- 等等...

#### 语言过滤
如果项目包含多种语言，可以按语言过滤：
- ☑️ python (深度支持：类、函数、导入分析)
- ☑️ java (深度支持：类、接口、方法、继承、实现关系)
- ☑️ go (深度支持：结构体、接口、函数、方法)
- ☑️ javascript (基础支持)
- ☑️ typescript (基础支持)

#### 节点操作
- **点击节点**：如果是文件节点，会在新标签页打开对应的源码文件
- **拖拽节点**：调整布局
- **滚轮缩放**：放大/缩小视图
- **右下角小地图**：快速导航大型图表

### 4. 工具栏功能

**右上角按钮**：
- 🔄 **重新生成**：清除缓存并重新分析代码
- 💾 **导出**：导出JSON格式的代码地图数据
- 🌓 **主题切换**：切换亮色/暗色主题
- ⬅️ **返回Wiki**：返回Wiki页面

**React Flow控制器**（左下角）：
- ➕ 放大
- ➖ 缩小
- 🎯 适应屏幕
- 🔒 锁定/解锁

### 5. 统计信息

左侧面板显示实时统计：
- **文件数量**
- **节点数量**（当前显示/总计）
- **关系数量**（当前显示/总计）
- **代码行数**

## 📊 API端点

### 生成代码地图
```http
POST /api/codemap/generate
Content-Type: application/json

{
  "repo_url": "https://github.com/owner/repo",
  "repo_type": "github",
  "token": "optional_token",
  "options": {
    "include_tests": true,
    "max_depth": 10,
    "languages": ["python", "javascript"]
  }
}
```

### 获取缓存的代码地图
```http
GET /api/codemap?owner=owner&repo=repo&repo_type=github
```

### 删除代码地图缓存
```http
DELETE /api/codemap?owner=owner&repo=repo&repo_type=github&authorization_code=YOUR_CODE
```

## ⚙️ 配置选项

编辑 `api/code_analyzer.py` 中的配置：

```python
# 支持的语言（带深度分析标注）
SUPPORTED_EXTENSIONS = {
    '.py': 'python',      # 深度支持：AST解析
    '.java': 'java',      # 深度支持：自定义解析器
    '.go': 'go',          # 深度支持：自定义解析器
    '.js': 'javascript',  # 基础支持
    '.ts': 'typescript',  # 基础支持
    # 添加更多...
}

# 排除的目录
DEFAULT_EXCLUDED_DIRS = {
    'node_modules', '.git', '__pycache__',
    'target', 'build', 'dist', 'vendor',  # Java/Go构建目录
    # 添加更多...
}
```

### 语言支持级别

**深度支持**（提取详细结构）：
- **Python**: 类、函数、导入、继承关系
- **Java**: 类、接口、枚举、方法、字段、继承、实现关系
- **Go**: 结构体、接口、函数、方法、字段标签

**基础支持**（仅文件级别）：
- JavaScript, TypeScript, 其他语言

## 🐛 故障排除

### 问题1：生成失败

**症状**：点击"生成代码地图"后报错

**解决方案**：
1. 检查后端API是否正常运行
2. 查看浏览器控制台错误信息
3. 检查Python后端日志
4. 确保仓库可访问（私有仓库需要token）

### 问题2：图表加载慢

**症状**：大型项目加载缓慢

**解决方案**：
1. 使用过滤功能减少显示节点
2. 在生成时添加 `max_depth` 限制：
   ```json
   {
     "options": {
       "max_depth": 5
     }
   }
   ```
3. 排除测试文件：
   ```json
   {
     "options": {
       "include_tests": false
     }
   }
   ```

### 问题3：节点重叠

**症状**：节点位置重叠难以查看

**解决方案**：
1. 手动拖拽调整节点位置
2. 使用"适应屏幕"按钮重新布局
3. 使用过滤功能减少显示节点数量

### 问题4：看不到某些文件

**症状**：某些文件没有显示在代码地图中

**原因**：
- 文件类型不在支持列表中
- 被排除规则过滤掉
- 分析过程出错（查看日志）

**解决方案**：
1. 添加文件扩展名到 `SUPPORTED_EXTENSIONS`
2. 检查排除规则
3. 查看后端日志定位错误

## 🔧 高级用法

### 自定义布局算法

编辑 `src/components/Codemap.tsx` 中的 `layoutNodes` 函数来自定义节点布局。

### 扩展解析器

1. 在 `api/code_analyzer.py` 中添加新语言的解析逻辑
2. 实现类似 `_analyze_python_file` 的方法
3. 在 `_analyze_file` 中调用

### 添加新的节点类型

1. 在 `NodeType` 枚举中添加新类型
2. 在 `NodeTypeColors` 中添加颜色配置
3. 在 `NodeTypeIcons` 中添加图标

## 📈 性能优化建议

### 大型仓库（>1000文件）

1. **增量分析**：只分析修改的文件
2. **分层显示**：按目录结构分层
3. **虚拟化渲染**：React Flow自动处理
4. **过滤优先**：先过滤再渲染

### 缓存策略

代码地图缓存位置：`~/.adalflow/codemaps/`

清除所有缓存：
```bash
rm -rf ~/.adalflow/codemaps/*
```

## 🎯 最佳实践

1. **首次使用**：从小型项目开始熟悉功能
2. **定期更新**：代码变更后重新生成代码地图
3. **合理过滤**：大型项目使用过滤功能聚焦关注点
4. **导出备份**：重要项目导出JSON备份
5. **团队协作**：分享代码地图帮助新人理解项目结构

## 📝 未来计划

- [ ] AI辅助注释生成
- [ ] 代码变更热力图
- [ ] 依赖循环检测
- [ ] 复杂度分析可视化
- [ ] 导出PNG/SVG图片
- [ ] 多仓库对比视图

