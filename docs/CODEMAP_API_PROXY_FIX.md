# Codemap Chat API代理修复

## 问题描述
用户在项目wiki页面启用Codemap选项提问时，前端调用了错误的URL：
```
http://127.0.0.1:3000/server/undefined/api/chat/with_codemap
```

这导致404错误，因为：
1. URL指向前端服务器（3000端口）而不是后端API
2. 路径中包含错误的 `/server/undefined/` 部分
3. 没有正确的代理路由

## 解决方案

### 架构说明
项目采用了 **Next.js API Routes** 作为代理层：
- **前端**: Next.js (端口 3000)
- **代理层**: Next.js API Routes (`/api/*`)
- **后端**: FastAPI (端口 8001)

```
Browser → Next.js (3000) → API Route Proxy → FastAPI (8001)
         /api/chat/codemap  →  /api/chat/with_codemap
```

### 修复内容

#### 1. 创建新的Next.js API代理路由
**文件**: `src/app/api/chat/codemap/route.ts`

这个路由负责：
- 接收前端的 `/api/chat/codemap` 请求
- 代理到后端的 `/api/chat/with_codemap` 端点
- 处理错误和返回响应

**关键代码**:
```typescript
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function POST(req: NextRequest) {
  const requestBody = await req.json();
  const targetUrl = `${TARGET_SERVER_BASE_URL}/api/chat/with_codemap`;

  const backendResponse = await fetch(targetUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });

  const data = await backendResponse.json();
  return NextResponse.json(data);
}
```

#### 2. 修改前端API调用
**文件**: `src/components/Ask.tsx`

修改前：
```typescript
const apiResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat/with_codemap`, {
  // 直接调用后端API（错误）
});
```

修改后：
```typescript
const apiResponse = await fetch('/api/chat/codemap', {
  // 通过Next.js API代理（正确）
});
```

## 环境配置

### 后端服务器端口
**默认端口**: 8001（在 `api/main.py` 中配置）

可以通过环境变量修改：
```bash
export PORT=8001  # Linux/Mac
set PORT=8001     # Windows
```

### 前端代理配置
**环境变量**: `SERVER_BASE_URL`

如果后端运行在不同端口，需要设置：
```bash
# .env.local (在项目根目录)
SERVER_BASE_URL=http://localhost:8001
```

如果不设置，默认使用 `http://localhost:8001`

## 启动服务

### 1. 启动后端API服务（端口8001）
```bash
cd D:\project\local\deepwiki-open

# 方法1: 使用uvicorn直接启动
python -m uvicorn api.api:app --host 0.0.0.0 --port 8001 --reload

# 方法2: 使用项目启动脚本
python -m api.main
```

验证后端运行：
```bash
curl http://localhost:8001/lang/config
```

### 2. 启动前端服务（端口3000）
```bash
cd D:\project\local\deepwiki-open

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

访问：http://localhost:3000

## 测试Codemap聊天功能

### 测试步骤
1. 访问项目wiki页面：`http://localhost:3000/{owner}/{repo}`
2. 在聊天界面找到 **"Codemap Integration"** 开关
3. 启用该开关（切换为蓝色）
4. 输入问题，例如："这个项目的主要功能是什么？"
5. 点击发送

### 预期行为
1. **请求流程**:
   ```
   Browser → POST /api/chat/codemap → Next.js Proxy → POST /api/chat/with_codemap → FastAPI Backend
   ```

2. **正常响应**:
   - 显示AI的回答
   - 下方显示 "Referenced Code Nodes" 面板
   - 列出回答中引用的代码节点

3. **网络请求**:
   - 前端请求：`http://localhost:3000/api/chat/codemap`
   - 后端请求：`http://localhost:8001/api/chat/with_codemap`

### 调试方法

#### 1. 检查浏览器开发者工具
打开 F12 → Network 标签页：
- 查找 `codemap` 请求
- 检查状态码（应该是 200）
- 查看请求和响应内容

#### 2. 检查后端日志
后端终端应该显示：
```
INFO: 127.0.0.1:xxx - "POST /api/chat/with_codemap HTTP/1.1" 200 OK
```

#### 3. 检查Next.js终端
前端终端应该显示：
```
Proxying Codemap chat request to backend...
```

### 常见错误和解决方案

#### 错误1: 404 Not Found
**原因**: 后端服务未启动或端口错误

**解决**:
```bash
# 确保后端在8001端口运行
python -m uvicorn api.api:app --host 0.0.0.0 --port 8001 --reload
```

#### 错误2: 503 Service Unavailable
**原因**: 后端服务不可访问

**解决**:
- 检查防火墙设置
- 确认 `SERVER_BASE_URL` 环境变量正确
- 检查后端是否正常运行

#### 错误3: CORS错误
**原因**: 跨域请求被阻止

**解决**: 后端已配置CORS，应该不会出现。如果出现，检查 `api/api.py` 中的CORS配置。

#### 错误4: 连接超时
**原因**: 后端响应慢或代码分析耗时

**解决**:
- 等待更长时间（首次分析较慢）
- 检查后端日志查看进度
- 考虑优化代码分析性能

## API端点对比

### 旧的（错误的）方式
```typescript
// 直接调用后端 - 不推荐
fetch('http://localhost:8001/api/chat/with_codemap', {...})
```

**问题**:
- 硬编码后端地址
- CORS问题
- 无法统一管理API调用
- 前端依赖后端地址

### 新的（正确的）方式
```typescript
// 通过Next.js API代理 - 推荐
fetch('/api/chat/codemap', {...})
```

**优势**:
- 统一的API调用方式
- 自动处理CORS
- 环境变量配置后端地址
- 前后端解耦

## 相关文件

### 新增文件
- `src/app/api/chat/codemap/route.ts` - Codemap聊天代理路由

### 修改文件
- `src/components/Ask.tsx` - 前端聊天组件（修改API调用URL）

### 参考文件
- `src/app/api/chat/stream/route.ts` - 普通聊天代理路由（参考实现）
- `api/codemap_endpoints.py` - 后端Codemap API端点
- `api/main.py` - 后端服务启动配置

## 验证清单

使用此清单验证修复是否成功：

- [ ] 后端服务正常启动（端口8001）
- [ ] 前端服务正常启动（端口3000）
- [ ] 访问项目wiki页面无错误
- [ ] 找到"Codemap Integration"开关
- [ ] 启用开关后颜色变为蓝色
- [ ] 输入问题可以正常发送
- [ ] 收到AI回答
- [ ] 显示"Referenced Code Nodes"面板
- [ ] 浏览器Network中看到`/api/chat/codemap`请求且状态200
- [ ] 后端日志显示`/api/chat/with_codemap`请求

## 总结

✅ **已修复**: Codemap聊天API URL错误问题
✅ **新增**: Next.js API代理路由 (`/api/chat/codemap`)
✅ **修改**: 前端使用正确的相对路径调用
✅ **架构**: 遵循项目现有的代理模式
✅ **兼容**: 与现有聊天功能保持一致

**修复时间**: 2026-01-21
**涉及文件**: 2个（1新增，1修改）
