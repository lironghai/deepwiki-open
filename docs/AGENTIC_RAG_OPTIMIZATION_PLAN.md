
整理成一份**修订版方案要点**，直接回答你的两点：① 用 Agent SDK 接管循环；② 把 Devin 的「Wiki 高层 + 按需代码检索」写进方案，“通过 advanced code search 获取与问题相关的代码上下文，结合 Wiki 生成 context-grounded、带引用的回答。
关系：Wiki 提供高层结构，Ask Devin 在问答时按需、可多轮做代码检索，形成“索引 + 按需检索”的 Agentic 式问答。”。

---

## 1. 用 Agent SDK 接管循环（不再手写 for）

你说得对：**多轮是“用工具还是模型回复”应由 SDK 内部的 agent 循环决定，调用方只传工具和最大步数，不关心循环。**

- **OpenAI Agents SDK**（[openai-agents-python](https://openai.github.io/openai-agents-python/running_agents/)）就是这样用的：
  - 你构造 `Agent(instructions=..., tools=[...])`，然后 `Runner.run(agent, input, max_turns=N)` 或 `Runner.run_streamed(...)`。
  - **循环在 SDK 内部**：LLM 输出 → 若有 tool calls 就执行、把结果 append、再调 LLM → 直到出现“最终文本输出”或达到 `max_turns`。
  - 调用方只看到一次 `run`/`run_streamed`，不写 for、不判断“这轮是工具还是回复”。

当前实现的问题正是：**自己在 `tool_call_handler` 里用 for 循环模拟这套逻辑**（调 LLM → 解析 tool_calls → 执行工具 → 再调 LLM），既重复造轮子，又容易和 SDK 的约定（如 tool_choice、流式事件）不一致。

因此，**优化方案里应明确**：

- **新实现**：在“模型调用处”改为使用 **Agent SDK**（或等价能力）：
  - 传入：**工具列表**（如 `rag_search`, `grep_search`）+ **最大迭代/步数**（如 `max_turns`）。
  - 由 **SDK 负责**：多轮时是用工具还是模型直接回复、何时结束，外部不写循环。
- **现有实现**：保留为备份（例如 `run_agent_loop_for_loop_backup`），仍是当前的手写 for 循环，用于回退或对比。

这样方案就体现了“用 SDK 的 agent 调用，而不是自己管循环”。

---

## 2. 把 Devin 的流程与思想写进方案

你希望方案里**显式体现**这句话所代表的逻辑：

- “通过 **advanced code search** 获取与问题相关的代码上下文，**结合 Wiki** 生成 **context-grounded、带引用的回答**。”
- “**Wiki 提供高层结构**，**Ask Devin 在问答时按需、可多轮做代码检索**，形成 **索引 + 按需检索** 的 Agentic 式问答。”

下面用同一套话术写进方案，并对应到实现要点。

### 2.1 Devin 的流程（方案中应写明的“目标形态”）

1. **索引侧（Wiki / 高层结构）**  
   - 事先有：仓库的 **Wiki / 高层结构**（目录、模块、架构摘要等），相当于“索引”。  
   - 对应我们：RAG 索引 + 可选 Wiki 页/结构摘要；已有。

2. **问答时（按需检索）**  
   - 用户提问后，**不在一开始塞满整段代码**，而是：  
   - 给 Agent **高层视图**（例如简短 repo 介绍 + 当前问题）；  
   - 提供 **advanced code search** 类工具（我们即 `rag_search` + `grep_search`）；  
   - 由 **Agent 按需、可多轮** 调用这些工具获取代码片段与文档。

3. **综合与输出**  
   - 在拿到足够检索结果后，**结合 Wiki/高层信息** 生成回答；  
   - 输出 **context-grounded、带引用**（如文件路径、行号或代码块）。

关系可以概括为：**Wiki/索引提供“结构”与“入口”；问答时通过“按需、多轮代码检索”拿到具体证据；两者结合得到 Agentic 式、可引用的回答。**

### 2.2 在方案中的具体体现（实现层面）

- **“Wiki 提供高层结构”**  
  - 在 Agent 的 **instructions**（或首条系统/用户消息）里提供：  
    - 仓库类型、名称、简要结构（来自现有 Wiki/结构或 RAG 的顶层摘要）；  
    - **不**在这里塞入大段 `<START_OF_CONTEXT>...` 的预检索代码，只给“地图”，不给“全文”。

- **“Ask Devin 在问答时按需、可多轮做代码检索”**  
  - 工具只暴露 **rag_search**、**grep_search**（advanced code search）；  
  - 由 **Agent SDK 的循环**决定：何时调工具、调几次、何时用模型回复；  
  - 对应“按需、可多轮”的代码检索，无需我们在外层再写 for。

- **“结合 Wiki 生成 context-grounded、带引用的回答”**  
  - instructions 中明确要求：  
    - 回答必须基于 **检索到的代码/文档** 和 **高层结构**；  
    - 引用时给出文件路径、片段或行号（带引用）。

这样，方案里既有“用 Agent SDK 替代手写循环”，也有“Devin 式：Wiki 高层 + 按需代码检索 → 带引用的回答”的完整逻辑与实现对应。

---

## 3. 修订后的方案结构建议（可直接写进文档）

在 `AGENTIC_RAG_OPTIMIZATION_PLAN.md`（或等价文档）里，建议至少包含下面几块，既体现“Agent SDK 接管循环”，又体现“借鉴 Devin 的思想和流程”：

1. **目标与问题**
   - 当前：手写 for 循环做“LLM ↔ 工具”多轮，调用方还要关心何时工具、何时结束。  
   - 目标：改为使用 **Agent SDK**，传入工具 + 最大迭代次数，多轮由 SDK 负责；并采用 **Devin 式“索引 + 按需检索”** 的问答流程。

2. **Devin 流程与对应关系（必含段落）**
   - 用你认可的原话写清：  
     - Wiki/索引提供高层结构；  
     - 问答时通过 advanced code search 按需、可多轮获取代码上下文；  
     - 结合 Wiki 生成 context-grounded、带引用的回答；  
     - 即“索引 + 按需检索”的 Agentic 问答。  
   - 并对应到我们：**instructions 里给高层结构 + 不预填大段代码**；**工具 = rag_search / grep_search**；**由 Agent 多轮调用工具后再综合、带引用**。

3. **实现要点**
   - **模型调用处**：用 Agent SDK（如 OpenAI Agents SDK）的 `Runner.run` / `Runner.run_streamed`，传入 `Agent(instructions=..., tools=[rag_search, grep_search])` 和 `max_turns`（及 run_config 等），**不再**在此处写 for 循环。  
   - **兼容性**：若当前使用 Dashscope/非 OpenAI 的 Chat Completions，需一层适配（用 SDK 的 custom provider 或封装成“Agent 接口 + 现有 client”），保证仍能流式、仍能限制步数。  
   - **备份**：保留现有 `run_agent_loop` 的 for 循环实现为 `run_agent_loop_for_loop_backup`，供回退或 A/B。

4. **Instructions / Prompt 设计（体现 Devin 思想）**
   - 提供 **高层结构**（repo 名、类型、模块/目录概览），不提供大段预检索代码。  
   - 明确说明：你有 **rag_search / grep_search**，需在回答前**按需、可多次**检索代码与文档；回答必须 **基于检索结果与 Wiki/结构**，并**带引用**（文件路径/代码片段）。

---

## 4. 实现状态（已落地）

- **依赖**：`api/pyproject.toml` 已增加 `openai-agents>=0.10.0`。
- **Agent SDK 接管循环**：
  - `api/tools/tool_call_handler.py`：对外仍为 `run_agent_loop()`；当 provider 为 `openai`/`azure`/`dashscope` 且已安装 `openai-agents` 时，使用 `Runner.run_streamed(Agent(instructions=..., tools=[rag_search, grep_search]), input, RunConfig(max_turns=...))`，循环由 SDK 内部完成；否则回退到手写循环 `run_agent_loop_for_loop_backup()`。
  - 工具通过 SDK 的 `@function_tool` 包装，内部调用现有 `execute_tool(rag_search|grep_search, ...)`。
- **Devin 式「索引 + 按需检索」**：
  - `api/prompts.py` 新增 **AGENTIC_AGENT_SYSTEM_PROMPT**：仅包含 repo 类型/名称/高层说明，明确具备 `rag_search`/`grep_search`，要求按需检索、回答需基于检索结果并带引用。
  - `api/simple_chat.py` 与 `api/websocket_wiki.py`：当 `supports_tool_calling(provider)` 时，使用 `AGENTIC_AGENT_SYSTEM_PROMPT` 作为 `system_instructions`，用户消息仅含对话历史、当前文件（如有）、查询，**不**预填 `<START_OF_CONTEXT>` 大段代码；由 Agent 多轮调用 `rag_search`/`grep_search` 获取上下文后再生成带引用的回答。

