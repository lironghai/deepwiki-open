import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

interface RepoStatusRequest {
  repo_url: string;
  repo_type: string;
  token?: string;
}

interface RepoStatusResponse {
  status: 'ready' | 'processing' | 'not_found' | 'error';
  message: string;
  has_embeddings: boolean;
  document_count: number;
}

/**
 * Check repository embedding status
 * This allows the frontend to verify if a repository's embeddings are ready
 * before attempting to make chat requests.
 */
export async function POST(req: NextRequest) {
  try {
    const requestBody: RepoStatusRequest = await req.json();

    if (!requestBody.repo_url) {
      return NextResponse.json(
        { error: 'repo_url is required' },
        { status: 400 }
      );
    }

    const targetUrl = `${TARGET_SERVER_BASE_URL}/api/repo_status`;

    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Error from backend (${targetUrl}): ${response.status} - ${errorBody}`);
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data: RepoStatusResponse = await response.json();
    return NextResponse.json(data);

  } catch (error: unknown) {
    console.error('Error in /api/repo/status:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json(
      { 
        status: 'error',
        message: `Failed to check repository status: ${message}`,
        has_embeddings: false,
        document_count: 0
      },
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
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}



