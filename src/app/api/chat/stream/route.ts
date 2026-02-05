import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL, derived from environment variable or defaulted.
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

// 配置参数
const MAX_RETRIES = 3;           // 最大重试次数
const RETRY_DELAY_MS = 2000;     // 重试间隔（毫秒）
const REQUEST_TIMEOUT_MS = 30000; // 请求超时时间（毫秒）

/**
 * 带超时的 fetch 请求
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * 带重试的 fetch 请求
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries: number = MAX_RETRIES,
  retryDelayMs: number = RETRY_DELAY_MS,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`Attempt ${attempt}/${maxRetries} to connect to backend...`);
      const response = await fetchWithTimeout(url, options, timeoutMs);
      console.log(`Successfully connected to backend on attempt ${attempt}`);
      return response;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      // 检查是否是超时或连接错误
      const isRetryable = 
        lastError.name === 'AbortError' || 
        lastError.message.includes('fetch failed') ||
        lastError.message.includes('ECONNREFUSED') ||
        lastError.message.includes('timeout') ||
        (lastError.cause && typeof lastError.cause === 'object' && 
         'code' in lastError.cause && 
         (lastError.cause.code === 'UND_ERR_HEADERS_TIMEOUT' || 
          lastError.cause.code === 'ECONNREFUSED'));

      if (!isRetryable || attempt === maxRetries) {
        console.error(`Failed after ${attempt} attempts:`, lastError.message);
        throw lastError;
      }

      console.log(`Attempt ${attempt} failed, retrying in ${retryDelayMs}ms...`);
      await new Promise(resolve => setTimeout(resolve, retryDelayMs));
    }
  }

  throw lastError || new Error('Unknown error during fetch');
}

// This is a fallback HTTP implementation that will be used if WebSockets are not available
// or if there's an error with the WebSocket connection
export async function POST(req: NextRequest) {
  try {
    const requestBody = await req.json();

    console.log('Using HTTP fallback for chat completion instead of WebSockets');

    const targetUrl = `${TARGET_SERVER_BASE_URL}/chat/completions/stream`;

    // 使用带重试的 fetch
    // const backendResponse = await fetchWithRetry(
    //   targetUrl,
    //   {
    //     method: 'POST',
    //     headers: {
    //       'Content-Type': 'application/json',
    //       'Accept': 'text/event-stream',
    //     },
    //     body: JSON.stringify(requestBody),
    //   }
    // );

    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream', // Indicate that we expect a stream
      },
      body: JSON.stringify(requestBody),
    });

    // If the backend service returned an error, forward that error to the client
    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      const errorHeaders = new Headers();
      backendResponse.headers.forEach((value, key) => {
        errorHeaders.set(key, value);
      });
      return new NextResponse(errorBody, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        headers: errorHeaders,
      });
    }

    // Ensure the backend response has a body to stream
    if (!backendResponse.body) {
      return new NextResponse('Stream body from backend is null', { status: 500 });
    }

    // Create a new ReadableStream to pipe the data from the backend to the client
    const stream = new ReadableStream({
      async start(controller) {
        const reader = backendResponse.body!.getReader();
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }
            controller.enqueue(value);
          }
        } catch (error) {
          console.error('Error reading from backend stream in proxy:', error);
          controller.error(error);
        } finally {
          controller.close();
          reader.releaseLock();
        }
      },
      cancel(reason) {
        console.log('Client cancelled stream request:', reason);
      }
    });

    // Set up headers for the response to the client
    const responseHeaders = new Headers();
    const contentType = backendResponse.headers.get('Content-Type');
    if (contentType) {
      responseHeaders.set('Content-Type', contentType);
    }
    responseHeaders.set('Cache-Control', 'no-cache, no-transform');

    return new NextResponse(stream, {
      status: backendResponse.status,
      headers: responseHeaders,
    });

  } catch (error) {
    console.error('Error in API proxy route (/api/chat/stream):', error);
    
    let errorMessage = 'Internal Server Error in proxy';
    let statusCode = 500;
    
    if (error instanceof Error) {
      errorMessage = error.message;
      
      // 如果是超时错误，返回 503 Service Unavailable
      if (error.name === 'AbortError' || 
          errorMessage.includes('timeout') ||
          errorMessage.includes('fetch failed')) {
        statusCode = 503;
        errorMessage = 'Backend service is busy or unavailable. Please try again later.';
      }
    }
    
    return new NextResponse(JSON.stringify({ 
      error: errorMessage,
      retryable: statusCode === 503 
    }), {
      status: statusCode,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// Handle OPTIONS requests for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
