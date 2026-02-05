import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

interface RepoPrepareRequest {
  repo_url: string;
  repo_type: string;
  token?: string;
  excluded_dirs?: string;
  excluded_files?: string;
  included_dirs?: string;
  included_files?: string;
}

interface RepoPrepareResponse {
  status: 'accepted' | 'processing' | 'ready' | 'error';
  message: string;
}

/**
 * Trigger repository preparation (clone + embedding) in the background.
 * This endpoint returns immediately with status 'accepted' and starts
 * background processing on the server. Use /api/repo/status to check progress.
 */
export async function POST(req: NextRequest) {
  try {
    const requestBody: RepoPrepareRequest = await req.json();

    if (!requestBody.repo_url) {
      return NextResponse.json(
        { error: 'repo_url is required' },
        { status: 400 }
      );
    }

    const targetUrl = `${TARGET_SERVER_BASE_URL}/api/repo/prepare`;

    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // Handle 202 Accepted response (background task started)
    if (response.status === 202) {
      const data = await response.json();
      return NextResponse.json(data, { status: 202 });
    }

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Error from backend (${targetUrl}): ${response.status} - ${errorBody}`);
      return NextResponse.json(
        { status: 'error', message: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data: RepoPrepareResponse = await response.json();
    return NextResponse.json(data);

  } catch (error: unknown) {
    console.error('Error in /api/repo/prepare:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json(
      { 
        status: 'error',
        message: `Failed to prepare repository: ${message}`
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






