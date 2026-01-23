"""
Codemap增强功能的API端点
包含AI增强、RAG集成等新功能
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.ai_enhanced_analyzer import analyze_repository_with_ai
from api.call_graph_analyzer import CallGraphAnalyzer
from api.dataflow_analyzer import DataFlowAnalyzer
from api.code_analyzer import CodeAnalyzer, load_codemap
from api.codemap_enhanced_rag import CodemapEnhancedRAG, CodemapEnhancedDeepResearchRAG
from api.config import configs, get_model_config

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()


def get_adalflow_default_root_path():
    """获取adalflow根路径"""
    return os.path.expanduser(os.path.join("~", ".adalflow"))


def get_codemap_cache_path(owner: str, repo: str, repo_type: str) -> str:
    """获取Codemap缓存路径"""
    root = get_adalflow_default_root_path()
    cache_dir = os.path.join(root, "codemaps")
    os.makedirs(cache_dir, exist_ok=True)
    filename = f"codemap_{repo_type}_{owner}_{repo}.json"
    return os.path.join(cache_dir, filename)


# ========== 数据模型 ==========

class EnhancedCodemapRequest(BaseModel):
    """AI增强的Codemap生成请求"""
    repo_url: str = Field(..., description="Repository URL")
    repo_type: str = Field(default="github", description="Repository type")
    token: Optional[str] = Field(None, description="Access token for private repos")
    options: Optional[Dict[str, Any]] = Field(default={}, description="Analysis options")
    enable_ai: bool = Field(default=True, description="Enable AI enhancements")
    enable_call_graph: bool = Field(default=True, description="Enable call graph analysis")
    force_regenerate: bool = Field(default=False, description="Force regenerate codemap")


class CodemapWithRAGRequest(BaseModel):
    """支持Codemap的RAG请求"""
    repo_url: str = Field(..., description="Repository URL")
    repo_type: str = Field(default="github", description="Repository type")
    question: str = Field(..., description="User question")
    use_codemap: bool = Field(default=True, description="Use codemap context")
    deep_research: bool = Field(default=False, description="Enable deep research")

    # 模型参数（与前端Ask组件对齐）
    provider: Optional[str] = Field(None, description="Model provider")
    model: Optional[str] = Field(None, description="Model name")
    language: Optional[str] = Field("en", description="Language for responses")
    token: Optional[str] = Field(None, description="Repository access token")


class CallGraphQueryRequest(BaseModel):
    """调用图查询请求"""
    repo_url: str
    repo_type: str = "github"
    start_function: Optional[str] = None
    end_function: Optional[str] = None
    query_type: str = Field(default="hotspots", description="Query type: hotspots, entry_points, leaf_functions, call_chain")


class DataFlowQueryRequest(BaseModel):
    """数据流查询请求"""
    repo_url: str
    repo_type: str = "github"
    variable_name: str
    function_name: str
    file_path: Optional[str] = None


# ========== API端点 ==========

@router.post("/api/codemap/generate_enhanced")
async def generate_enhanced_codemap(request: EnhancedCodemapRequest):
    """生成AI增强的Codemap

    包含：
    - 基础静态分析
    - AI生成的注解
    - 执行路径识别
    - 架构洞察
    - 调用图分析（可选）
    """
    try:
        logger.info(f"Generating enhanced codemap for {request.repo_url}")

        # 解析仓库信息
        url_parts = request.repo_url.rstrip('/').split('/')
        if request.repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
            owner = url_parts[-2]
            repo_name = url_parts[-1].replace(".git", "")
        else:
            raise HTTPException(status_code=400, detail="Invalid repository URL format")

        # 检查缓存
        cache_path = get_codemap_cache_path(owner, repo_name, request.repo_type)

        if os.path.exists(cache_path) and not request.force_regenerate:
            logger.info(f"Loading enhanced codemap from cache: {cache_path}")
            try:
                codemap_data = load_codemap(cache_path)
                return {
                    "status": "success",
                    "source": "cache",
                    "data": codemap_data
                }
            except Exception as e:
                logger.warning(f"Failed to load cached codemap: {e}")

        # 获取或克隆仓库
        from api.data_pipeline import download_repo
        root_path = get_adalflow_default_root_path()
        repo_path = os.path.join(root_path, "repos", f"{owner}_{repo_name}")

        if not os.path.exists(repo_path):
            logger.info(f"Cloning repository to {repo_path}")
            await asyncio.to_thread(
                download_repo,
                request.repo_url,
                repo_path,
                request.repo_type,
                request.token
            )

        # 生成增强的Codemap
        if request.enable_ai:
            logger.info("Generating AI-enhanced codemap...")
            codemap_data = await asyncio.to_thread(
                analyze_repository_with_ai,
                repo_path,
                request.options
            )
        else:
            logger.info("Generating basic codemap...")
            from api.code_analyzer import analyze_repository
            codemap_data = await asyncio.to_thread(
                analyze_repository,
                repo_path,
                request.options
            )

        # 添加调用图分析
        if request.enable_call_graph:
            try:
                logger.info("Building call graph...")
                analyzer = CodeAnalyzer(repo_path, request.options)
                analyzer.nodes = [type('obj', (object,), d) for d in codemap_data['nodes']]  # 简化处理

                call_graph_analyzer = CallGraphAnalyzer(analyzer)
                call_graph_analyzer.build_call_graph()

                call_graph_data = call_graph_analyzer.export_call_graph()
                codemap_data['call_graph'] = call_graph_data

                logger.info("Call graph analysis complete")
            except Exception as e:
                logger.error(f"Error building call graph: {e}")
                codemap_data['call_graph'] = {'error': str(e)}

        # 添加元数据
        codemap_data['metadata']['repo_url'] = request.repo_url
        codemap_data['metadata']['repo_type'] = request.repo_type
        codemap_data['metadata']['owner'] = owner
        codemap_data['metadata']['repo'] = repo_name
        codemap_data['metadata']['generated_at'] = str(asyncio.get_event_loop().time())

        # 保存到缓存
        from api.code_analyzer import save_codemap
        await asyncio.to_thread(save_codemap, codemap_data, cache_path)

        return {
            "status": "success",
            "source": "generated",
            "data": codemap_data
        }

    except Exception as e:
        logger.error(f"Error generating enhanced codemap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/chat/with_codemap")
async def chat_with_codemap(request: CodemapWithRAGRequest):
    """支持Codemap的聊天端点

    在RAG查询中整合Codemap上下文
    """
    try:
        logger.info(f"Chat with codemap for {request.repo_url}: {request.question}")

        # 解析仓库信息
        url_parts = request.repo_url.rstrip('/').split('/')
        if request.repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
            owner = url_parts[-2]
            repo_name = url_parts[-1].replace(".git", "")
        else:
            raise HTTPException(status_code=400, detail="Invalid repository URL format")

        # 获取仓库路径
        root_path = get_adalflow_default_root_path()
        repo_path = os.path.join(root_path, "repos", f"{owner}_{repo_name}")

        if not os.path.exists(repo_path):
            raise HTTPException(status_code=404, detail="Repository not found. Please generate wiki first.")

        # 初始化增强的RAG
        # 使用请求中的provider和model，如果没有则使用配置文件默认值
        # 使用与正常提问接口一致的配置获取方式
        default_provider = configs.get('default_provider', 'google')
        providers = configs.get('providers', {})

        # 使用请求参数或配置默认值
        selected_provider = request.provider or default_provider

        if not providers or selected_provider not in providers:
            available_providers = ', '.join(providers.keys()) if providers else 'none'
            raise HTTPException(
                status_code=500,
                detail=f"Provider '{selected_provider}' not found in configuration. Available providers: {available_providers}"
            )

        # 使用与正常提问接口一致的初始化方式
        # 直接传递provider和model参数，RAG类内部会调用get_model_config获取配置
        selected_model = request.model

        logger.info(f"Using provider: {selected_provider}, model: {selected_model}")

        if request.deep_research:
            rag = CodemapEnhancedDeepResearchRAG(provider=selected_provider, model=selected_model)
        else:
            rag = CodemapEnhancedRAG(provider=selected_provider, model=selected_model)

        # 准备retriever（从向量数据库检索）
        try:
            logger.info(f"Preparing retriever for {repo_path}")
            rag.prepare_retriever(
                repo_url_or_path=repo_path,
                type=request.repo_type,
                access_token=request.token
            )
        except Exception as e:
            logger.error(f"Failed to prepare retriever: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to prepare retriever: {str(e)}"
            )

        # 加载Codemap
        if request.use_codemap:
            try:
                rag.load_codemap(repo_path)
                logger.info("Codemap loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load codemap: {e}")

        # 执行查询（包含向量检索和Codemap上下文）
        # RAG的call方法会自动进行向量检索
        response = rag.call(
            question=request.question,
            context=None,  # RAG会自动通过retriever检索上下文
            language=request.language
        )

        # 获取引用的节点
        referenced_nodes = rag.get_referenced_nodes()

        # 获取Codemap摘要
        codemap_summary = rag.get_codemap_summary()

        # Extract the actual answer from the GeneratorOutput object
        answer_text = ""
        if response and hasattr(response, 'data') and response.data:
            answer_text = response.data.answer if hasattr(response.data, 'answer') else str(response.data)

        return {
            "status": "success",
            "answer": answer_text,
            "referenced_nodes": referenced_nodes,
            "codemap_summary": codemap_summary,
            "used_codemap": request.use_codemap
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat with codemap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/codemap/call_graph")
async def query_call_graph(request: CallGraphQueryRequest):
    """查询调用图信息

    支持的查询类型：
    - hotspots: 热点函数
    - entry_points: 入口点
    - leaf_functions: 叶子函数
    - call_chain: 调用链（需要start_function和end_function）
    """
    try:
        # 解析仓库信息
        url_parts = request.repo_url.rstrip('/').split('/')
        if request.repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
            owner = url_parts[-2]
            repo_name = url_parts[-1].replace(".git", "")
        else:
            raise HTTPException(status_code=400, detail="Invalid repository URL format")

        # 获取仓库路径
        root_path = get_adalflow_default_root_path()
        repo_path = os.path.join(root_path, "repos", f"{owner}_{repo_name}")

        if not os.path.exists(repo_path):
            raise HTTPException(status_code=404, detail="Repository not found")

        # 加载Codemap（如果存在）
        cache_path = get_codemap_cache_path(owner, repo_name, request.repo_type)
        if os.path.exists(cache_path):
            codemap_data = load_codemap(cache_path)

            # 检查是否有call_graph数据
            if 'call_graph' in codemap_data:
                call_graph_data = codemap_data['call_graph']

                if request.query_type == "hotspots":
                    return {"status": "success", "data": call_graph_data.get('hotspots', [])}
                elif request.query_type == "entry_points":
                    return {"status": "success", "data": call_graph_data.get('entry_points', [])}
                elif request.query_type == "leaf_functions":
                    return {"status": "success", "data": call_graph_data.get('leaf_functions', [])}
                elif request.query_type == "call_chain":
                    if not request.start_function or not request.end_function:
                        raise HTTPException(status_code=400, detail="start_function and end_function required for call_chain query")

                    # 需要重新构建CallGraphAnalyzer来查询调用链
                    # 这里简化处理
                    return {
                        "status": "success",
                        "message": "Call chain analysis requires full codemap regeneration",
                        "start": request.start_function,
                        "end": request.end_function
                    }
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown query type: {request.query_type}")

        raise HTTPException(status_code=404, detail="Call graph data not found. Please regenerate codemap with call_graph enabled.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying call graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/codemap/dataflow")
async def query_dataflow(request: DataFlowQueryRequest):
    """查询数据流信息

    追踪指定变量在函数中的数据流
    """
    try:
        # 解析仓库信息
        url_parts = request.repo_url.rstrip('/').split('/')
        if request.repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
            owner = url_parts[-2]
            repo_name = url_parts[-1].replace(".git", "")
        else:
            raise HTTPException(status_code=400, detail="Invalid repository URL format")

        # 获取仓库路径
        root_path = get_adalflow_default_root_path()
        repo_path = os.path.join(root_path, "repos", f"{owner}_{repo_name}")

        if not os.path.exists(repo_path):
            raise HTTPException(status_code=404, detail="Repository not found")

        # 加载Codemap
        cache_path = get_codemap_cache_path(owner, repo_name, request.repo_type)
        if not os.path.exists(cache_path):
            raise HTTPException(status_code=404, detail="Codemap not found. Please generate codemap first.")

        codemap_data = load_codemap(cache_path)

        # 创建CodeAnalyzer
        analyzer = CodeAnalyzer(repo_path)
        # 简化处理：从codemap_data重建节点
        # 实际应该完整重建analyzer

        # 创建DataFlowAnalyzer
        dataflow_analyzer = DataFlowAnalyzer(analyzer)

        # 查找目标函数节点
        target_func_node = None
        for node_data in codemap_data['nodes']:
            if node_data['name'] == request.function_name:
                if not request.file_path or node_data['path'] == request.file_path:
                    # 转换为CodeNode对象
                    from api.code_analyzer import CodeNode, NodeType
                    target_func_node = CodeNode(
                        id=node_data['id'],
                        name=node_data['name'],
                        type=NodeType(node_data['type']),
                        path=node_data['path'],
                        language=node_data.get('language'),
                        start_line=node_data.get('start_line'),
                        end_line=node_data.get('end_line')
                    )
                    break

        if not target_func_node:
            raise HTTPException(status_code=404, detail=f"Function '{request.function_name}' not found")

        # 追踪变量数据流
        flow_nodes = dataflow_analyzer.trace_variable_flow(
            request.variable_name,
            target_func_node
        )

        # 转换为可序列化的格式
        flow_data = [
            {
                'type': node.flow_type.value,
                'variable': node.variable_name,
                'line': node.line_number,
                'file': node.file_path,
                'snippet': node.code_snippet,
                'context': node.context
            }
            for node in flow_nodes
        ]

        return {
            "status": "success",
            "variable": request.variable_name,
            "function": request.function_name,
            "flow_count": len(flow_data),
            "flow": flow_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying dataflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/codemap/summary/{owner}/{repo}")
async def get_codemap_summary(owner: str, repo: str, repo_type: str = "github"):
    """获取Codemap摘要信息

    返回快速概览，不包含完整的节点和边数据
    """
    try:
        cache_path = get_codemap_cache_path(owner, repo, repo_type)

        if not os.path.exists(cache_path):
            raise HTTPException(status_code=404, detail="Codemap not found")

        codemap_data = load_codemap(cache_path)

        # 构建摘要
        summary = {
            "metadata": codemap_data.get('metadata', {}),
            "ai_enhanced": codemap_data.get('ai_enhanced', False),
            "has_annotations": bool(codemap_data.get('ai_annotations')),
            "annotation_count": len(codemap_data.get('ai_annotations', {})),
            "has_execution_paths": bool(codemap_data.get('execution_paths')),
            "execution_path_count": len(codemap_data.get('execution_paths', [])),
            "has_architecture_insights": bool(codemap_data.get('architecture_insights')),
            "has_call_graph": bool(codemap_data.get('call_graph')),
        }

        # 添加架构洞察摘要
        if 'architecture_insights' in codemap_data:
            insights = codemap_data['architecture_insights']
            summary['architecture'] = {
                'pattern': insights.get('architecture_pattern'),
                'quality_score': insights.get('quality_score'),
                'issue_count': len(insights.get('issues', [])),
                'recommendation_count': len(insights.get('recommendations', []))
            }

        return {
            "status": "success",
            "summary": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting codemap summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
