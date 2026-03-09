"""
Tool call handler for Agentic RAG.

When openai-agents SDK is available and provider is OpenAI-compatible, uses
Runner.run_streamed (SDK owns the loop). Otherwise uses the hand-written
for-loop (run_agent_loop_for_loop_backup). Yields structured messages that
callers (WebSocket / HTTP) can forward to the frontend.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import aiohttp

from api.tools.agent_tools import AGENT_TOOLS, execute_tool

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 10

# Providers that expose AsyncOpenAI-like client (SDK can use OpenAIChatCompletionsModel).
SDK_COMPATIBLE_PROVIDERS = ("openai", "azure", "dashscope")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_agent_loop(
    provider: str,
    model_client: Any,
    model_kwargs: Dict,
    initial_prompt: str,
    rag_instance: Any,
    repo_path: Optional[str],
    max_iterations: int = MAX_AGENT_ITERATIONS,
    system_instructions: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Drives the agentic tool-calling loop with streaming. Prefers the Agent SDK
    when available and provider is SDK-compatible; otherwise uses the for-loop backup.

    Yields dicts:
        {"type": "content", "delta": str}
        {"type": "tool_call_start", "id": str, "name": str, "arguments": str}
        {"type": "tool_call_result", "id": str, "name": str, "summary": str}
        {"type": "error", "message": str}
    """
    if provider in SDK_COMPATIBLE_PROVIDERS:
        try:
            async for msg in _run_agent_loop_sdk(
                model_client=model_client,
                model_kwargs=model_kwargs,
                initial_prompt=initial_prompt,
                system_instructions=system_instructions,
                rag_instance=rag_instance,
                repo_path=repo_path,
                max_iterations=max_iterations,
            ):
                yield msg
            return
        except Exception as e:
            logger.warning("Agent SDK run failed, falling back to for-loop: %s", e)

    async for msg in run_agent_loop_for_loop_backup(
        provider=provider,
        model_client=model_client,
        model_kwargs=model_kwargs,
        initial_prompt=initial_prompt,
        rag_instance=rag_instance,
        repo_path=repo_path,
        max_iterations=max_iterations,
        system_instructions=system_instructions,
    ):
        yield msg


async def _run_agent_loop_sdk(
    model_client: Any,
    model_kwargs: Dict,
    initial_prompt: str,
    system_instructions: Optional[str],
    rag_instance: Any,
    repo_path: Optional[str],
    max_iterations: int,
) -> AsyncGenerator[Dict, None]:
    """Use openai-agents Runner.run_streamed; map stream events to our yield format."""
    try:
        from agents import (
            Agent,
            ModelSettings,
            OpenAIChatCompletionsModel,
            RunConfig,
            Runner,
            function_tool,
        )
    except ImportError:
        raise RuntimeError("openai-agents not installed")

    try:
        from agents import set_tracing_disabled
        set_tracing_disabled(True)
    except Exception:
        pass

    if model_client.async_client is None:
        model_client.async_client = model_client.init_async_client()

    model_name = model_kwargs.get("model")
    instructions = system_instructions if system_instructions else initial_prompt
    user_input = initial_prompt

    @function_tool
    def rag_search(query: str, top_k: int = 5) -> str:
        """Search the repository codebase using semantic similarity. Use when you need more context about concepts, classes, functions, or features."""
        return execute_tool(
            "rag_search",
            json.dumps({"query": query, "top_k": top_k}),
            rag_instance,
            repo_path,
        )

    @function_tool
    def grep_search(
        pattern: str,
        file_glob: str = "*",
        max_results: int = 20,
    ) -> str:
        """Search for exact text patterns in the repository using regex. Use when you need specific strings, function/class/variable names, imports, or config values."""
        return execute_tool(
            "grep_search",
            json.dumps({"pattern": pattern, "file_glob": file_glob, "max_results": max_results}),
            rag_instance,
            repo_path,
        )

    sdk_model = OpenAIChatCompletionsModel(
        openai_client=model_client.async_client,
        model=model_name,
    )
    model_settings_kw: Dict[str, Any] = {"temperature": model_kwargs.get("temperature", 0.7)}
    if "top_p" in model_kwargs:
        model_settings_kw["top_p"] = model_kwargs["top_p"]
    model_settings = ModelSettings(**model_settings_kw)

    agent = Agent(
        name="CodeAnalyst",
        instructions=instructions,
        tools=[rag_search, grep_search],
        model=sdk_model,
    )
    run_config = RunConfig(model_settings=model_settings)

    result = Runner.run_streamed(
        agent,
        input=user_input,
        run_config=run_config,
        max_turns=max_iterations,
    )

    try:
        from openai.types.responses import ResponseTextDeltaEvent
    except ImportError:
        ResponseTextDeltaEvent = None

    async for event in result.stream_events():
        if event.type == "raw_response_event" and ResponseTextDeltaEvent is not None:
            if isinstance(event.data, ResponseTextDeltaEvent) and getattr(event.data, "delta", None):

                logger.info(f"Agent loop iteration content: {event.data}")

                yield {"type": "content", "delta": event.data.delta}
        elif event.type == "run_item_stream_event" and hasattr(event, "item"):
            item = event.item
            itype = getattr(item, "type", None)
            if itype == "tool_call_item":
                tool_call_start = {
                    "type": "tool_call_start",
                    "id": getattr(item, "call_id", "") or getattr(item, "id", ""),
                    "name": getattr(item, "name", ""),
                    "arguments": getattr(item, "arguments", "") or json.dumps(getattr(item, "input", {})),
                };
                logger.info(f"Agent loop iteration tool_call_start: {tool_call_start}")
            elif itype == "tool_call_output_item":
                out = getattr(item, "output", "") or getattr(item, "result", "")
                if len(out) > 8000:
                    out = out[:8000] + "\n\n... (truncated)"
                summary = out[:200] + "..." if len(out) > 200 else out
                tool_call_result = {
                    "type": "tool_call_result",
                    "id": getattr(item, "call_id", "") or getattr(item, "id", ""),
                    "name": getattr(item, "name", ""),
                    "summary": summary,
                }
                logger.info(f"Agent loop iteration tool_call_result: {tool_call_result}")



async def run_agent_loop_for_loop_backup(
    provider: str,
    model_client: Any,
    model_kwargs: Dict,
    initial_prompt: str,
    rag_instance: Any,
    repo_path: Optional[str],
    max_iterations: int = MAX_AGENT_ITERATIONS,
    system_instructions: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Hand-written agent loop (LLM -> tool_calls -> execute -> LLM). Used when SDK
    is unavailable or provider is not SDK-compatible. Yields same shapes as run_agent_loop.
    """
    if system_instructions:
        messages: List[Dict] = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": initial_prompt},
        ]
    else:
        messages = [{"role": "user", "content": initial_prompt}]

    for iteration in range(max_iterations):
        logger.info(f"Agent loop iteration {iteration + 1}/{max_iterations}")

        use_streaming = provider in ("openai", "azure", "dashscope")
        response_data = None

        if use_streaming:
            stream_gen = _openai_compatible_call_streaming(
                provider, model_client, model_kwargs, messages, tools=AGENT_TOOLS
            )
            async for delta, finished_data in stream_gen:
                if delta is not None:
                    yield {"type": "content", "delta": delta}
                if finished_data is not None:
                    response_data = finished_data
                    break
        else:
            response_data = await _call_with_tools(
                provider, model_client, model_kwargs, messages
            )
            if response_data:
                content = _extract_content(response_data)
                if content:
                    yield {"type": "content", "delta": content}

        if response_data is None:
            yield {"type": "error", "message": "Failed to get response from the model."}
            return

        tool_calls = _extract_tool_calls(response_data)
        content = _extract_content(response_data)

        if not tool_calls:
            logger.info(
                f"Agent loop done after {iteration + 1} iteration(s) — no tool calls"
            )
            if not use_streaming and content:
                yield {"type": "content", "delta": content}
            return

        # Model wants to use tools ------------------------------------------------
        logger.info(f"Model requested {len(tool_calls)} tool call(s)")
        # Content was already streamed when use_streaming

        messages.append(_format_assistant_message(response_data))

        for tc in tool_calls:
            tc_id = tc.get("id", "")
            tc_name = tc.get("function", {}).get("name", "")
            tc_args = tc.get("function", {}).get("arguments", "{}")

            tool_call_start = {
                "type": "tool_call_start",
                "id": tc_id,
                "name": tc_name,
                "arguments": tc_args,
            }
            logger.info(f"Agent loop iteration tool_call_start: {tool_call_start}")

            result = execute_tool(tc_name, tc_args, rag_instance, repo_path)

            if len(result) > 8000:
                result = result[:8000] + "\n\n... (truncated)"

            messages.append(
                {"role": "tool", "tool_call_id": tc_id, "content": result}
            )

            summary = result[:200] + "..." if len(result) > 200 else result
            yield {
                "type": "tool_call_result",
                "id": tc_id,
                "name": tc_name,
                "summary": summary,
            }

    # Exhausted iterations — final call without tools (streaming)
    logger.warning(
        f"Agent loop hit max iterations ({max_iterations}), final call without tools"
    )
    if provider in ("openai", "azure", "dashscope"):
        stream_gen = _openai_compatible_call_streaming(
            provider, model_client, model_kwargs, messages, tools=None
        )
        async for delta, _ in stream_gen:
            if delta:
                yield {"type": "content", "delta": delta}
    else:
        final_content = await _call_without_tools(
            provider, model_client, model_kwargs, messages
        )
        if final_content:
            yield {"type": "content", "delta": final_content}
        else:
            yield {
                "type": "content",
                "delta": "I was unable to complete the analysis within the allowed number of tool calls.",
            }


# ---------------------------------------------------------------------------
# Internal helpers — provider-agnostic wrappers
# ---------------------------------------------------------------------------

async def _call_with_tools(
    provider: str, model_client: Any, model_kwargs: Dict, messages: List[Dict]
) -> Optional[Dict]:
    try:
        if provider in ("openai", "azure", "dashscope"):
            return await _openai_compatible_call(
                provider, model_client, model_kwargs, messages, tools=AGENT_TOOLS
            )
        elif provider == "openrouter":
            return await _openrouter_call(
                model_client, model_kwargs, messages, tools=AGENT_TOOLS
            )
        else:
            logger.error(f"Provider {provider} does not support tool calling")
            return None
    except Exception as e:
        logger.error(f"Error in _call_with_tools: {e}")
        return None


async def _call_without_tools(
    provider: str, model_client: Any, model_kwargs: Dict, messages: List[Dict]
) -> Optional[str]:
    try:
        if provider in ("openai", "azure", "dashscope"):
            resp = await _openai_compatible_call(
                provider, model_client, model_kwargs, messages, tools=None
            )
        elif provider == "openrouter":
            resp = await _openrouter_call(
                model_client, model_kwargs, messages, tools=None
            )
        else:
            return None
        return _extract_content(resp)
    except Exception as e:
        logger.error(f"Error in _call_without_tools: {e}")
        return None


# ---------------------------------------------------------------------------
# Provider-specific call implementations
# ---------------------------------------------------------------------------

async def _openai_compatible_call(
    provider: str,
    model_client: Any,
    model_kwargs: Dict,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
) -> Optional[Dict]:
    """Non-streaming call via the OpenAI SDK (works for OpenAI / Azure / Dashscope)."""
    if model_client.async_client is None:
        model_client.async_client = model_client.init_async_client()

    kwargs: Dict[str, Any] = {
        "model": model_kwargs.get("model"),
        "messages": messages,
        "temperature": model_kwargs.get("temperature", 0.7),
        "stream": False,
    }
    if "top_p" in model_kwargs:
        kwargs["top_p"] = model_kwargs["top_p"]
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    if provider == "dashscope":
        extra_body = kwargs.get("extra_body", {})
        extra_body["enable_thinking"] = False
        kwargs["extra_body"] = extra_body

    response = await model_client.async_client.chat.completions.create(**kwargs)
    return _completion_to_dict(response)


async def _openai_compatible_call_streaming(
    provider: str,
    model_client: Any,
    model_kwargs: Dict,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
) -> AsyncGenerator[Tuple[Optional[str], Optional[Dict]], None]:
    """
    Streaming call via OpenAI SDK. Yields (content_delta, None) for each text chunk,
    then (None, response_data) at the end with aggregated content and tool_calls.
    """
    if model_client.async_client is None:
        model_client.async_client = model_client.init_async_client()

    kwargs: Dict[str, Any] = {
        "model": model_kwargs.get("model"),
        "messages": messages,
        "temperature": model_kwargs.get("temperature", 0.7),
        "stream": True,
    }
    if "top_p" in model_kwargs:
        kwargs["top_p"] = model_kwargs["top_p"]
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    if provider == "dashscope":
        extra_body = kwargs.get("extra_body", {})
        extra_body["enable_thinking"] = False
        kwargs["extra_body"] = extra_body

    stream = await model_client.async_client.chat.completions.create(**kwargs)

    content_parts: List[str] = []
    tool_calls_by_index: Dict[int, Dict[str, Any]] = {}
    finish_reason: Optional[str] = None

    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue

        if getattr(delta, "content", None) and delta.content:
            content_parts.append(delta.content)
            yield (delta.content, None)

        if getattr(delta, "tool_calls", None) and delta.tool_calls:
            for tc in delta.tool_calls:
                idx = getattr(tc, "index", None)
                if idx is None:
                    continue
                if idx not in tool_calls_by_index:
                    tool_calls_by_index[idx] = {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                acc = tool_calls_by_index[idx]
                if getattr(tc, "id", None):
                    acc["id"] = tc.id
                if getattr(tc, "type", None):
                    acc["type"] = tc.type
                fn = getattr(tc, "function", None)
                if fn:
                    if getattr(fn, "name", None):
                        acc["function"]["name"] = fn.name
                    if getattr(fn, "arguments", None):
                        acc["function"]["arguments"] += fn.arguments

        finish_reason = chunk.choices[0].finish_reason

    # Build aggregated response_data for the caller
    message: Dict[str, Any] = {
        "role": "assistant",
        "content": "".join(content_parts) if content_parts else None,
    }
    if tool_calls_by_index:
        message["tool_calls"] = [
            tool_calls_by_index[i]
            for i in sorted(tool_calls_by_index.keys())
        ]
    response_data: Dict[str, Any] = {
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": message,
            }
        ]
    }
    yield (None, response_data)


async def _openrouter_call(
    model_client: Any,
    model_kwargs: Dict,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
) -> Optional[Dict]:
    """Direct HTTP call to the OpenRouter /chat/completions endpoint."""
    if not model_client.async_client:
        model_client.async_client = model_client.init_async_client()

    api_key = model_client.async_client.get("api_key")
    base_url = model_client.async_client.get(
        "base_url", "https://openrouter.ai/api/v1"
    )

    if not api_key:
        logger.error("OpenRouter API key not configured")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/AsyncFuncAI/deepwiki-open",
        "X-Title": "DeepWiki",
    }

    body: Dict[str, Any] = {
        "model": model_kwargs.get("model"),
        "messages": messages,
        "temperature": model_kwargs.get("temperature", 0.7),
        "stream": False,
    }
    if "top_p" in model_kwargs:
        body["top_p"] = model_kwargs["top_p"]
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"OpenRouter error ({resp.status}): {error_text}")
                return None
            return await resp.json()


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------

def _completion_to_dict(completion: Any) -> Dict:
    """Convert an OpenAI ChatCompletion object to a plain dict."""
    result: Dict[str, Any] = {"choices": []}
    for choice in completion.choices:
        choice_dict: Dict[str, Any] = {
            "index": choice.index,
            "finish_reason": choice.finish_reason,
            "message": {
                "role": choice.message.role,
                "content": choice.message.content,
            },
        }
        if choice.message.tool_calls:
            choice_dict["message"]["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
        result["choices"].append(choice_dict)
    return result


def _extract_tool_calls(response_data: Optional[Dict]) -> Optional[List[Dict]]:
    if not response_data or "choices" not in response_data:
        return None
    choices = response_data["choices"]
    if not choices:
        return None
    tool_calls = choices[0].get("message", {}).get("tool_calls")
    return tool_calls if tool_calls else None


def _extract_content(response_data: Optional[Dict]) -> Optional[str]:
    if not response_data or "choices" not in response_data:
        return None
    choices = response_data["choices"]
    if not choices:
        return None
    return choices[0].get("message", {}).get("content")


def _format_assistant_message(response_data: Dict) -> Dict:
    """Build the assistant message dict (including tool_calls) for the messages list."""
    message = response_data["choices"][0]["message"]
    result: Dict[str, Any] = {
        "role": "assistant",
        "content": message.get("content"),
    }
    if message.get("tool_calls"):
        result["tool_calls"] = message["tool_calls"]
    return result
