import { NextRequest, NextResponse } from 'next/server';

/**
 * GitLab API 代理路由
 * 解决前端直接调用外部 GitLab API 时的 CORS 跨域问题
 * 
 * 使用方式：
 * GET /api/gitlab/proxy?url=<gitlab_api_url>&token=<optional_private_token>
 * 
 * 注意：url参数会被URLSearchParams自动编码，所以前端传递未编码的URL
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  let targetUrl = searchParams.get('url');
  const token = searchParams.get('token');
  console.error('GitLab url param:', targetUrl);
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
      // 'Content-Type': 'application/json',
      // 'User-Agent': 'DeepWiki-Open/1.0',
      // 'Accept': 'application/json',
    };

    if (token) {
      headers['PRIVATE-TOKEN'] = token;
      console.error('GitLab token provided:', token.substring(0, 10) + '...');
    } else {
      console.error('GitLab token NOT provided');
    }

    console.error('GitLab fetch URL:', targetUrl);
    console.error('GitLab fetch headers:', JSON.stringify(Object.keys(headers)));


    if (targetUrl.startsWith('http://git.ljdong.net/api/v4/projects')) {
      targetUrl = targetUrl.replace('http:', 'https:')
      console.error('GitLab new url :', targetUrl);
    }
    
    const response = await fetch(targetUrl, { 
      headers,
      // 添加重定向跟随
      redirect: 'follow',
    });
    
    console.error('GitLab fetch response status:', response.status);
    console.error('GitLab fetch response URL:', response.url);
    
    // 处理非 JSON 响应（如 README 等原始文件内容）
    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');
    
    // 如果是404，尝试获取详细错误信息
    if (!response.ok) {
      const errorText = await response.text();
      console.error('GitLab API error response:', errorText);
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

// 定义一个主函数
async function main() {
  try {
    let targetUrl = "http://git.ljdong.net/api/v4/projects/hero%2Fserver%2Ftest-feishu"
    targetUrl = "http://127.0.0.1:29003/api/gitlab/proxy?url=http%3A%2F%2Fgit.ljdong.net%2Fapi%2Fv4%2Fprojects%2Fhero%252Fserver%252Ftest-feishu&token=k5GAhUhvRceXMoWGc1Xh"
    const token = "k5GAhUhvRceXMoWGc1Xh"
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'User-Agent': 'DeepWiki-Open/1.0',
      'Accept': 'application/json',
    };

    headers['PRIVATE-TOKEN'] = token;

    // const response = await fetch(targetUrl, {
    //   headers,
    //   // 添加重定向跟随
    //   redirect: 'follow',
    // });

    const response = await GET(new NextRequest(targetUrl, {
      headers,
      // 添加重定向跟随
      redirect: 'follow',
    }))

    console.error('GitLab fetch response status:', response.status);
    console.error('GitLab fetch response URL:', response.url);
  } catch (error) {
    console.error('测试失败:', error);
    process.exit(1); // 非零退出码表示失败
  }
}

// 只有在直接执行此文件时才运行 main
if (require.main === module) {
  main();
}

// 导出 main 函数以便其他文件可以调用
export { main };

