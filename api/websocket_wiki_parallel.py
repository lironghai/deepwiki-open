"""
串行Wiki生成WebSocket端点
使用ParallelWikiGenerator但串行调用（max_workers=1或逐个调用）
"""

import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from urllib.parse import unquote

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from api.config import get_model_config, configs
from api.tools.wiki_generator import ParallelWikiGenerator, PageGenerationResult
from api.tools.mermaid_preprocessor import MermaidPreprocessor
from api.data_pipeline import DatabaseManager
from adalflow.utils import get_adalflow_default_root_path

from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class WikiGenerationRequest(BaseModel):
    """Wiki串行生成请求"""
    repo_url: str = Field(..., description="Repository URL")
    repo_type: str = Field("github", description="Repository type")
    token: Optional[str] = Field(None, description="Access token")
    pages: List[Dict[str, Any]] = Field(..., description="List of pages to generate")
    provider: str = Field("google", description="Model provider")
    model: Optional[str] = Field(None, description="Model name")
    language: str = Field("en", description="Language")


class MockLLMService:
    """Mock LLM服务，用于生成内容"""
    def __init__(self, generator, model_client, model_kwargs):
        self.generator = generator
        self.model_client = model_client
        self.model_kwargs = model_kwargs

    async def generate(self, prompt: str) -> str:
        """生成内容"""
        try:
            # 直接使用model_client调用API，绕过Generator的模板处理
            from adalflow.core.types import ModelType

            # 构建API参数
            api_kwargs = self.model_client.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=self.model_kwargs,
                model_type=ModelType.LLM
            )

            # 调用API
            result = self.model_client.call(api_kwargs=api_kwargs, model_type=ModelType.LLM)

            # 提取响应
            if hasattr(result, 'data'):
                if isinstance(result.data, str):
                    return result.data
                if hasattr(result.data, 'answer'):
                    return result.data.answer
                return str(result.data)
            return str(result)
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise


def get_llm_service(provider: str, model: Optional[str]):
    """获取LLM服务实例"""
    from api.config import get_model_config
    from adalflow import Generator

    model_config = get_model_config(provider, model)

    # 创建model_client实例
    model_client = model_config["model_client"]()
    model_kwargs = model_config["model_kwargs"]

    # 创建简单的模板
    simple_template = "{{prompt}}"

    generator = Generator(
        template=simple_template,
        model_client=model_client,
        model_kwargs=model_kwargs
    )

    return MockLLMService(generator, model_client, model_kwargs)




async def handle_websocket_wiki_generate(websocket: WebSocket):
    """
    处理Wiki生成的WebSocket连接（串行模式，max_workers=1）
    """
    await websocket.accept()
    
    try:
        # 接收请求
        request_data = await websocket.receive_json()
        request = WikiGenerationRequest(**request_data)
        
        logger.info(f"Starting wiki generation for {len(request.pages)} pages (serial mode, max_workers=1)")
        
        # 提取repo路径
        url_parts = request.repo_url.rstrip('/').split('/')
        if request.repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
            owner = url_parts[-2]
            repo_name = url_parts[-1].replace(".git", "")
            repo_path = os.path.join(get_adalflow_default_root_path(), "repos", f"{owner}_{repo_name}")
        else:
            repo_path = request.repo_url
        
        if not os.path.exists(repo_path):
            try:
                await websocket.send_json({
                    "stage": "error",
                    "error": f"Repository not found at {repo_path}"
                })
            except (RuntimeError, Exception):
                pass  # WebSocket可能已关闭
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass
            return
        
        # 发送开始消息
        try:
            await websocket.send_json({
                "stage": "started",
                "progress": 0,
                "total_pages": len(request.pages)
            })
        except (RuntimeError, Exception) as e:
            logger.warning(f"Could not send start message: {e}")
            return
        
        # 获取LLM服务
        try:
            llm_service = get_llm_service(request.provider, request.model)
        except Exception as e:
            logger.error(f"Failed to create LLM service: {e}")
            try:
                await websocket.send_json({
                    "stage": "error",
                    "error": f"Failed to initialize LLM service: {str(e)}"
                })
            except (RuntimeError, Exception):
                pass  # WebSocket可能已关闭
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass
            return
        
        # 创建生成器（使用max_workers=1实现串行处理）
        generator = ParallelWikiGenerator(
            llm_service=llm_service,
            max_workers=1,  # 设置为1实现串行处理
            enable_codemap=True
        )
        
        # 串行生成页面（逐个处理，使用原有的generate_pages_parallel但max_workers=1）
        processed_results = []
        total_pages = len(request.pages)
        
        # 使用原有的生成方法，但通过max_workers=1确保串行
        results = await generator.generate_pages_parallel(
            pages=request.pages,
            repo_path=repo_path,
            progress_callback=None  # 不使用回调，手动发送进度
        )
        
        # 预处理Mermaid并格式化结果
        for result in results:
            # 发送进度更新
            try:
                await websocket.send_json({
                    "stage": "generating",
                    "progress": int(40 + (result.page_index / total_pages) * 50),  # 40-90%
                    "completed": result.page_index + 1,
                    "total": total_pages,
                    "current_page": result.title
                })
            except (RuntimeError, Exception) as e:
                logger.warning(f"WebSocket closed during generation: {e}")
                break  # 如果websocket已关闭，停止处理
            
            # 预处理Mermaid
            if result.content:
                processed_content = MermaidPreprocessor.extract_and_process_mermaid_blocks(result.content)
            else:
                processed_content = result.content
            
            processed_results.append({
                "page_index": result.page_index,
                "title": result.title,
                "content": processed_content,
                "success": result.success,
                "error": result.error,
                "codemap_used": result.codemap_used,
                "modules_referenced": result.modules_referenced,
                "generation_time_ms": result.generation_time_ms
            })
        
        # 使用生成器的统计方法
        statistics = generator.get_statistics(results)
        
        # 发送完成消息
        try:
            await websocket.send_json({
                "stage": "complete",
                "progress": 100,
                "pages": processed_results,
                "statistics": statistics
            })
        except (RuntimeError, Exception) as e:
            logger.warning(f"Could not send completion message: {e}")

        logger.info(f"Wiki generation completed: {len(processed_results)} pages (serial mode)")

        # Run GitNexus analysis after wiki is done so the graph is built from final repo state
        try:
            from api.gitnexus_cli import run_gitnexus_analyze
            if run_gitnexus_analyze(repo_path):
                logger.info("GitNexus analysis completed for repo at %s", repo_path)
            else:
                logger.warning("GitNexus analysis skipped or failed for repo at %s", repo_path)
        except Exception as gn_err:
            logger.warning("GitNexus post-wiki run failed: %s", gn_err)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in wiki generation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await websocket.send_json({
                "stage": "error",
                "error": str(e)
            })
        except (RuntimeError, Exception) as send_error:
            logger.debug(f"Could not send error message: {send_error}")
    finally:
        try:
            await websocket.close()
        except Exception as close_error:
            logger.debug(f"Error closing websocket: {close_error}")

