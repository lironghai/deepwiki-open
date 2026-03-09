# Wiki 生成流程与模型交互提示词分析

## 问题描述

当前生成的 Wiki 内容存在：
- **大量推断**：模型在缺乏足够证据时仍写出“可能”“通常”等推断性描述
- **建议性内容**：如“建议采用”“可以考虑”等非事实描述
- **大量不存在的信息**：编造文件路径、函数名、API、代码片段等

本文档分析 Wiki 生成流程与提示词，定位根因并给出改进方向。

---

## 一、Wiki 生成流程概览

### 1.1 流程划分

| 阶段 | 触发位置 | 通信方式 | 后端处理 |
|------|----------|----------|----------|
| **结构生成** | 前端 `page.tsx` | WebSocket `/ws/chat` | RAG 聊天（检索 + 同一轮生成） |
| **单页内容生成** | 前端 `generatePageContent()` | WebSocket `/ws/chat` | RAG 聊天（检索 + 同一轮生成） |

另有一条并行生成路径：`/ws/wiki/generate` → `ParallelWikiGenerator`（`api/tools/wiki_generator.py`），当前前端**串行调用 `/ws/chat` 逐页生成**，未使用该并行接口。若使用，其 prompt 更简单且**未注入任何代码**，幻觉风险更高。

### 1.2 结构生成流程（Wiki 大纲）

1. 前端组装一条**用户消息**，包含：
   - `<file_tree>`：服务端返回的仓库文件列表（`prepareAndWaitForRepo` 的 `file_paths`）
   - `<readme>`：README 内容
   - 可选：Codemap summary（架构层、key_modules 等）
   - 指令：要求返回 `<wiki_structure>` XML（title、description、sections、pages，每页含 title、description、importance、**relevant_files 的 file_path**、related_pages）
2. 通过 **WebSocket `/ws/chat`** 发送，后端：
   - 使用 **RAG** 对该条用户消息做检索，得到 `context_text`
   - 使用 **SIMPLE_CHAT_SYSTEM_PROMPT**（或 Deep Research 系列）格式化系统提示
   - 将 `context_text` 作为 `<START_OF_CONTEXT>` 与用户消息一起发给模型
3. 模型返回的 XML 被前端解析为 `WikiStructure`（含 `pages`，每页含 `filePaths`）。

**结构阶段已有约束**（前端 prompt）：
- “The &lt;file_path&gt; entries in relevant_files MUST ONLY contain files that ACTUALLY EXIST in the &lt;file_tree&gt;”
- 虽可减少编造路径，但**页面标题、描述**仍可能过于“建议性”或与仓库实际不符，因模型主要依据 file_tree/readme/codemap 摘要“推断”页面设计。

### 1.3 单页内容生成流程（当前实现）

1. 前端对每个 `page` 调用 `generatePageContent(page)`：
   - 拼一条**用户消息** `promptContent`，包含：
     - 角色与任务说明（“expert technical writer”“DEEPLY TECHNICAL and COMPREHENSIVE wiki page”）
     - **本页主题**：`page.title`
     - **声称**：“You will be given... A list of [RELEVANT_SOURCE_FILES]... **You have access to the full content of these files**”
     - 实际只给出 **文件路径列表**（Markdown 链接）：  
       `filePaths.map(path => \`- [${path}](${generateFileUrl(path)})\`).join('\n')`
     - 大量格式与深度要求（Mermaid、表格、引用格式、至少 5 个 source citations 等）
   - 通过 **WebSocket `/ws/chat`** 发送，**不包含任何文件正文**。
2. 后端（`websocket_wiki.py`）：
   - 使用 **RAG** 对这条用户消息做 **retrieve**，得到 `context_text`
   - 将 `context_text` 放入 `<START_OF_CONTEXT>`，与系统提示、用户消息一起发给模型
3. 模型仅能依据 **RAG 检索到的片段** 生成页面内容。

**关键脱节**：
- Prompt 声称 “You have access to the **full content** of these files” 且 “Based **ONLY** on the content of the [RELEVANT_SOURCE_FILES]”。
- 实际提供给模型的是 **RAG 基于整段 prompt 的检索结果**，未必针对本页的 `page.filePaths`，也**未必包含这些文件的完整或足够内容**。
- 检索结果可能很少、或与列出的 filePaths 重叠度低，模型在“必须写满深度技术内容”的压力下只能**推断、建议或编造**。

---

## 二、提示词与上下文来源

### 2.1 结构生成（前端 → /ws/chat）

- **系统提示**：`api/prompts.py` 中 `SIMPLE_CHAT_SYSTEM_PROMPT`（或 Deep Research 系列），含 grounding 规则（仅引用 context 中的内容、不编造路径等）。
- **用户消息**：`src/app/[owner]/[repo]/page.tsx` 约 1152–1328 行：
  - 提供 `<file_tree>`、`<readme>`、可选 codemap
  - 要求 6–8 或 12–16 页、每页 8–10 个 source files、**file_path 必须出现在 file_tree 中**
- **上下文**：RAG 对该条长消息的检索结果；与“生成大纲”的语义可能匹配不足，模型主要依赖消息内的 file_tree/readme/codemap。

### 2.2 单页内容生成（前端 → /ws/chat）

- **系统提示**：同上，`SIMPLE_CHAT_SYSTEM_PROMPT` 等，强调仅基于 context、不编造。
- **用户消息**：`page.tsx` 约 494–619 行：
  - 任务： “generate a DEEPLY TECHNICAL and COMPREHENSIVE wiki page”
  - 要求：“Based ONLY on the content of the [RELEVANT_SOURCE_FILES]”“All information must be derived **SOLELY** from the [RELEVANT_SOURCE_FILES]. Do not infer, invent...”
  - **实际输入**：仅 `[WIKI_PAGE_TOPIC]` + **文件路径列表**（链接），**无文件内容**
- **上下文**：RAG 对整段 prompt 的检索结果，**不是**按 `page.filePaths` 定向注入的文件内容。

### 2.3 并行页面生成（wiki_generator.py，当前前端未用）

- **Prompt 构建**：`_build_enhanced_prompt` / `_build_basic_prompt`：
  - 仅包含：页面 title、description、codemap 的 module 名/类型/简短 description、architecture_layers 名称
  - 指令：“Generate comprehensive wiki page content in Markdown format. Include code examples, explanations, and relevant details.”
- **无任何代码或文件内容注入**，且无“仅基于给定内容、禁止推断”的硬性约束，若启用该路径幻觉会更严重。

---

## 三、根因归纳

1. **页面内容生成时“声称给全文，实际只给路径”**  
   Prompt 写 “You have access to the full content of these files”，但请求中**没有注入** `page.filePaths` 对应文件的真实内容，只有 RAG 检索片段，且检索与“本页相关文件”未绑定。

2. **RAG 检索与“本页相关文件”脱节**  
   检索 query 是整段 wiki 页生成 prompt，返回的 chunks 不一定覆盖或优先覆盖 `page.filePaths`，导致 context 不足或偏题。

3. **提示词鼓励“全面、深度”而证据不足**  
   “DEEPLY TECHNICAL”“AT LEAST 10 relevant source files”“Complete API Documentation”“Implementation details”等要求，在 context 不足时必然促使模型推断和编造。

4. **Wiki 页面生成缺少“仅基于下列原文”的硬约束**  
   虽有 “derive SOLELY from”“Do not infer, invent”，但未在结构上保证“下列内容即全部允许引用的原文”，模型仍会混入外部知识或建议。

---

## 四、改进建议（概要）

### 4.1 单页内容生成：以“真实文件内容”为唯一依据

- **后端**：在处理“Wiki 单页生成”请求时：
  - 识别本页的 `relevant_files` / `filePaths`（可从请求体或约定格式中解析）。
  - 使用 `get_file_content`（或本地 repo 读文件）按路径拉取**真实文件内容**，做长度/ token 控制（截断或摘要）。
  - 将**仅此**作为 `<START_OF_CONTEXT>` 注入，或与 RAG 结果合并但明确标注“以下为指定文件的原文，仅可引用此处”。
- **前端**：在调用 `/ws/chat` 时，可传结构化字段（如 `wikiPageGeneration: { pageId, title, filePaths }`），便于后端识别并注入对应文件内容。

### 4.2 提示词约束强化

- 单页生成系统/用户提示中：
  - 明确写：“Below is the ONLY source material. Do not cite, mention, or imply any file, function, or code that does not appear in the following content.”
  - 若未提供某文件内容（如超长被截断），要求模型明确写“该文件未在上下文中提供”而非推断。
- 降低“必须写满”的压力：如“若上下文中信息不足，请缩短该节或注明‘根据所提供片段无法展开’”。

### 4.3 结构生成

- 保持“file_path 必须存在于 file_tree”的校验；可选在服务端对返回的 XML 做一次 file_path 与 file_tree 的校验并过滤/修正。
- 结构描述可加一句：“Describe only what can be inferred from the provided file tree and README; do not invent modules or features.”

### 4.4 若使用 ParallelWikiGenerator（/ws/wiki/generate）

- 必须在 `_build_enhanced_prompt` / `_build_basic_prompt` 中注入**指定文件的真实内容**（或从 codemap 拉取对应片段），并加入与 RAG 相同的 grounding 规则（仅引用下述内容、不编造路径/代码）。

---

## 五、涉及文件索引

| 用途 | 文件路径 |
|------|----------|
| RAG/聊天系统提示与模板 | `api/prompts.py` |
| 单页内容生成用户消息（前端） | `src/app/[owner]/[repo]/page.tsx`（约 494–619、621–733） |
| 结构生成用户消息（前端） | `src/app/[owner]/[repo]/page.tsx`（约 1152–1328） |
| WebSocket 聊天与 RAG 调用 | `api/websocket_wiki.py` |
| 并行 Wiki 页面生成器 | `api/tools/wiki_generator.py` |
| 获取单文件内容 | `api/data_pipeline.py`（`get_file_content`） |

---

## 六、结论

当前 Wiki 出现**大量推断、建议与不存在信息**的主要原因，是**单页内容生成时未向模型提供“本页相关文件”的真实内容**，仅依赖 RAG 检索结果，且提示词又要求“深度、全面、仅基于给定文件”。改进方向是：**在生成每页内容时，显式注入该页 relevant_files 的原文（或受控摘要），并强化“仅可引用下述内容、禁止推断与编造”的提示与结构约束**。
