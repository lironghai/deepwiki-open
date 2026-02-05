# Codemap + 分层RAG实施清单

基于 [CODEMAP_RAG_LAYERS_INTEGRATION.md](./CODEMAP_RAG_LAYERS_INTEGRATION.md) 的实施清单

---

## 📊 进度总览

| 阶段 | 任务 | 状态 | 预计时间 | 实际时间 |
|------|------|------|---------|---------|
| 阶段1 | 基础设施 | ⏳ 待开始 | 1天 | - |
| 阶段2 | 分层RAG | ⏳ 待开始 | 1天 | - |
| 阶段3 | 并行生成 | ⏳ 待开始 | 1天 | - |
| 阶段4 | 集成优化 | ⏳ 待开始 | 1天 | - |

**总计**：4天

---

## 阶段1：基础设施（第1天）

### 文件创建

- [ ] `api/tools/__init__.py`
- [ ] `api/tools/codemap_cache.py`
- [ ] `api/tools/wiki_exceptions.py`
- [ ] `api/tools/wiki_resources.py`
- [ ] `api/tools/wiki_validator.py`

### 核心任务

#### 1.1 CodemapCacheManager

**文件**: `api/tools/codemap_cache.py`

- [ ] 实现单例模式
- [ ] 实现线程安全的缓存操作（get, set, clear）
- [ ] 实现TTL过期机制（1小时）
- [ ] 实现文件系统持久化
- [ ] 实现统计信息接口（get_stats）

**测试**：
```python
# tests/unit/test_codemap_cache.py
- [ ] 测试单例模式（多次创建返回同一实例）
- [ ] 测试线程安全（并发读写）
- [ ] 测试TTL过期
- [ ] 测试文件加载和保存
```

#### 1.2 异常层级

**文件**: `api/tools/wiki_exceptions.py`

- [ ] 定义WikiException基类
- [ ] 定义WikiValidationError
- [ ] 定义WikiGenerationError
- [ ] 定义WikiResourceError
- [ ] 定义CodemapLoadError
- [ ] 定义RAGRetrievalError

**测试**：
```python
# tests/unit/test_wiki_exceptions.py
- [ ] 测试异常层级继承关系
- [ ] 测试异常消息传递
```

#### 1.3 资源管理

**文件**: `api/tools/wiki_resources.py`

- [ ] 实现CodemapContext类
- [ ] 实现codemap_context函数
- [ ] 实现wiki_generation_context
- [ ] 实现异步版本（如需要）

**测试**：
```python
# tests/unit/test_wiki_resources.py
- [ ] 测试CodemapContext正常流程
- [ ] 测试异常情况下的清理
- [ ] 测试降级处理（codemap加载失败）
- [ ] 测试资源自动释放
```

### 验收标准

- [ ] 所有文件创建完成
- [ ] CodemapCacheManager线程安全测试通过（100次并发操作无错误）
- [ ] Context Manager能正确加载和清理资源
- [ ] 所有单元测试通过（覆盖率≥80%）
- [ ] 代码review通过

---

## 阶段2：分层RAG（第2天）

### 文件创建

- [ ] `api/tools/rag_layers.py`

### 核心任务

#### 2.1 LayeredRAG核心类

**文件**: `api/tools/rag_layers.py`

- [ ] 实现LayeredRAG类
- [ ] 实现RAGLayerResult数据类
- [ ] 实现retrieve主方法

#### 2.2 第一层：关键字匹配

- [ ] 实现_layer_1_keyword_matching方法
- [ ] 定义结构性关键字字典
- [ ] 实现codemap需求检测逻辑
- [ ] 实现文档初步过滤

**测试**：
```python
# tests/unit/test_rag_layers.py
- [ ] 测试architecture关键字检测
- [ ] 测试class_details关键字检测
- [ ] 测试dependencies关键字检测
- [ ] 测试无关键字情况
```

#### 2.3 第二层：语义相似度

- [ ] 实现_layer_2_semantic_retrieval方法
- [ ] 实现增强查询构建（使用codemap实体）
- [ ] 实现文档评分机制
- [ ] 实现codemap实体匹配加分

**测试**：
```python
- [ ] 测试语义检索准确性
- [ ] 测试codemap实体提取
- [ ] 测试评分机制
- [ ] 测试Top-K选择
```

#### 2.4 第三层：依赖关系扩展

- [ ] 实现DependencyContextExpander类
- [ ] 实现_extract_entities_from_docs
- [ ] 实现_find_related_entities
- [ ] 实现_find_docs_for_entities
- [ ] 实现依赖图遍历算法

**测试**：
```python
- [ ] 测试实体提取
- [ ] 测试依赖关系查找
- [ ] 测试extends/implements关系识别
- [ ] 测试imports/calls关系识别
- [ ] 测试上下文扩展限制（max_additional）
```

### 验收标准

- [ ] 三层RAG检索正常工作
- [ ] Codemap正确注入到各层
- [ ] 检索质量提升（通过对比测试，准确率+20%以上）
- [ ] 性能在可接受范围（总延迟<1秒）
- [ ] 集成测试通过

---

## 阶段3：并行生成（第3天）

### 文件创建

- [ ] `api/tools/wiki_generator.py`

### 核心任务

#### 3.1 ParallelWikiGenerator

**文件**: `api/tools/wiki_generator.py`

- [ ] 实现ParallelWikiGenerator类
- [ ] 实现generate_pages_parallel方法
- [ ] 实现_generate_single_page方法
- [ ] 实现_extract_relevant_modules
- [ ] 实现_generate_content_with_codemap
- [ ] 实现_build_enhanced_prompt

**测试**：
```python
# tests/unit/test_wiki_generator.py
- [ ] 测试单页生成
- [ ] 测试并行生成（10页）
- [ ] 测试错误处理（某些页面失败）
- [ ] 测试codemap集成
- [ ] 测试worker数量配置
```

#### 3.2 集成codemap缓存

- [ ] 在并行生成前预加载codemap
- [ ] 确保所有worker共享同一codemap实例
- [ ] 实现codemap加载失败的降级处理

**测试**：
```python
- [ ] 测试codemap缓存共享
- [ ] 测试并发访问安全性
- [ ] 测试降级处理
```

#### 3.3 错误处理和重试

- [ ] 实现页面生成失败重试机制（最多3次）
- [ ] 实现超时处理（单页最多60秒）
- [ ] 实现错误收集和报告

**测试**：
```python
- [ ] 测试重试机制
- [ ] 测试超时处理
- [ ] 测试错误报告
```

#### 3.4 进度跟踪（WebSocket）

- [ ] 实现进度回调接口
- [ ] 集成WebSocket进度推送
- [ ] 实现实时状态更新

### 性能基准测试

**测试场景**：
- [ ] 6页wiki生成（小型）
- [ ] 10页wiki生成（中型）
- [ ] 15页wiki生成（大型）

**目标**：
- [ ] 6页：<15秒（当前~30秒）
- [ ] 10页：<18秒（当前~50秒）
- [ ] 15页：<22秒（当前~75秒）

### 验收标准

- [ ] 并行生成速度提升≥60%
- [ ] Codemap在并行环境中正常工作
- [ ] 错误处理robust（允许部分失败）
- [ ] 所有worker共享codemap缓存
- [ ] 进度跟踪实时准确
- [ ] 性能基准测试通过

---

## 阶段4：集成与优化（第4天）

### 核心任务

#### 4.1 集成到现有RAG

**文件**: `api/rag.py`

- [ ] 修改RAG类，添加layered_retrieval选项
- [ ] 集成LayeredRAG到call方法
- [ ] 保持向后兼容性
- [ ] 更新文档字符串

**修改**：
```python
class RAG(adal.Component):
    def __init__(self, provider="google", model=None, use_layered_retrieval=True):
        # ...
        self.use_layered_retrieval = use_layered_retrieval
        if use_layered_retrieval:
            from api.tools.rag_layers import LayeredRAG
            from api.tools.codemap_cache import codemap_cache
            self.layered_rag = LayeredRAG(self, codemap_cache)

    def call(self, query: str, repo_path: str = None, language: str = "en"):
        if self.use_layered_retrieval and repo_path:
            # 使用分层检索
            result = self.layered_rag.retrieve(query, repo_path)
            return result.documents
        else:
            # 原有逻辑
            # ...
```

**测试**：
```python
# tests/integration/test_rag_integration.py
- [ ] 测试分层检索集成
- [ ] 测试向后兼容性
- [ ] 测试性能对比
```

#### 4.2 集成到wiki生成

**文件**: `api/websocket_wiki.py`

- [ ] 修改handle_websocket_wiki函数
- [ ] 集成wiki_generation_context
- [ ] 集成ParallelWikiGenerator
- [ ] 更新进度推送逻辑

**测试**：
```python
# tests/integration/test_wiki_generation.py
- [ ] 测试完整wiki生成流程
- [ ] 测试codemap集成
- [ ] 测试并行生成
- [ ] 测试错误处理
- [ ] 测试WebSocket通信
```

#### 4.3 端到端测试

**测试仓库**：
- [ ] 小型仓库（<100文件）
- [ ] 中型仓库（100-500文件）
- [ ] 大型仓库（>500文件）

**测试场景**：
1. [ ] 基本wiki生成（无codemap）
2. [ ] wiki生成（有codemap）
3. [ ] 结构性问题查询
4. [ ] 依赖关系查询
5. [ ] 并行生成性能
6. [ ] 错误恢复

#### 4.4 性能调优

**目标**：
- [ ] RAG检索延迟<1秒
- [ ] Wiki生成速度提升≥70%
- [ ] 内存占用<300MB
- [ ] 缓存命中率>80%

**优化项**：
- [ ] 优化codemap加载逻辑
- [ ] 调整并发worker数量
- [ ] 优化依赖图遍历算法
- [ ] 实现查询缓存

#### 4.5 文档更新

- [ ] 更新README.md
- [ ] 更新API文档
- [ ] 创建使用示例
- [ ] 更新CLAUDE.md

### 验收标准

- [ ] 完整流程正常工作
- [ ] 性能指标达标（见性能影响评估）
- [ ] 代码质量review通过
- [ ] 文档完整且准确
- [ ] 所有测试通过（单元+集成+E2E）
- [ ] 无regression（原有功能不受影响）

---

## 测试策略

### 单元测试

**覆盖率目标**: ≥80%

**测试框架**: pytest

**测试文件**：
- `tests/unit/test_codemap_cache.py`
- `tests/unit/test_wiki_exceptions.py`
- `tests/unit/test_wiki_resources.py`
- `tests/unit/test_rag_layers.py`
- `tests/unit/test_wiki_generator.py`

### 集成测试

**覆盖场景**：
- RAG集成
- Wiki生成集成
- WebSocket通信
- Codemap集成

**测试文件**：
- `tests/integration/test_rag_integration.py`
- `tests/integration/test_wiki_generation.py`

### 端到端测试

**测试仓库**：
- deepwiki-open（自身）
- 公开的小型项目
- 公开的中型项目

**测试文件**：
- `tests/e2e/test_complete_workflow.py`

### 性能测试

**基准测试**：
- `tests/performance/test_rag_performance.py`
- `tests/performance/test_wiki_generation_performance.py`

**指标**：
- 响应时间
- 吞吐量
- 内存使用
- 缓存命中率

---

## 依赖管理

### 新增依赖

- 无新增外部依赖（仅使用标准库和现有依赖）

### Python版本

- 要求：Python 3.11+

### 兼容性

- 向后兼容现有API
- 新功能通过参数开关控制

---

## 风险管理

| 风险 | 影响 | 概率 | 缓解措施 | 负责人 |
|------|------|------|---------|-------|
| Codemap加载失败 | 中 | 低 | 降级处理，允许不使用codemap继续 | 开发 |
| 并发冲突 | 高 | 中 | 使用线程安全的RLock，充分测试 | 开发 |
| 性能下降 | 中 | 低 | 性能基准测试，及时调优 | QA |
| 内存溢出 | 高 | 低 | 设置缓存TTL，定期清理 | 开发 |
| 测试覆盖不足 | 中 | 中 | 制定详细测试计划，review覆盖率 | QA |

---

## 发布计划

### Alpha版本（内部测试）

**目标**：验证核心功能

**范围**：
- 阶段1-2完成
- 基础功能可用
- 内部测试通过

**时间**：第2天结束

### Beta版本（小范围测试）

**目标**：验证性能和稳定性

**范围**：
- 阶段1-3完成
- 并行生成可用
- 性能达标

**时间**：第3天结束

### Release版本（正式发布）

**目标**：生产环境可用

**范围**：
- 所有阶段完成
- 所有测试通过
- 文档完整

**时间**：第4天结束

---

## 回滚计划

如果遇到严重问题：

1. **立即回滚**：恢复到上一个稳定版本
2. **问题分析**：确定根本原因
3. **修复计划**：制定修复方案
4. **重新测试**：充分测试后再部署

**回滚检查点**：
- 每个阶段结束后创建Git tag
- 保留原有功能的向后兼容性
- 通过feature flag控制新功能开启

---

## 监控和维护

### 监控指标

- [ ] RAG检索延迟（P50, P95, P99）
- [ ] Wiki生成速度
- [ ] Codemap缓存命中率
- [ ] 错误率
- [ ] 内存使用

### 日志

- [ ] 添加详细的debug日志
- [ ] 记录关键操作（codemap加载、RAG检索、wiki生成）
- [ ] 记录性能指标

### 维护计划

- [ ] 每周review性能指标
- [ ] 每月review错误日志
- [ ] 根据反馈持续优化

---

**文档版本**: 1.0
**创建日期**: 2026-01-23
**最后更新**: 2026-01-23
**负责人**: 开发团队
