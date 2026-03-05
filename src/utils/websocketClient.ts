/**
 * WebSocket client for chat completions
 * This replaces the HTTP streaming endpoint with a WebSocket connection
 */

/**
 * 获取 WebSocket URL
 * 优先使用环境变量，否则动态从当前页面 URL 构建
 * 这样可以确保在生产环境中正确连接到后端
 */
export const getWebSocketUrl = (path: string = '/ws/chat') => {
  // 在服务端渲染时使用环境变量
  if (typeof window === 'undefined') {
    const baseUrl = process.env.WS_SERVER_BASE_URL || 'http://localhost:8001';
    const wsBaseUrl = baseUrl.replace(/^https/, 'wss').replace(/^http/, 'ws');
    return `${wsBaseUrl}${path}`;
  }
  
  // 在客户端使用当前页面的域名（假设前端和后端在同一域名下通过代理）
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  
  // 检查是否有环境变量配置的后端地址（需要 NEXT_PUBLIC_ 前缀才能在客户端访问）
  const envBaseUrl = process.env.NEXT_PUBLIC_WS_SERVER_URL;
  if (envBaseUrl) {
    const wsBaseUrl = envBaseUrl.replace(/^https/, 'wss').replace(/^http/, 'ws');
    return `${wsBaseUrl}${path}`;
  }
  
  // 默认使用当前域名
  return `${protocol}//${host}${path}`;
};

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletionRequest {
  repo_url: string;
  messages: ChatMessage[];
  filePath?: string;
  token?: string;
  type?: string;
  provider?: string;
  model?: string;
  language?: string;
  excluded_dirs?: string;
  excluded_files?: string;
}

export interface ToolCallInfo {
  id: string;
  name: string;
  arguments: string;
  status: 'calling' | 'done';
  summary?: string;
}

/**
 * Creates a WebSocket connection for chat completions.
 *
 * Supports both plain-text messages (backward compat) and structured JSON
 * messages from the Agentic RAG tool-calling loop:
 *   { type: "content",          delta: string }
 *   { type: "tool_call_start",  id, name, arguments }
 *   { type: "tool_call_result", id, name, summary }
 *   { type: "error",           message: string }
 */
export const createChatWebSocket = (
  request: ChatCompletionRequest,
  onMessage: (message: string) => void,
  onError: (error: Event) => void,
  onClose: () => void,
  onToolCall?: (data: ToolCallInfo) => void,
  onToolResult?: (data: ToolCallInfo) => void,
): WebSocket => {
  const wsUrl = getWebSocketUrl('/ws/chat');
  console.log('Connecting to WebSocket:', wsUrl);
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('WebSocket connection established');
    ws.send(JSON.stringify(request));
  };

  ws.onmessage = (event) => {
    const raw: string = event.data;
    try {
      const msg = JSON.parse(raw);
      if (msg && typeof msg === 'object' && msg.type) {
        switch (msg.type) {
          case 'content':
            onMessage(msg.delta ?? '');
            break;
          case 'tool_call_start':
            if (onToolCall) {
              onToolCall({
                id: msg.id,
                name: msg.name,
                arguments: msg.arguments,
                status: 'calling',
              });
            }
            break;
          case 'tool_call_result':
            if (onToolResult) {
              onToolResult({
                id: msg.id,
                name: msg.name,
                arguments: '',
                status: 'done',
                summary: msg.summary,
              });
            }
            break;
          case 'error':
            onMessage(`\nError: ${msg.message ?? 'Unknown error'}`);
            break;
          default:
            onMessage(raw);
        }
        return;
      }
    } catch {
      // Not JSON — fall through to plain-text handling
    }
    onMessage(raw);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError(error);
  };

  ws.onclose = () => {
    console.log('WebSocket connection closed');
    onClose();
  };

  return ws;
};

/**
 * Closes a WebSocket connection
 * @param ws The WebSocket connection to close
 */
export const closeWebSocket = (ws: WebSocket | null): void => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
};
