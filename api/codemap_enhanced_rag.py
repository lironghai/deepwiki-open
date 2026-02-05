"""
Codemap增强的RAG系统
将Codemap作为结构化知识源整合到RAG流程中
"""
import logging
import os
from typing import List, Dict, Any, Optional
import json

import adalflow as adal

from api.rag import RAG, Memory
from api.code_analyzer import load_codemap
from api.ai_enhanced_analyzer import analyze_repository_with_ai

logger = logging.getLogger(__name__)


class CodemapEnhancedRAG(RAG):
    """集成Codemap的增强RAG系统

    将代码结构图作为额外的上下文来源，提供更精确的代码导航和问答
    """

    def __init__(self, provider="google", model=None, **kwargs):
        """初始化Codemap增强的RAG系统

        Args:
            provider: 模型提供商（google, openai, dashscope等）
            model: 使用的模型名称，None表示使用默认模型
            **kwargs: 其他参数传递给父类
        """
        super().__init__(provider, model, **kwargs)

        # Codemap缓存
        self.codemap_cache: Dict[str, Dict[str, Any]] = {}
        self.current_repo_path: Optional[str] = None

        # 引用的代码节点（用于高亮显示）
        self.referenced_nodes: List[Dict[str, Any]] = []

    def load_codemap(self, repo_path: str, force_regenerate: bool = False) -> Dict[str, Any]:
        """加载Codemap作为额外上下文

        Args:
            repo_path: 仓库路径
            force_regenerate: 是否强制重新生成

        Returns:
            Codemap数据
        """
        # 检查缓存
        if repo_path in self.codemap_cache and not force_regenerate:
            logger.info(f"Using cached codemap for {repo_path}")
            return self.codemap_cache[repo_path]

        # 尝试从文件加载
        cache_dir = self._get_codemap_cache_dir()
        cache_file = self._get_codemap_cache_path(repo_path)

        if os.path.exists(cache_file) and not force_regenerate:
            try:
                logger.info(f"Loading codemap from cache file: {cache_file}")
                codemap_data = load_codemap(cache_file)
                self.codemap_cache[repo_path] = codemap_data
                self.current_repo_path = repo_path
                return codemap_data
            except Exception as e:
                logger.warning(f"Failed to load cached codemap: {e}")

        # 生成新的Codemap
        logger.info(f"Generating new codemap for {repo_path}")
        try:
            # 使用AI增强的分析器
            codemap_data = analyze_repository_with_ai(repo_path, {
                'max_depth': 8,
                'include_tests': False
            })

            # 保存到缓存文件
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(codemap_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved codemap to {cache_file}")

            self.codemap_cache[repo_path] = codemap_data
            self.current_repo_path = repo_path
            return codemap_data

        except Exception as e:
            logger.error(f"Failed to generate codemap: {e}")
            return {}

    def _get_codemap_cache_dir(self) -> str:
        """获取Codemap缓存目录"""
        from api.api import get_adalflow_default_root_path
        root = get_adalflow_default_root_path()
        return os.path.join(root, "codemaps")

    def _get_codemap_cache_path(self, repo_path: str) -> str:
        """获取Codemap缓存文件路径"""
        # 从repo_path提取repo名称
        repo_name = os.path.basename(repo_path)
        cache_dir = self._get_codemap_cache_dir()
        return os.path.join(cache_dir, f"codemap_{repo_name}.json")

    def call(
        self,
        question: str,
        context: str = None,
        language: str = "en"
    ) -> adal.core.generator.GeneratorOutput:
        """增强的RAG调用，包含Codemap上下文

        Args:
            question: 用户问题
            context: 原始上下文（来自文档检索）
            language: 语言设置（默认en）

        Returns:
            生成器输出
        """
        # 重置引用节点
        self.referenced_nodes = []

        # 获取Codemap上下文
        codemap_context = ""
        if self.current_repo_path and self.current_repo_path in self.codemap_cache:
            try:
                codemap_context = self._build_codemap_context(question)
            except Exception as e:
                logger.error(f"Error building codemap context: {e}")
                codemap_context = ""

        # 检索相关文档
        retrieved_documents = super().call(query=question, language=language)

        # 从检索结果中提取文档对象列表
        context_docs = []
        if retrieved_documents and len(retrieved_documents) > 0:
            context_docs = retrieved_documents[0].documents if hasattr(retrieved_documents[0], 'documents') else []

        # 如果有Codemap上下文，创建一个虚拟文档对象添加到开头
        if codemap_context:
            # 创建一个简单的对象来存储codemap上下文
            class CodemapContextDoc:
                def __init__(self, text):
                    self.text = text
                    self.meta_data = {'file_path': 'Codemap Structure Info'}

            codemap_doc = CodemapContextDoc(codemap_context)
            # 将codemap文档添加到文档列表开头
            context_docs = [codemap_doc] + context_docs

        # 使用generator生成答案
        # 更新prompt中的上下文（contexts应该是文档对象列表）
        self.generator.prompt_kwargs["contexts"] = context_docs
        self.generator.prompt_kwargs["conversation_history"] = self.memory()

        # 生成答案
        response = self.generator(prompt_kwargs={"input_str": question})

        # 将对话添加到记忆中
        if response and response.data:
            answer_text = response.data.answer if hasattr(response.data, 'answer') else str(response.data)
            self.memory.add_dialog_turn(question, answer_text)

        return response

    def _build_codemap_context(self, question: str) -> str:
        """基于问题构建Codemap上下文

        Args:
            question: 用户问题

        Returns:
            格式化的Codemap上下文
        """
        if not self.current_repo_path or self.current_repo_path not in self.codemap_cache:
            return ""

        codemap = self.codemap_cache[self.current_repo_path]

        # 1. 找到相关节点
        relevant_nodes = self._find_relevant_nodes(question, codemap)

        if not relevant_nodes:
            # 如果没有找到特定节点，提供架构概览
            return self._build_architecture_overview(codemap)

        # 2. 格式化节点信息
        context_lines = []
        context_lines.append("### 相关代码组件\n")

        for node in relevant_nodes:
            # 基本信息
            node_info = f"**{node['type']}**: `{node['name']}`"
            if node.get('path'):
                node_info += f" (位于 `{node['path']}`)"

            context_lines.append(node_info)

            # AI注解（如果有）
            if 'ai_annotation' in node:
                context_lines.append(f"  - 功能: {node['ai_annotation']}")

            # 行号（如果有）
            if node.get('start_line') and node.get('end_line'):
                context_lines.append(f"  - 行号: {node['start_line']}-{node['end_line']}")

            # 方法列表（对于类）
            if node['type'] == 'class' and 'methods' in node.get('metadata', {}):
                methods = node['metadata']['methods']
                if methods:
                    context_lines.append(f"  - 方法: {', '.join(methods[:5])}")

            # 依赖关系
            dependencies = self._get_node_dependencies(node['id'], codemap)
            if dependencies:
                context_lines.append(f"  - 依赖: {', '.join(dependencies[:5])}")

            context_lines.append("")  # 空行

        # 3. 添加架构信息（如果有）
        if 'architecture_insights' in codemap:
            insights = codemap['architecture_insights']
            context_lines.append("\n### 架构信息\n")
            context_lines.append(f"- 架构模式: {insights['architecture_pattern']}")
            if insights.get('quality_score'):
                context_lines.append(f"- 代码质量评分: {insights['quality_score']}/10")

        # 4. 添加执行路径（如果问题涉及流程）
        if any(keyword in question.lower() for keyword in ['流程', '执行', '调用', '如何工作', 'how', 'flow']):
            paths_context = self._build_execution_paths_context(codemap, relevant_nodes)
            if paths_context:
                context_lines.append("\n### 相关执行路径\n")
                context_lines.append(paths_context)

        return "\n".join(context_lines)

    def _find_relevant_nodes(self, question: str, codemap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于问题找到相关的代码节点

        Args:
            question: 用户问题
            codemap: Codemap数据

        Returns:
            相关节点列表
        """
        nodes = codemap.get('nodes', [])
        relevant = []

        # 提取问题中的关键词
        keywords = self._extract_keywords(question)

        # 遍历所有节点，计算相关性分数
        for node in nodes:
            score = self._calculate_node_relevance(node, keywords, question)
            if score > 0.3:  # 相关性阈值
                node_copy = node.copy()
                node_copy['relevance_score'] = score

                # 添加AI注解（如果有）
                annotations = codemap.get('ai_annotations', {})
                if node['id'] in annotations:
                    node_copy['ai_annotation'] = annotations[node['id']]

                relevant.append(node_copy)
                self.referenced_nodes.append(node_copy)

        # 按相关性排序
        relevant.sort(key=lambda n: n.get('relevance_score', 0), reverse=True)

        return relevant[:10]  # 返回最相关的10个节点

    def _extract_keywords(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        # 简单的关键词提取（可以改进为使用NLP）
        # 移除常见的停用词
        stop_words = {
            '是', '的', '在', '了', '和', '有', '这', '那', '吗', '么', '什么', '如何', '怎么',
            'what', 'how', 'is', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for'
        }

        words = question.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _calculate_node_relevance(self, node: Dict[str, Any], keywords: List[str], question: str) -> float:
        """计算节点与问题的相关性分数

        Args:
            node: 代码节点
            keywords: 关键词列表
            question: 原始问题

        Returns:
            相关性分数（0-1）
        """
        score = 0.0

        # 1. 名称匹配（40%）
        node_name_lower = node.get('name', '').lower()
        for keyword in keywords:
            if keyword in node_name_lower:
                score += 0.4 / len(keywords)

        # 2. 路径匹配（20%）
        node_path_lower = node.get('path', '').lower()
        for keyword in keywords:
            if keyword in node_path_lower:
                score += 0.2 / len(keywords)

        # 3. 类型匹配（10%）
        # 如果问题提到"类"、"函数"等，优先匹配对应类型
        node_type = node.get('type', '')
        if ('class' in question.lower() or '类' in question) and node_type in ['class', 'interface']:
            score += 0.1
        elif ('function' in question.lower() or '函数' in question) and node_type == 'function':
            score += 0.1

        # 4. AI注解匹配（30%）
        # 如果节点有AI注解，检查注解中是否包含关键词
        # 注意：这里暂时无法访问注解，在_find_relevant_nodes中处理

        return min(score, 1.0)

    def _get_node_dependencies(self, node_id: str, codemap: Dict[str, Any]) -> List[str]:
        """获取节点的依赖关系

        Args:
            node_id: 节点ID
            codemap: Codemap数据

        Returns:
            依赖的节点名称列表
        """
        edges = codemap.get('edges', [])
        nodes = codemap.get('nodes', [])

        # 创建节点ID到节点的映射
        node_map = {n['id']: n for n in nodes}

        dependencies = []
        for edge in edges:
            if edge['source'] == node_id and edge['type'] in ['import', 'call', 'reference']:
                target_id = edge['target']
                if target_id in node_map:
                    dependencies.append(node_map[target_id]['name'])

        return dependencies

    def _build_architecture_overview(self, codemap: Dict[str, Any]) -> str:
        """构建架构概览

        Args:
            codemap: Codemap数据

        Returns:
            架构概览文本
        """
        lines = []
        lines.append("### 代码库架构概览\n")

        # 统计信息
        metadata = codemap.get('metadata', {})
        lines.append(f"- 总文件数: {metadata.get('total_files', 0)}")
        lines.append(f"- 总代码行数: {metadata.get('total_lines', 0)}")
        lines.append(f"- 节点数: {metadata.get('node_count', 0)}")

        # 语言分布
        languages = metadata.get('languages', [])
        if languages:
            lines.append(f"- 主要语言: {', '.join(languages)}")

        # 架构层次
        arch_layers = metadata.get('architecture_layers', {})
        if arch_layers:
            lines.append("\n### 识别的架构层次\n")
            for layer, classes in arch_layers.items():
                if classes:
                    lines.append(f"- **{layer}**: {len(classes)} 个组件")

        # 架构洞察
        if 'architecture_insights' in codemap:
            insights = codemap['architecture_insights']
            lines.append("\n### 架构分析\n")
            lines.append(f"- 架构模式: {insights['architecture_pattern']}")
            if insights.get('quality_score'):
                lines.append(f"- 质量评分: {insights['quality_score']}/10")

            # 主要问题
            if insights.get('issues'):
                lines.append("\n主要关注点:")
                for issue in insights['issues'][:3]:
                    lines.append(f"  - {issue}")

        return "\n".join(lines)

    def _build_execution_paths_context(self, codemap: Dict[str, Any], relevant_nodes: List[Dict[str, Any]]) -> str:
        """构建执行路径上下文

        Args:
            codemap: Codemap数据
            relevant_nodes: 相关节点

        Returns:
            执行路径上下文
        """
        paths = codemap.get('execution_paths', [])
        if not paths:
            return ""

        lines = []

        # 找到与相关节点相关的执行路径
        relevant_node_ids = {n['id'] for n in relevant_nodes}

        for path in paths[:5]:  # 最多5条路径
            path_nodes = set(path.get('path_nodes', []))
            if path_nodes & relevant_node_ids:  # 有交集
                lines.append(f"**{path['entry_point']}**")
                lines.append(f"  - {path['description']}")
                lines.append(f"  - 重要性: {path.get('importance_score', 0):.2f}")
                lines.append("")

        return "\n".join(lines)

    def get_referenced_nodes(self) -> List[Dict[str, Any]]:
        """获取本次查询引用的代码节点

        Returns:
            引用的节点列表
        """
        return self.referenced_nodes.copy()

    def get_codemap_summary(self) -> Dict[str, Any]:
        """获取当前Codemap的摘要信息

        Returns:
            摘要信息字典
        """
        if not self.current_repo_path or self.current_repo_path not in self.codemap_cache:
            return {}

        codemap = self.codemap_cache[self.current_repo_path]

        summary = {
            'has_codemap': True,
            'node_count': codemap.get('metadata', {}).get('node_count', 0),
            'file_count': codemap.get('metadata', {}).get('total_files', 0),
            'ai_enhanced': codemap.get('ai_enhanced', False),
            'has_annotations': bool(codemap.get('ai_annotations')),
            'has_execution_paths': bool(codemap.get('execution_paths')),
            'has_insights': bool(codemap.get('architecture_insights'))
        }

        if 'architecture_insights' in codemap:
            insights = codemap['architecture_insights']
            summary['architecture_pattern'] = insights['architecture_pattern']
            summary['quality_score'] = insights.get('quality_score', 0)

        return summary


class CodemapEnhancedDeepResearchRAG(CodemapEnhancedRAG):
    """支持Codemap的深度研究RAG

    在深度研究过程中利用Codemap提供更精确的代码导航
    """

    def __init__(self, provider="google", model=None, **kwargs):
        """初始化深度研究RAG系统

        Args:
            provider: 模型提供商（google, openai, dashscope等）
            model: 使用的模型名称，None表示使用默认模型
            **kwargs: 其他参数传递给父类
        """
        super().__init__(provider, model, **kwargs)

        # 使用CodemapEnhancedRAG替换基础RAG
        self.simple_rag = CodemapEnhancedRAG(provider, model, **kwargs)

    def load_codemap(self, repo_path: str, force_regenerate: bool = False):
        """加载Codemap

        Args:
            repo_path: 仓库路径
            force_regenerate: 是否强制重新生成
        """
        self.simple_rag.load_codemap(repo_path, force_regenerate)

    def get_referenced_nodes(self) -> List[Dict[str, Any]]:
        """获取引用的代码节点"""
        return self.simple_rag.get_referenced_nodes()

    def get_codemap_summary(self) -> Dict[str, Any]:
        """获取Codemap摘要"""
        return self.simple_rag.get_codemap_summary()
