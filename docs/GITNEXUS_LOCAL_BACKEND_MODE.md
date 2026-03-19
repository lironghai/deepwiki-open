# GitNexus 本地后端模式（官方说明）

本仓库按 [GitNexus 官方 README](https://github.com/abhigyanpatwari/GitNexus) 的 **Local Backend Mode** 集成：

- **后端**：`gitnexus serve` 在容器内 3001 端口运行，由 Next 同源转发到 `/gitnexus`，无需对外暴露 3001。
- **前端**：官方 [gitnexus-web](https://github.com/abhigyanpatwari/GitNexus/tree/main/gitnexus-web) 构建后托管在站点的 `/gitnexus-app/`，通过 URL 参数 `?server=<同源>/gitnexus` 连接后端（与官方 “open the web UI locally — it auto-detects the server” 一致，此处用 `server` 显式指定代理地址）。

## 官方原文（README）

> **Local Backend Mode:** Run `gitnexus serve` and open the web UI locally — it auto-detects the server and shows all your indexed repos, with full AI chat support. No need to re-upload or re-index.

> Or run locally:
> ```bash
> git clone https://github.com/abhigyanpatwari/GitNexus.git
> cd gitnexus/gitnexus-web
> npm install
> npm run dev
> ```

## 本仓库实现

1. **Docker**：镜像构建时会 clone GitNexus、构建 `gitnexus-web`（`vite build --base /gitnexus-app/`），并将产物复制到 Next 的 `public/gitnexus-app`，随前端一起发布。
2. **本地开发（无 Docker）**：可执行 `scripts/build-gitnexus-web.sh` 生成 `public/gitnexus-app`，再启动 Next；若未构建则该入口会提示“无法加载图谱”。
3. **深度代码图谱页**：访问 `/{owner}/{repo}/codemap` 会加载 iframe `/gitnexus-app/?server=<当前站点>/gitnexus`，即使用官方支持的 `server` 参数连接本地后端。

## 与 DeepWiki 的流程关系

- **AGENTS.md / CLAUDE.md**：若 clone 下来的仓库中本身含有这两个文件，会被默认排除在 wiki 内容、经典代码地图和嵌入索引之外，避免混入 AI/Agent 辅助说明；对项目本身无负面影响。
- **GitNexus 执行时机**：为减少对“准备仓库”的阻塞，并保证图谱基于最终仓库状态生成，**GitNexus 分析改为在「项目 wiki 生成完成」之后执行**，不再在 prepare（clone + 嵌入）阶段执行。产物仍写在仓库内的 `.gitnexus/` 目录（若 CLI 未来支持单独输出目录可再扩展）。

## 参考

- [GitNexus README - Web UI (browser-based)](https://github.com/abhigyanpatwari/GitNexus#web-ui-browser-based)
- [GitNexus README - Bridge mode](https://github.com/abhigyanpatwari/GitNexus#two-ways-to-use-gitnexus)
