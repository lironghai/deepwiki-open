import { NextRequest, NextResponse } from 'next/server';

// Backend server base URL
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

/**
 * POST handler for Codemap-enhanced chat
 * Proxies requests to the FastAPI backend
 */
export async function POST(req: NextRequest) {
  try {
    const requestBody = await req.json();

    console.log('Proxying Codemap chat request to backend...');

    const targetUrl = `${TARGET_SERVER_BASE_URL}/api/chat/with_codemap`;

    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // If the backend service returned an error, forward that error to the client
    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      console.error('Backend error:', backendResponse.status, errorBody);
      return new NextResponse(errorBody, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Parse the JSON response from backend
    const data = await backendResponse.json();

    // Return the response to the client
    return NextResponse.json(data, {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error in Codemap chat proxy route:', error);

    let errorMessage = 'Internal Server Error in proxy';
    let statusCode = 500;

    if (error instanceof Error) {
      errorMessage = error.message;

      // If it's a connection error, return 503 Service Unavailable
      if (errorMessage.includes('fetch failed') ||
          errorMessage.includes('ECONNREFUSED') ||
          errorMessage.includes('timeout')) {
        statusCode = 503;
        errorMessage = 'Backend service is unavailable. Please make sure the API server is running.';
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
