import { NextRequest, NextResponse } from 'next/server';

// Backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

interface WikiPageUpdateRequest {
  owner: string;
  repo: string;
  repo_type: string;
  language: string;
  page_id: string;
  title?: string;
  content?: string;
}

/**
 * Update a single wiki page
 * Proxies PATCH request to the FastAPI backend
 */
export async function PATCH(req: NextRequest) {
  try {
    const requestBody: WikiPageUpdateRequest = await req.json();

    // Validate required fields
    if (!requestBody.owner || !requestBody.repo || !requestBody.repo_type || 
        !requestBody.language || !requestBody.page_id) {
      return NextResponse.json(
        { error: 'owner, repo, repo_type, language, and page_id are required' },
        { status: 400 }
      );
    }

    // Validate that at least one field is being updated
    if (requestBody.title === undefined && requestBody.content === undefined) {
      return NextResponse.json(
        { error: 'At least one of title or content must be provided' },
        { status: 400 }
      );
    }

    const targetUrl = `${TARGET_SERVER_BASE_URL}/api/wiki_cache/page`;

    const response = await fetch(targetUrl, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Error from backend (${targetUrl}): ${response.status} - ${errorBody}`);
      
      let errorData;
      try {
        errorData = JSON.parse(errorBody);
      } catch {
        errorData = { error: response.statusText };
      }
      
      return NextResponse.json(
        errorData,
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: unknown) {
    console.error('Error in /api/wiki/page:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json(
      { error: `Failed to update wiki page: ${message}` },
      { status: 500 }
    );
  }
}

// Handle OPTIONS requests for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
