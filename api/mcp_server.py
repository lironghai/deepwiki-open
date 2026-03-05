"""
DeepWiki MCP Server
使用 FastMCP 框架实现标准 MCP 协议

提供两个工具:
1. deepwiki_list_projects - 列出已解析的仓库，支持名称模糊查询
2. deepwiki_ask - 针对已解析的仓库提问，支持深度研究参数控制
"""

import asyncio
import logging
import os
from typing import Optional, List

from fastmcp import FastMCP

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastMCP 服务器实例
mcp = FastMCP(name="deepwiki-mcp")

# 获取adalflow默认路径
def get_adalflow_default_root_path():
    return os.path.expanduser(os.path.join("~", ".adalflow"))

WIKI_CACHE_DIR = os.path.join(get_adalflow_default_root_path(), "wikicache")


# ============================================
# 辅助函数
# ============================================

def parse_cache_filename(filename: str) -> Optional[dict]:
    """解析缓存文件名，提取仓库信息"""
    if not filename.startswith("deepwiki_cache_") or not filename.endswith(".json"):
        return None
    
    try:
        parts = filename.replace("deepwiki_cache_", "").replace(".json", "").split('_')
        if len(parts) >= 4:
            repo_type = parts[0]
            owner = parts[1]
            language = parts[-1]
            repo = "_".join(parts[2:-1])
            
            return {
                "id": filename,
                "owner": owner,
                "repo": repo,
                "name": f"{owner}/{repo}",
                "repo_type": repo_type,
                "language": language
            }
    except Exception as e:
        logger.error(f"Error parsing filename {filename}: {e}")
    
    return None


def list_processed_projects(query: Optional[str] = None) -> List[dict]:
    """列出所有已处理的项目，支持模糊查询"""
    projects = []
    
    if not os.path.exists(WIKI_CACHE_DIR):
        logger.info(f"Cache directory {WIKI_CACHE_DIR} not found")
        return []
    
    try:
        filenames = os.listdir(WIKI_CACHE_DIR)
        
        for filename in filenames:
            project = parse_cache_filename(filename)
            if project:
                if query:
                    query_lower = query.lower()
                    if (query_lower in project["owner"].lower() or 
                        query_lower in project["repo"].lower() or
                        query_lower in project["name"].lower()):
                        file_path = os.path.join(WIKI_CACHE_DIR, filename)
                        stat = os.stat(file_path)
                        project["submitted_at"] = int(stat.st_mtime * 1000)
                        projects.append(project)
                else:
                    file_path = os.path.join(WIKI_CACHE_DIR, filename)
                    stat = os.stat(file_path)
                    project["submitted_at"] = int(stat.st_mtime * 1000)
                    projects.append(project)
        
        projects.sort(key=lambda p: p.get("submitted_at", 0), reverse=True)
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
    
    return projects


def get_repo_url_from_project(project: dict) -> str:
    """根据项目信息构建仓库URL"""
    repo_type = project.get("repo_type", "github")
    owner = project.get("owner", "")
    repo = project.get("repo", "")
    
    if repo_type == "github":
        return f"https://github.com/{owner}/{repo}"
    elif repo_type == "gitlab":
        return f"https://gitlab.com/{owner}/{repo}"
    elif repo_type == "bitbucket":
        return f"https://bitbucket.org/{owner}/{repo}"
    else:
        return f"https://github.com/{owner}/{repo}"


def find_project_by_name(repo_name: str) -> Optional[dict]:
    """通过仓库名称查找项目"""
    projects = list_processed_projects()
    
    for project in projects:
        if project["name"].lower() == repo_name.lower():
            return project
    
    for project in projects:
        if project["repo"].lower() == repo_name.lower():
            return project
    
    for project in projects:
        if repo_name.lower() in project["name"].lower():
            return project
    
    return None


# ============================================
# 工具实现函数（核心逻辑）
# ============================================

async def _impl_list_projects(query: Optional[str] = None) -> str:
    """列出已解析的所有仓库 - 核心实现，返回半结构化格式"""
    try:
        projects = list_processed_projects(query)
        
        if not projects:
            if query:
                return f"未找到包含 '{query}' 的已解析仓库。"
            else:
                return "没有找到已解析的仓库。请先通过DeepWiki页面解析仓库。"
        
        result_lines = [f"找到 {len(projects)} 个已解析的仓库:\n"]
        result_lines.append("=" * 50)
        
        for i, project in enumerate(projects, 1):
            result_lines.append(f"\n## 仓库 {i}")
            result_lines.append(f"repo: {project['name']}")
            result_lines.append(f"from_type: {project['repo_type']}")
            result_lines.append(f"language: {project['language']}")
            result_lines.append(f"owner: {project['owner']}")
            result_lines.append(f"repo_name: {project['repo']}")
            result_lines.append("-" * 30)
        
        result_lines.append(f"\n## 使用说明")
        result_lines.append("调用 deepwiki_ask 工具时，repo 参数可使用上述 repo 字段值（如 owner/repo_name）")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error in _impl_list_projects: {e}")
        return f"查询仓库列表时出错: {str(e)}"


async def _impl_ask(
    repo: str,
    question: str,
    deep_research: bool = False,
    language: str = "zh",
    file_path: Optional[str] = None
) -> str:
    """针对已解析的仓库提问 - 核心实现"""
    if not repo or not question:
        return "错误: 必须提供 repo 和 question 参数"
    
    project = find_project_by_name(repo)
    if not project:
        available = list_processed_projects()
        if available:
            names = [p["name"] for p in available[:10]]
            hint = f"可用的仓库: {', '.join(names)}"
            if len(available) > 10:
                hint += f" 等共 {len(available)} 个"
        else:
            hint = "请先通过DeepWiki页面解析仓库"
        
        return f"未找到仓库 '{repo}'。{hint}"
    
    repo_url = get_repo_url_from_project(project)
    
    try:
        answer = await perform_rag_query(
            repo_url=repo_url,
            repo_type=project["repo_type"],
            question=question,
            deep_research=deep_research,
            language=language,
            file_path=file_path
        )
        
        header = f"**仓库**: {project['name']} ({project['repo_type']})\n"
        # header += f"**问题**: {question}\n"
        if deep_research:
            header += "**模式**: 深度研究\n"
        header += "\n---\n\n"
        
        return header + answer
        
    except Exception as e:
        logger.error(f"Error in _impl_ask: {e}")
        return f"处理提问时出错: {str(e)}"


# ============================================
# MCP 工具定义 (用于 stdio 模式)
# ============================================

@mcp.tool()
async def deepwiki_list_projects(query: Optional[str] = None) -> str:
    """
    列出已解析的所有仓库，支持名称模糊查询。
    
    Args:
        query: 可选，仓库名称模糊查询关键词，会在owner和repo名称中搜索
    
    Returns:
        已解析仓库列表，包含owner、repo、类型等信息
    """
    return await _impl_list_projects(query)


@mcp.tool()
async def deepwiki_ask(
    repo: str,
    question: str,
    deep_research: bool = False,
    language: str = "en",
    file_path: Optional[str] = None
) -> str:
    """
    针对已解析的仓库提问，获取代码相关问题的答案。
    
    Args:
        repo: 仓库名称，支持格式: 'owner/repo' 或 'repo'
        question: 要问的问题
        deep_research: 是否启用深度研究模式，默认false。启用后会进行多轮迭代分析
        language: 回答语言，默认 'en'。支持: en, zh, ja, es, kr, vi 等
        file_path: 可选，指定要分析的文件路径
    
    Returns:
        针对问题的回答
    """
    return await _impl_ask(repo, question, deep_research, language, file_path)


# ============================================
# RAG 查询实现
# ============================================

async def call_llm(provider: str, model_config: dict, prompt: str) -> str:
    """
    根据 provider 调用对应的 LLM，返回完整响应文本
    """
    from adalflow.core.types import ModelType
    
    model_name = model_config.get("model", "")
    temperature = model_config.get("temperature", 0.7)
    top_p = model_config.get("top_p", 0.8)
    
    if provider == "dashscope":
        from api.dashscope_client import DashscopeClient
        from adalflow.core.types import GeneratorOutput
        client = DashscopeClient()
        model_kwargs = {
            "model": model_name,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
        }
        api_kwargs = client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=model_kwargs,
            model_type=ModelType.LLM
        )
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        # DashscopeClient 非流式返回 GeneratorOutput 对象
        if isinstance(response, GeneratorOutput):
            return response.data if response.data else ""
        if isinstance(response, str):
            return response
        # 尝试从 data 属性获取
        if hasattr(response, 'data'):
            return response.data if response.data else ""
        return str(response)
    
    elif provider == "openai":
        from api.openai_client import OpenAIClient
        from adalflow.core.types import GeneratorOutput
        client = OpenAIClient()
        model_kwargs = {
            "model": model_name,
            "stream": False,
            "temperature": temperature,
        }
        if top_p:
            model_kwargs["top_p"] = top_p
        api_kwargs = client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=model_kwargs,
            model_type=ModelType.LLM
        )
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        # 处理 GeneratorOutput 类型
        if isinstance(response, GeneratorOutput):
            return response.data if response.data else ""
        if isinstance(response, str):
            return response
        if hasattr(response, 'data'):
            return response.data if response.data else ""
        # 处理 OpenAI 响应格式
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        return str(response)
    
    elif provider == "openrouter":
        from api.openrouter_client import OpenRouterClient
        from adalflow.core.types import GeneratorOutput
        client = OpenRouterClient()
        model_kwargs = {
            "model": model_name,
            "stream": False,
            "temperature": temperature,
        }
        if top_p:
            model_kwargs["top_p"] = top_p
        api_kwargs = client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=model_kwargs,
            model_type=ModelType.LLM
        )
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        if isinstance(response, GeneratorOutput):
            return response.data if response.data else ""
        if isinstance(response, str):
            return response
        if hasattr(response, 'data'):
            return response.data if response.data else ""
        return str(response)
    
    elif provider == "ollama":
        from adalflow.components.model_client.ollama_client import OllamaClient
        from adalflow.core.types import GeneratorOutput
        client = OllamaClient()
        model_kwargs = {
            "model": model_name,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": model_config.get("num_ctx", 32000)
            }
        }
        api_kwargs = client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=model_kwargs,
            model_type=ModelType.LLM
        )
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        if isinstance(response, GeneratorOutput):
            return response.data if response.data else ""
        if hasattr(response, 'data'):
            return response.data if response.data else ""
        if hasattr(response, 'response'):
            return response.response
        return str(response)
    
    elif provider == "bedrock":
        from api.bedrock_client import BedrockClient
        from adalflow.core.types import GeneratorOutput
        client = BedrockClient()
        model_kwargs = {
            "model": model_name,
            "temperature": temperature,
            "top_p": top_p
        }
        api_kwargs = client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=model_kwargs,
            model_type=ModelType.LLM
        )
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        if isinstance(response, GeneratorOutput):
            return response.data if response.data else ""
        if isinstance(response, str):
            return response
        if hasattr(response, 'data'):
            return response.data if response.data else ""
        return str(response)
    
    elif provider == "azure":
        from api.azureai_client import AzureAIClient
        from adalflow.core.types import GeneratorOutput
        client = AzureAIClient()
        model_kwargs = {
            "model": model_name,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p
        }
        api_kwargs = client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=model_kwargs,
            model_type=ModelType.LLM
        )
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        if isinstance(response, GeneratorOutput):
            return response.data if response.data else ""
        if isinstance(response, str):
            return response
        if hasattr(response, 'data'):
            return response.data if response.data else ""
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        return str(response)
    
    else:
        # Google (默认)
        import google.generativeai as genai
        generation_config = {
            "temperature": temperature,
            "top_p": top_p,
        }
        if "top_k" in model_config:
            generation_config["top_k"] = model_config["top_k"]
        
        model = genai.GenerativeModel(
            model_name=model_name or "gemini-2.0-flash",
            generation_config=generation_config,
        )
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        return str(response)


async def perform_rag_query(
    repo_url: str,
    repo_type: str,
    question: str,
    deep_research: bool = False,
    language: str = "zh",
    file_path: Optional[str] = None
) -> str:
    """执行RAG查询，使用配置中的 default_provider 和 default_model"""
    from api.rag import RAG
    from api.config import configs, get_model_config
    from api.prompts import (
        DEEP_RESEARCH_FIRST_ITERATION_PROMPT,
        SIMPLE_CHAT_SYSTEM_PROMPT
    )
    from api.data_pipeline import get_file_content
    
    # 从配置获取默认 provider 和 model
    default_provider = configs.get("default_provider", "google")
    provider_config = configs.get("providers", {}).get(default_provider, {})
    
    # 深度研究使用 default_deep_research_model，普通查询使用 default_model
    if deep_research:
        default_model = provider_config.get("default_deep_research_model") or provider_config.get("default_model")
        logger.info(f"MCP Deep Research using provider: {default_provider}, model: {default_model}")
    else:
        default_model = provider_config.get("default_model")
        logger.info(f"MCP RAG Query using provider: {default_provider}, model: {default_model}")
    
    request_rag = RAG(provider=default_provider, model=default_model)
    
    await asyncio.to_thread(
        request_rag.prepare_retriever,
        repo_url, repo_type, None,
        None, None, None, None
    )
    
    context_text = ""
    try:
        rag_query = question
        if file_path:
            rag_query = f"Contexts related to {file_path}"
        
        retrieved_documents = request_rag(rag_query, language=language)
        
        if retrieved_documents and retrieved_documents[0].documents:
            documents = retrieved_documents[0].documents
            docs_by_file = {}
            for doc in documents:
                fp = doc.meta_data.get('file_path', 'unknown')
                if fp not in docs_by_file:
                    docs_by_file[fp] = []
                docs_by_file[fp].append(doc)
            
            context_parts = []
            for fp, docs in docs_by_file.items():
                header = f"## File Path: {fp}\n\n"
                content = "\n\n".join([doc.text for doc in docs])
                context_parts.append(f"{header}{content}")
            
            context_text = "\n\n" + "-" * 10 + "\n\n".join(context_parts)
    except Exception as e:
        logger.error(f"Error in RAG retrieval: {e}")
    
    repo_name = repo_url.split("/")[-1] if "/" in repo_url else repo_url
    supported_langs = configs["lang_config"]["supported_languages"]
    language_name = supported_langs.get(language, "Chinese")
    
    if deep_research:
        system_prompt = DEEP_RESEARCH_FIRST_ITERATION_PROMPT.format(
            repo_type=repo_type,
            repo_url=repo_url,
            repo_name=repo_name,
            language_name=language_name
        )
    else:
        system_prompt = SIMPLE_CHAT_SYSTEM_PROMPT.format(
            repo_type=repo_type,
            repo_url=repo_url,
            repo_name=repo_name,
            language_name=language_name
        )
    
    file_content = ""
    if file_path:
        try:
            file_content = get_file_content(repo_url, file_path, repo_type, None)
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
    
    prompt = f"/no_think {system_prompt}\n\n"
    
    if file_content:
        prompt += f"<currentFileContent path=\"{file_path}\">\n{file_content}\n</currentFileContent>\n\n"
    
    if context_text.strip():
        prompt += "<START_OF_CONTEXT>\n"
        prompt += "The following are ACTUAL code snippets retrieved from the repository. You MUST ONLY reference files and code that appear below. Do NOT invent or fabricate any file paths or code not shown here.\n"
        prompt += f"{context_text}\n<END_OF_CONTEXT>\n\n"
    else:
        prompt += "<note>No relevant code snippets were retrieved from the repository. You should inform the user that you cannot find relevant information in the repository context rather than guessing.</note>\n\n"
    
    prompt += f"<query>\n{question}\n</query>\n\nAssistant: "
    
    # 获取模型配置
    model_config = get_model_config(default_provider, default_model)["model_kwargs"]
    
    # 调用 LLM
    answer = await call_llm(default_provider, model_config, prompt)
    
    if deep_research:
        answer = await perform_deep_research_iterations(
            request_rag=request_rag,
            initial_response=answer,
            question=question,
            repo_url=repo_url,
            repo_type=repo_type,
            repo_name=repo_name,
            language=language,
            language_name=language_name,
            model_config=model_config,
            provider=default_provider
        )
    
    return answer


async def perform_deep_research_iterations(
    request_rag,
    initial_response: str,
    question: str,
    repo_url: str,
    repo_type: str,
    repo_name: str,
    language: str,
    language_name: str,
    model_config: dict,
    provider: str = "google",
    max_iterations: int = 3
) -> str:
    """执行深度研究的多轮迭代"""
    from api.prompts import (
        DEEP_RESEARCH_INTERMEDIATE_ITERATION_PROMPT,
        DEEP_RESEARCH_FINAL_ITERATION_PROMPT
    )
    
    all_responses = [initial_response]
    current_response = initial_response
    
    def is_complete(content: str) -> bool:
        markers = [
            '## Final Conclusion',
            'This concludes our research',
            'This completes our investigation',
            'Key Findings and Implementation Details'
        ]
        return any(marker in content for marker in markers)
    
    if is_complete(initial_response):
        return initial_response
    
    for iteration in range(2, max_iterations + 2):
        conversation_history = ""
        for i, resp in enumerate(all_responses):
            if i == 0:
                conversation_history += f"<turn>\n<user>{question}</user>\n<assistant>{resp}</assistant>\n</turn>\n"
            else:
                conversation_history += f"<turn>\n<user>Continue the research</user>\n<assistant>{resp}</assistant>\n</turn>\n"
        
        if iteration >= max_iterations + 1:
            system_prompt = DEEP_RESEARCH_FINAL_ITERATION_PROMPT.format(
                repo_type=repo_type,
                repo_url=repo_url,
                repo_name=repo_name,
                research_iteration=iteration,
                language_name=language_name
            )
        else:
            system_prompt = DEEP_RESEARCH_INTERMEDIATE_ITERATION_PROMPT.format(
                repo_type=repo_type,
                repo_url=repo_url,
                repo_name=repo_name,
                research_iteration=iteration,
                language_name=language_name
            )
        
        context_text = ""
        try:
            retrieved_documents = request_rag(question, language=language)
            if retrieved_documents and retrieved_documents[0].documents:
                documents = retrieved_documents[0].documents
                docs_by_file = {}
                for doc in documents:
                    fp = doc.meta_data.get('file_path', 'unknown')
                    if fp not in docs_by_file:
                        docs_by_file[fp] = []
                    docs_by_file[fp].append(doc)
                
                context_parts = []
                for fp, docs in docs_by_file.items():
                    header = f"## File Path: {fp}\n\n"
                    content = "\n\n".join([doc.text for doc in docs])
                    context_parts.append(f"{header}{content}")
                
                context_text = "\n\n" + "-" * 10 + "\n\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error in iteration {iteration} RAG retrieval: {e}")
        
        prompt = f"{system_prompt}\n\n"
        prompt += f"<conversation_history>\n{conversation_history}</conversation_history>\n\n"
        
        if context_text.strip():
            prompt += "<START_OF_CONTEXT>\n"
            prompt += "The following are ACTUAL code snippets retrieved from the repository. You MUST ONLY reference files and code that appear below. Do NOT invent or fabricate any file paths or code not shown here.\n"
            prompt += f"{context_text}\n<END_OF_CONTEXT>\n\n"
        
        prompt += f"<query>\nContinue the research on: {question}\n</query>\n\nAssistant: "
        
        # 使用 call_llm 调用配置的 provider
        current_response = await call_llm(provider, model_config, prompt)
        
        all_responses.append(current_response)
        
        if is_complete(current_response):
            break
    
    final_output = "\n\n---\n\n".join(all_responses)
    return final_output


# ============================================
# FastAPI 集成 (使用路由方式)
# ============================================

def create_mcp_routes():
    """
    创建MCP路由，用于集成到现有FastAPI应用
    
    实现 Streamable HTTP 传输协议，同时复用 FastMCP 定义的工具
    """
    import json as json_module
    from fastapi import APIRouter, Request
    from fastapi.responses import Response
    from pydantic import BaseModel
    
    def make_json_response(data: dict, status_code: int = 200) -> Response:
        """创建 JSON 响应，确保 Content-Length 正确"""
        content = json_module.dumps(data, ensure_ascii=False)
        return Response(
            content=content,
            status_code=status_code,
            media_type="application/json"
        )
    
    router = APIRouter(prefix="/mcp", tags=["MCP"])
    
    # 获取工具列表（从 FastMCP 装饰器注册的工具）
    def get_tools_list():
        return [
            {
                "name": "deepwiki_list_projects",
                "description": "列出已解析的所有仓库，支持名称模糊查询。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "可选，仓库名称模糊查询关键词"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "deepwiki_ask",
                "description": "项目代码理解助手，针对已解析的仓库提问，获取代码相关问题的答案。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "仓库名称，可以是完整名称(如owner/repo)或部分名称进行模糊匹配"
                        },
                        "question": {
                            "type": "string",
                            "description": "要询问的问题，关于代码库的任何技术问题"
                        },
                        "deep_research": {
                            "type": "boolean",
                            "default": False,
                            "description": "是否启用深度研究模式，启用后会进行更深入的代码分析，耗时更长但结果更详细"
                        },
                        "language": {
                            "type": "string",
                            "default": "zh",
                            "description": "回答使用的语言，如 'zh'(中文)、'en'(英文)、'ja'(日文) 等"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "可选，指定要查询的文件路径，用于限定问题范围到特定文件"
                        }
                    },
                    "required": ["repo", "question"]
                }
            }
        ]
    
    async def call_tool_by_name(name: str, arguments: dict) -> str:
        """调用工具 - 使用核心实现函数"""
        if name == "deepwiki_list_projects":
            return await _impl_list_projects(**arguments)
        elif name == "deepwiki_ask":
            return await _impl_ask(**arguments)
        else:
            return f"未知工具: {name}"
    
    @router.post("")
    @router.post("/")
    async def handle_mcp_request(request: Request):
        """
        MCP Streamable HTTP 主端点
        处理所有 JSON-RPC 2.0 请求
        """
        try:
            body = await request.json()
            method = body.get("method")
            params = body.get("params", {})
            msg_id = body.get("id")
            
            if method == "initialize":
                return make_json_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "deepwiki-mcp", "version": "1.0.0"}
                    }
                })
            
            elif method in ["notifications/initialized", "initialized"]:
                if msg_id is None:
                    return Response(status_code=204)
                return make_json_response({"jsonrpc": "2.0", "id": msg_id, "result": {}})
            
            elif method == "tools/list":
                return make_json_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": get_tools_list()}
                })
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await call_tool_by_name(tool_name, arguments)
                return make_json_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": result}]}
                })
            
            elif method == "ping":
                return make_json_response({"jsonrpc": "2.0", "id": msg_id, "result": {}})
            
            else:
                return make_json_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                })
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return make_json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            })
    
    class ToolCallRequest(BaseModel):
        name: str
        arguments: dict = {}
    
    @router.get("/tools")
    async def list_tools():
        """便捷API: 列出工具"""
        return make_json_response({"tools": get_tools_list()})
    
    @router.post("/tools/call")
    async def call_tool_endpoint(req: ToolCallRequest):
        """便捷API: 调用工具"""
        try:
            result = await call_tool_by_name(req.name, req.arguments)
            return make_json_response({"result": result})
        except Exception as e:
            return make_json_response({"error": str(e)}, status_code=500)
    
    @router.get("/health")
    async def mcp_health():
        """健康检查"""
        return make_json_response({"status": "healthy", "service": "deepwiki-mcp"})
    
    return router


def get_mcp_app():
    """
    返回 MCP 路由（用于 app.include_router）
    """
    return create_mcp_routes()


# ============================================
# 独立 HTTP 服务
# ============================================

def create_standalone_app():
    """
    创建独立的 FastAPI 应用
    用于 MCP 服务独占端口运行
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title="DeepWiki MCP Server",
        description="MCP Server for DeepWiki - 与已解析的代码仓库交互问答",
        version="1.0.0"
    )
    
    # 添加 CORS 支持
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加 MCP 路由
    app.include_router(create_mcp_routes())
    
    # 根路径
    @app.get("/")
    async def root():
        return {
            "service": "DeepWiki MCP Server",
            "version": "1.0.0",
            "endpoints": {
                "mcp": "POST /mcp/ - MCP JSON-RPC endpoint",
                "tools": "GET /mcp/tools - List available tools",
                "call": "POST /mcp/tools/call - Call a tool directly",
                "health": "GET /mcp/health - Health check"
            }
        }
    
    return app


# ============================================
# 启动入口
# ============================================

def main():
    """主入口点"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="DeepWiki MCP Server")
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode (standalone server)")
    parser.add_argument("--port", type=int, default=8002, help="Port for HTTP mode (default: 8002)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host for HTTP mode (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    if args.http:
        # HTTP 模式 - 启动独立的 FastAPI 服务
        import uvicorn
        
        logger.info(f"Starting DeepWiki MCP Server (HTTP mode) on {args.host}:{args.port}...")
        logger.info(f"MCP endpoint: http://{args.host}:{args.port}/mcp/")
        logger.info(f"Tools list: http://{args.host}:{args.port}/mcp/tools")
        
        uvicorn.run(
            create_standalone_app(),
            host=args.host,
            port=args.port,
            log_level="info"
        )
    else:
        # 默认 stdio 模式
        logger.info("Starting DeepWiki MCP Server (stdio mode)...")
        mcp.run()


if __name__ == "__main__":
    main()
