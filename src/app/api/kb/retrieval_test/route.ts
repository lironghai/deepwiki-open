import { NextRequest, NextResponse } from 'next/server';

const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function POST(req: NextRequest) {
  try {
    const requestBody = await req.json();

    if (!requestBody.repo_url || !requestBody.query) {
      return NextResponse.json({ error: 'repo_url and query are required' }, { status: 400 });
    }

    const response = await fetch(`${TARGET_SERVER_BASE_URL}/api/kb/retrieval_test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Error from backend: ${response.status} - ${errorBody}`);
      return NextResponse.json({ error: `Backend error: ${response.statusText}` }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: unknown) {
    console.error('Error in /api/kb/retrieval_test:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json({ status: 'error', error_message: message }, { status: 500 });
  }
}
