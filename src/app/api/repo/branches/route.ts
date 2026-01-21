import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

interface RepoBranchesRequest {
  repo_url: string;
  repo_type: string;
  token?: string;
}

interface RepoBranchesResponse {
  branches: string[];
  default_branch?: string;
}

/**
 * Fetch the list of branches for a repository.
 * This endpoint proxies the request to the backend API.
 */
export async function POST(req: NextRequest) {
  try {
    const requestBody: RepoBranchesRequest = await req.json();

    if (!requestBody.repo_url) {
      return NextResponse.json(
        { error: 'repo_url is required' },
        { status: 400 }
      );
    }

    const targetUrl = `${TARGET_SERVER_BASE_URL}/api/repo/branches`;

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
        { error: `Backend error: ${response.statusText}`, details: errorBody },
        { status: response.status }
      );
    }

    const data: RepoBranchesResponse = await response.json();
    return NextResponse.json(data);

  } catch (error: unknown) {
    console.error('Error in /api/repo/branches:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json(
      { 
        error: 'Failed to fetch branches',
        message
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

