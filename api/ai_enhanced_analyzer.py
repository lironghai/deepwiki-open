"""
AI增强的代码分析器
整合LLM能力，为代码节点生成语义理解和智能注解
"""
import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from api.code_analyzer import CodeAnalyzer, CodeNode, CodeEdge, NodeType, EdgeType
from api.config import configs

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPath:
    """执行路径"""
    entry_point: str
    path_nodes: List[str]
    description: str
    importance_score: float


@dataclass
class ArchitectureInsight:
    """架构洞察"""
    architecture_pattern: str
    quality_score: float
    issues: List[str]
    recommendations: List[str]
    layer_analysis: Dict[str, Any]


class AIEnhancedCodeAnalyzer(CodeAnalyzer):
    """AI增强的代码分析器

    在静态分析基础上添加LLM驱动的语义理解
    """

    def __init__(self, repo_path: str, options: Optional[Dict[str, Any]] = None):
        super().__init__(repo_path, options)

        # 初始化LLM生成器
        try:
            from api.config import configs, get_model_config
            
            # 使用与正常提问接口一致的配置获取方式
            default_provider = configs.get('default_provider', 'google')
            providers = configs.get('providers', {})

            if default_provider in providers:
                # 使用get_model_config函数获取配置，与正常提问接口保持一致
                import adalflow as adal

                model_config = get_model_config(default_provider, None)

                # 创建 adalflow.Generator 实例
                # 使用简单的模板，允许直接传递提示文本
                simple_template = "{{prompt}}"
                self.generator = adal.Generator(
                    template=simple_template,
                    model_client=model_config["model_client"],
                    model_kwargs=model_config["model_kwargs"]
                )

                default_model = model_config["model_kwargs"].get("model")
                self.ai_enabled = True
                logger.info(f"AI analyzer initialized with {default_provider}/{default_model}")
            else:
                self.generator = None
                self.ai_enabled = False
                logger.warning("AI analyzer disabled: no valid generator configuration")

        except Exception as e:
            logger.warning(f"Failed to initialize AI generator: {e}")
            self.generator = None
            self.ai_enabled = False

        # AI生成的数据
        self.ai_annotations = {}
        self.execution_paths = []
        self.architecture_insights = None

    def generate_ai_annotations(self, max_nodes: int = 50) -> Dict[str, str]:
        """为关键代码节点生成AI注解

        Args:
            max_nodes: 最大注解节点数量

        Returns:
            节点ID到注解的映射
        """
        if not self.ai_enabled:
            logger.info("AI annotations disabled")
            return {}

        logger.info(f"Generating AI annotations for up to {max_nodes} nodes...")

        # 选择重要节点
        important_nodes = self._get_important_nodes(max_nodes)

        annotations = {}
        batch_size = 10  # 批量处理以提高效率

        for i in range(0, len(important_nodes), batch_size):
            batch = important_nodes[i:i+batch_size]

            try:
                batch_annotations = self._generate_batch_annotations(batch)
                annotations.update(batch_annotations)
                logger.info(f"Generated {len(batch_annotations)} annotations (batch {i//batch_size + 1})")
            except Exception as e:
                logger.error(f"Error generating annotations for batch: {e}")
                continue

        self.ai_annotations = annotations
        return annotations

    def _get_important_nodes(self, max_count: int) -> List[CodeNode]:
        """选择重要的节点进行AI注解

        优先级：
        1. 类（特别是公共API）
        2. 公共函数
        3. 入口点（main, __init__等）
        """
        important = []

        # 1. 收集所有类和函数节点
        classes = []
        functions = []
        entry_points = []

        for node in self.nodes:
            if node.type in [NodeType.CLASS, NodeType.INTERFACE]:
                classes.append(node)
            elif node.type == NodeType.FUNCTION:
                # 检查是否是入口点
                if node.name in ['main', '__init__', '__main__', 'run', 'start', 'execute']:
                    entry_points.append(node)
                else:
                    functions.append(node)

        # 2. 按优先级排序
        # 入口点最优先
        important.extend(entry_points[:5])

        # 然后是类（按行数降序，大类通常更重要）
        classes.sort(key=lambda n: (n.end_line or 0) - (n.start_line or 0) if n.end_line and n.start_line else 0, reverse=True)
        important.extend(classes[:30])

        # 最后是函数（按行数降序）
        functions.sort(key=lambda n: (n.end_line or 0) - (n.start_line or 0) if n.end_line and n.start_line else 0, reverse=True)
        important.extend(functions[:15])

        return important[:max_count]

    def _generate_batch_annotations(self, nodes: List[CodeNode]) -> Dict[str, str]:
        """批量生成注解"""
        if not nodes:
            return {}

        # 构建批量提示
        nodes_info = []
        for node in nodes:
            info = {
                'id': node.id,
                'name': node.name,
                'type': node.type.value,
                'path': node.path,
                'language': node.language or 'unknown'
            }

            # 添加文档字符串（如果有）
            if node.description:
                info['docstring'] = node.description

            # 添加元数据
            if node.metadata:
                if 'imports' in node.metadata:
                    info['imports'] = node.metadata['imports'][:5]  # 限制数量
                if 'methods' in node.metadata:
                    info['has_methods'] = len(node.metadata.get('methods', []))

            nodes_info.append(info)

        prompt = f"""为以下代码节点生成简洁的功能描述（每个1-2句话）：

{json.dumps(nodes_info, indent=2, ensure_ascii=False)}

要求：
1. 每个节点一行，格式：node_id: 描述
2. 描述要专业、准确、简洁
3. 使用中文
4. 不要包含"这是..."、"该..."等冗余词汇
5. 直接说明功能和用途

示例格式：
class_file_api_py_UserService: 处理用户相关业务逻辑，包括注册、登录、权限验证
func_file_utils_py_format_date: 将日期对象格式化为指定字符串格式
"""

        try:
            # 使用 adalflow.Generator 正确调用方式
            generator_output = self.generator(prompt_kwargs={"prompt": prompt})

            # 从 GeneratorOutput 中提取文本响应
            if hasattr(generator_output, 'data') and generator_output.data:
                response = str(generator_output.data)
            else:
                response = str(generator_output)

            # 解析响应
            annotations = {}
            for line in response.split('\n'):
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        node_id = parts[0].strip()
                        description = parts[1].strip()
                        annotations[node_id] = description

            return annotations

        except Exception as e:
            logger.error(f"Error calling LLM for annotations: {e}")
            return {}

    def identify_key_execution_paths(self, max_paths: int = 10) -> List[ExecutionPath]:
        """识别关键执行路径

        Args:
            max_paths: 最大路径数量

        Returns:
            执行路径列表
        """
        if not self.ai_enabled:
            logger.info("Execution path identification disabled")
            return []

        logger.info("Identifying key execution paths...")

        # 1. 找到入口点
        entry_points = self._find_entry_points()

        if not entry_points:
            logger.warning("No entry points found")
            return []

        execution_paths = []

        # 2. 为每个入口点追踪执行路径
        for entry in entry_points[:max_paths]:
            try:
                path_nodes = self._trace_execution_path(entry)

                # 使用LLM生成路径描述
                description = self._generate_path_description(entry, path_nodes)

                # 计算重要性分数
                importance = self._calculate_path_importance(entry, path_nodes)

                execution_paths.append(ExecutionPath(
                    entry_point=entry.name,
                    path_nodes=[n.id for n in path_nodes],
                    description=description,
                    importance_score=importance
                ))

            except Exception as e:
                logger.error(f"Error tracing execution path from {entry.name}: {e}")
                continue

        # 按重要性排序
        execution_paths.sort(key=lambda p: p.importance_score, reverse=True)

        self.execution_paths = execution_paths
        return execution_paths

    def _find_entry_points(self) -> List[CodeNode]:
        """找到代码库的入口点"""
        entry_points = []

        # 常见入口点名称
        entry_names = {
            'main', '__main__', '__init__', 'run', 'start', 'execute',
            'init', 'setup', 'bootstrap', 'launch', 'app', 'create_app'
        }

        for node in self.nodes:
            if node.type == NodeType.FUNCTION:
                # 检查函数名
                if node.name.lower() in entry_names:
                    entry_points.append(node)
                    continue

                # 检查是否是API端点（FastAPI, Flask等）
                if node.metadata and 'decorators' in node.metadata:
                    decorators = node.metadata['decorators']
                    if any('@app.' in d or '@router.' in d or '@blueprint.' in d for d in decorators):
                        entry_points.append(node)

        return entry_points

    def _trace_execution_path(self, entry_point: CodeNode, max_depth: int = 5) -> List[CodeNode]:
        """从入口点追踪执行路径"""
        visited = set()
        path = []

        def dfs(node: CodeNode, depth: int):
            if depth >= max_depth or node.id in visited:
                return

            visited.add(node.id)
            path.append(node)

            # 找到所有被此节点调用的节点
            for edge in self.edges:
                if edge.source == node.id and edge.type == EdgeType.CALL:
                    target_node = next((n for n in self.nodes if n.id == edge.target), None)
                    if target_node:
                        dfs(target_node, depth + 1)

        dfs(entry_point, 0)
        return path

    def _generate_path_description(self, entry_point: CodeNode, path_nodes: List[CodeNode]) -> str:
        """生成执行路径的描述"""
        if not self.ai_enabled or not path_nodes:
            return f"从 {entry_point.name} 开始的执行路径"

        # 构建路径信息
        path_info = {
            'entry': entry_point.name,
            'steps': [
                {
                    'name': node.name,
                    'type': node.type.value,
                    'file': node.path
                }
                for node in path_nodes[:10]  # 限制数量
            ]
        }

        prompt = f"""描述以下代码执行路径的主要功能（1句话）：

入口点: {path_info['entry']}
路径步骤:
{json.dumps(path_info['steps'], indent=2, ensure_ascii=False)}

只返回一句话的功能描述，不要包含其他内容。
"""

        try:
            # 使用 adalflow.Generator 正确调用方式
            generator_output = self.generator(prompt_kwargs={"prompt": prompt})

            # 从 GeneratorOutput 中提取文本响应
            if hasattr(generator_output, 'data') and generator_output.data:
                response = str(generator_output.data)
            else:
                response = str(generator_output)

            return response.strip()
        except Exception as e:
            logger.error(f"Error generating path description: {e}")
            return f"从 {entry_point.name} 开始的执行路径"

    def _calculate_path_importance(self, entry_point: CodeNode, path_nodes: List[CodeNode]) -> float:
        """计算执行路径的重要性分数（0-1）"""
        score = 0.0

        # 1. 入口点类型（30%）
        if entry_point.name.lower() in ['main', '__main__']:
            score += 0.3
        elif entry_point.name.lower() in ['run', 'start', 'execute']:
            score += 0.25
        else:
            score += 0.15

        # 2. 路径长度（20%）
        path_length_score = min(len(path_nodes) / 20.0, 1.0)  # 20个节点为满分
        score += path_length_score * 0.2

        # 3. 涉及的文件数（20%）
        unique_files = len(set(n.path for n in path_nodes))
        file_score = min(unique_files / 10.0, 1.0)  # 10个文件为满分
        score += file_score * 0.2

        # 4. 涉及的语言多样性（10%）
        unique_languages = len(set(n.language for n in path_nodes if n.language))
        lang_score = min(unique_languages / 3.0, 1.0)  # 3种语言为满分
        score += lang_score * 0.1

        # 5. 是否有注解（20%）
        annotated_count = sum(1 for n in path_nodes if n.id in self.ai_annotations)
        annotation_score = annotated_count / len(path_nodes) if path_nodes else 0
        score += annotation_score * 0.2

        return min(score, 1.0)

    def generate_architecture_insights(self) -> ArchitectureInsight:
        """使用LLM生成架构洞察"""
        if not self.ai_enabled:
            logger.info("Architecture insights disabled")
            return ArchitectureInsight(
                architecture_pattern="未知",
                quality_score=0.0,
                issues=[],
                recommendations=[],
                layer_analysis={}
            )

        logger.info("Generating architecture insights...")

        # 获取代码库摘要
        summary = self.generate_codemap_summary()

        # 构建提示
        prompt = f"""分析以下代码库的架构并评估质量：

## 统计信息
- 总文件数: {summary['total_files']}
- 总类数: {summary['total_classes']}
- 总函数数: {summary['total_functions']}
- 总代码行数: {summary['total_lines']}
- 语言分布: {json.dumps(summary['language_distribution'], ensure_ascii=False)}

## 识别的架构层次
{json.dumps(summary.get('architecture_layers', {}), indent=2, ensure_ascii=False)}

## 关键模块（前10个）
{json.dumps(summary.get('key_modules', [])[:10], indent=2, ensure_ascii=False)}

请分析：
1. 主要架构模式（如MVC、微服务、分层架构、领域驱动设计等）
2. 代码组织质量评分（0-10分）
3. 发现的主要问题（最多5个）
4. 改进建议（最多5个）

以JSON格式返回：
{{
  "architecture_pattern": "架构模式名称",
  "quality_score": 7.5,
  "issues": ["问题1", "问题2"],
  "recommendations": ["建议1", "建议2"],
  "layer_analysis": {{
    "层次名称": {{"count": 数量, "quality": "评价"}}
  }}
}}

只返回JSON，不要包含其他内容。
"""

        try:
            # 使用 adalflow.Generator 正确调用方式
            generator_output = self.generator(prompt_kwargs={"prompt": prompt})

            # 从 GeneratorOutput 中提取文本响应
            if hasattr(generator_output, 'data') and generator_output.data:
                response = str(generator_output.data)
            else:
                response = str(generator_output)

            # 尝试解析JSON
            # 清理响应（移除可能的markdown代码块标记）
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])

            data = json.loads(response)

            insight = ArchitectureInsight(
                architecture_pattern=data.get('architecture_pattern', '未知'),
                quality_score=float(data.get('quality_score', 0.0)),
                issues=data.get('issues', []),
                recommendations=data.get('recommendations', []),
                layer_analysis=data.get('layer_analysis', {})
            )

            self.architecture_insights = insight
            return insight

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse architecture insights JSON: {e}")
            logger.error(f"Response: {response}")
            return ArchitectureInsight(
                architecture_pattern="解析失败",
                quality_score=0.0,
                issues=["AI分析结果解析失败"],
                recommendations=["请检查LLM配置"],
                layer_analysis={}
            )
        except Exception as e:
            logger.error(f"Error generating architecture insights: {e}")
            return ArchitectureInsight(
                architecture_pattern="生成失败",
                quality_score=0.0,
                issues=[str(e)],
                recommendations=[],
                layer_analysis={}
            )

    def analyze_with_ai(self) -> Dict[str, Any]:
        """执行完整的AI增强分析

        Returns:
            包含所有AI增强数据的字典
        """
        logger.info("Starting AI-enhanced code analysis...")

        # 1. 先执行基础静态分析
        codemap = self.analyze()

        if not self.ai_enabled:
            logger.warning("AI features disabled, returning basic codemap")
            return codemap.to_dict()

        # 2. 生成AI注解
        try:
            annotations = self.generate_ai_annotations(max_nodes=50)
            logger.info(f"Generated {len(annotations)} AI annotations")
        except Exception as e:
            logger.error(f"Error generating annotations: {e}")
            annotations = {}

        # 3. 识别执行路径
        try:
            paths = self.identify_key_execution_paths(max_paths=10)
            logger.info(f"Identified {len(paths)} execution paths")
        except Exception as e:
            logger.error(f"Error identifying execution paths: {e}")
            paths = []

        # 4. 生成架构洞察
        try:
            insights = self.generate_architecture_insights()
            logger.info(f"Generated architecture insights: {insights.architecture_pattern}")
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            insights = None

        # 5. 组合结果
        result = codemap.to_dict()
        result['ai_enhanced'] = True
        result['ai_annotations'] = annotations
        result['execution_paths'] = [
            {
                'entry_point': p.entry_point,
                'path_nodes': p.path_nodes,
                'description': p.description,
                'importance_score': p.importance_score
            }
            for p in paths
        ]

        if insights:
            result['architecture_insights'] = {
                'architecture_pattern': insights.architecture_pattern,
                'quality_score': insights.quality_score,
                'issues': insights.issues,
                'recommendations': insights.recommendations,
                'layer_analysis': insights.layer_analysis
            }

        logger.info("AI-enhanced analysis complete")
        return result


def analyze_repository_with_ai(repo_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """分析代码仓库（AI增强版本）

    Args:
        repo_path: 仓库路径
        options: 分析选项

    Returns:
        AI增强的代码地图字典
    """
    analyzer = AIEnhancedCodeAnalyzer(repo_path, options)
    return analyzer.analyze_with_ai()
