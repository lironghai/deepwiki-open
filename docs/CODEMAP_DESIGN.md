# Codemap 功能架构设计

## 一、功能概述

Codemap是一个代码结构可视化功能，可以：
1. 展示项目文件结构树
2. 可视化模块依赖关系
3. 显示类/函数调用关系
4. 提供交互式代码导航

## 二、数据模型

### 2.1 代码节点（CodeNode）
```typescript
interface CodeNode {
  id: string;              // 唯一标识
  name: string;            // 节点名称
  type: 'file' | 'class' | 'function' | 'module' | 'directory';
  path: string;            // 文件路径
  language?: string;       // 编程语言
  startLine?: number;      // 起始行号
  endLine?: number;        // 结束行号
  description?: string;    // 描述
  metadata?: {
    size?: number;         // 代码行数
    complexity?: number;   // 圈复杂度
    imports?: string[];    // 导入的模块
    exports?: string[];    // 导出的内容
  };
}
```

### 2.2 依赖关系（CodeEdge）
```typescript
interface CodeEdge {
  id: string;
  source: string;          // 源节点ID
  target: string;          // 目标节点ID
  type: 'import' | 'call' | 'inherit' | 'implement' | 'reference';
  label?: string;          // 边标签
  weight?: number;         // 权重（调用次数）
}
```

### 2.3 代码地图（CodeMap）
```typescript
interface CodeMap {
  nodes: CodeNode[];
  edges: CodeEdge[];
  metadata: {
    repoOwner: string;
    repoName: string;
    totalFiles: number;
    totalLines: number;
    languages: Record<string, number>;  // 语言分布
    generatedAt: string;
  };
}
```

## 三、技术栈

### 3.1 后端分析
- **Python解析**: `ast` (内置)
- **Java解析**: 自定义正则表达式解析器 (`api/parsers/java_parser.py`)
  - 支持类、接口、枚举、注解
  - 提取方法、字段、继承关系
  - 解析包、导入、修饰符
- **Go解析**: 自定义正则表达式解析器 (`api/parsers/go_parser.py`)
  - 支持结构体、接口
  - 提取函数、方法（带receiver）
  - 解析包、导入、字段标签
- **JavaScript/TypeScript解析**: `@babel/parser` + `@babel/traverse` (计划支持)
- **文件遍历**: 使用 `code_analyzer.py` 中的 `CodeAnalyzer`
- **依赖分析**: 基于导入语句和调用关系的自定义分析器

### 3.2 前端可视化
- **图表库**: `reactflow` (交互式流程图)
- **备选方案**: `vis-network`, `cytoscape.js`
- **UI组件**: React + TailwindCSS

### 3.3 缓存策略
- 使用与wiki cache相同的机制
- 缓存路径: `~/.adalflow/codemaps/{owner}_{repo}.json`

## 四、API设计

### 4.1 生成代码地图
```
POST /api/codemap/generate
Body: {
  repo_url: string,
  repo_type: string,
  token?: string,
  options?: {
    includeTests?: boolean,
    maxDepth?: number,
    languages?: string[]
  }
}
Response: CodeMap
```

### 4.2 获取缓存的代码地图
```
GET /api/codemap?owner=xxx&repo=xxx&type=xxx
Response: CodeMap | null
```

### 4.3 分析特定文件
```
POST /api/codemap/analyze-file
Body: {
  repo_url: string,
  file_path: string,
  token?: string
}
Response: {
  nodes: CodeNode[],
  edges: CodeEdge[]
}
```

## 五、实现步骤

### Phase 1: 后端代码分析（核心）
1. 创建 `api/code_analyzer.py` - 代码分析引擎
2. 创建 `api/parsers/` 目录
   - `python_parser.py` - Python代码解析
   - `javascript_parser.py` - JS/TS代码解析
3. 在 `api/api.py` 中添加API路由

### Phase 2: 前端可视化
1. 安装依赖: `reactflow`
2. 创建 `src/components/Codemap.tsx` - 主可视化组件
3. 创建 `src/app/[owner]/[repo]/codemap/page.tsx` - 页面

### Phase 3: 集成与优化
1. 添加导航链接
2. 实现缓存机制
3. 优化性能（大型仓库处理）

## 六、UI设计

### 6.1 布局
```
+------------------+---------------------------+
|   侧边栏         |      主可视化区域          |
|  (过滤/搜索)     |    (React Flow图表)       |
|                  |                           |
|  □ 文件         |        ┌──────┐            |
|  □ 类           |        │ Node │            |
|  □ 函数         |        └──┬───┘            |
|                  |           │                |
|  搜索: [____]   |        ┌──▼───┐            |
|                  |        │ Node │            |
+------------------+---------------------------+
|            工具栏 (缩放/布局/导出)            |
+---------------------------------------------+
```

### 6.2 交互功能
- 鼠标悬停：显示节点详情
- 点击节点：跳转到文件/高亮代码
- 拖拽：调整布局
- 滚轮：缩放
- 搜索：高亮匹配节点
- 过滤：按类型/语言筛选

## 七、性能优化

### 7.1 大型仓库处理
- 增量分析：只分析changed files
- 分层渲染：超过500节点时分层显示
- 虚拟化：使用 React Flow 的虚拟化特性

### 7.2 缓存策略
- 本地缓存：LocalStorage存储用户视图状态
- 服务端缓存：与wiki cache共享存储

## 八、未来扩展

1. **AI辅助分析**: 使用LLM生成代码说明
2. **变更追踪**: 显示代码变更历史
3. **热力图**: 显示代码修改频率
4. **重构建议**: AI识别代码异味

