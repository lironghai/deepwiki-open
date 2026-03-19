# GitNexus 容器检查报告

## 检查时间
2026-03-10

## 容器状态
- **镜像**: deepwiki-open:modulewiki
- **容器名**: deepwiki-open
- **状态**: Up 19 hours

## 1. 服务是否启动

**结论：GitNexus 已正常启动。**

- 启动日志中有：`GitNexus server running on http://127.0.0.1:3001`
- 容器内执行 `which gitnexus` 得到：`/usr/bin/gitnexus`（全局安装存在）
- 容器内访问 `curl http://127.0.0.1:3001/` 得到 HTTP 404，且响应头为 `X-Powered-By: Express`，说明 3001 端口上已有 Express 服务在响应（根路径 404 为 GitNexus 常见行为）

## 2. Dockerfile / start.sh 是否存在问题

**结论：无问题。**

- Dockerfile 中已安装 build-essential / make / g++ 和 Node，并执行 `npm cache clean --force && npm install -g gitnexus`，无 `|| echo` 掩盖失败
- start.sh 逻辑正确：先判断 `command -v gitnexus`，有则 `gitnexus serve --port 3001 &`，否则 `npx -y gitnexus serve --port 3001 &`
- 当前镜像中 gitnexus 已全局安装，因此走的是 `gitnexus serve --port 3001` 分支

## 3. 为何之前“无响应”

- **3001 未做端口映射**：Docker 只映射了 8001/8002/3000 等，未映射 3001。在宿主机访问 `http://localhost:3001` 会连接失败，表现为“无响应”。
- **正确用法**：通过 Next 同源转发访问，即用前端同一端口 + 路径 `/gitnexus`，例如：
  - 开发：`http://localhost:29006/gitnexus/?repo=amis-mcp`
  - Docker（假设前端映射为 29003）：`http://localhost:29003/gitnexus/?repo=amis-mcp`
- next.config.ts 中已配置 `/gitnexus` 与 `/gitnexus/:path*` 转发到 `http://127.0.0.1:3001`，无需再映射 3001。

## 4. 建议

- 不要直接访问 `http://localhost:3001`（宿主机），一律使用 `http://<前端地址>/gitnexus/?repo=xxx`。
- 若使用旧镜像（曾用 `|| echo` 的 Dockerfile 构建），建议用当前 Dockerfile 重新构建并替换运行中的容器，以确保 gitnexus 一定安装成功。
