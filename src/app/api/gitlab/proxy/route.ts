import { NextRequest, NextResponse } from 'next/server';

/**
 * GitLab API 代理路由
 * 解决前端直接调用外部 GitLab API 时的 CORS 跨域问题
 * 
 * 使用方式：
 * GET /api/gitlab/proxy?url=<encoded_gitlab_api_url>&token=<optional_private_token>
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const targetUrl = searchParams.get('url');
  const token = searchParams.get('token');

  if (!targetUrl) {
    return NextResponse.json(
      { error: 'Missing url parameter' },
      { status: 400 }
    );
  }

  // 验证目标 URL 是否为有效的 GitLab API 请求
  try {
    const parsedUrl = new URL(targetUrl);
    if (!parsedUrl.pathname.includes('/api/v4/')) {
      return NextResponse.json(
        { error: 'Invalid GitLab API URL' },
        { status: 400 }
      );
    }
  } catch {
    return NextResponse.json(
      { error: 'Invalid URL format' },
      { status: 400 }
    );
  }

  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['PRIVATE-TOKEN'] = token;
    }

    const response = await fetch(targetUrl, { headers });

    // 处理非 JSON 响应（如 README 等原始文件内容）
    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: errorText || response.statusText },
        { status: response.status }
      );
    }

    // 构建响应头，转发分页信息
    const responseHeaders = new Headers();
    const xNextPage = response.headers.get('x-next-page');
    const xTotalPages = response.headers.get('x-total-pages');
    const xTotal = response.headers.get('x-total');

    if (xNextPage) {
      responseHeaders.set('x-next-page', xNextPage);
    }
    if (xTotalPages) {
      responseHeaders.set('x-total-pages', xTotalPages);
    }
    if (xTotal) {
      responseHeaders.set('x-total', xTotal);
    }

    if (isJson) {
      const data = await response.json();
      return NextResponse.json(data, { headers: responseHeaders });
    } else {
      // 对于非 JSON 响应（如 README 原始内容），返回文本
      const text = await response.text();
      return new NextResponse(text, {
        status: 200,
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          ...Object.fromEntries(responseHeaders.entries()),
        },
      });
    }
  } catch (error) {
    console.error('GitLab proxy error:', error);
    return NextResponse.json(
      { error: `Proxy error: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    );
  }
}


