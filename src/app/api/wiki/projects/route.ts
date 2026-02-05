import { NextResponse } from 'next/server';

// This should match the expected structure from your Python backend
interface ApiProcessedProject {
  id: string;
  owner: string;
  repo: string;
  name: string;
  repo_type: string;
  submittedAt: number;
  language: string;
}
// Payload for deleting a project (all data including wiki cache, codemap, repo, database)
interface DeleteProjectPayload {
  owner: string;
  repo: string;
  repo_type: string;
  authorization_code?: string;
}

/** Type guard to validate DeleteProjectPayload at runtime */
function isDeleteProjectPayload(obj: unknown): obj is DeleteProjectPayload {
  return (
    obj != null &&
    typeof obj === 'object' &&
    'owner' in obj && typeof (obj as Record<string, unknown>).owner === 'string' && ((obj as Record<string, unknown>).owner as string).trim() !== '' &&
    'repo' in obj && typeof (obj as Record<string, unknown>).repo === 'string' && ((obj as Record<string, unknown>).repo as string).trim() !== '' &&
    'repo_type' in obj && typeof (obj as Record<string, unknown>).repo_type === 'string' && ((obj as Record<string, unknown>).repo_type as string).trim() !== ''
  );
}

// Ensure this matches your Python backend configuration
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_HOST || 'http://localhost:8001';
const PROJECTS_API_ENDPOINT = `${PYTHON_BACKEND_URL}/api/processed_projects`;
const PROJECT_DELETE_API_ENDPOINT = `${PYTHON_BACKEND_URL}/api/project`;

export async function GET() {
  try {
    const response = await fetch(PROJECTS_API_ENDPOINT, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Add any other headers your Python backend might require, e.g., API keys
      },
      cache: 'no-store', // Ensure fresh data is fetched every time
    });

    if (!response.ok) {
      // Try to parse error from backend, otherwise use status text
      let errorBody = { error: `Failed to fetch from Python backend: ${response.statusText}` };
      try {
        errorBody = await response.json();
      } catch {
        // If parsing JSON fails, errorBody will retain its default value
        // The error from backend is logged in the next line anyway
      }
      console.error(`Error from Python backend (${PROJECTS_API_ENDPOINT}): ${response.status} - ${JSON.stringify(errorBody)}`);
      return NextResponse.json(errorBody, { status: response.status });
    }

    const projects: ApiProcessedProject[] = await response.json();
    return NextResponse.json(projects);

  } catch (error: unknown) {
    console.error(`Network or other error when fetching from ${PROJECTS_API_ENDPOINT}:`, error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json(
      { error: `Failed to connect to the Python backend. ${message}` },
      { status: 503 } // Service Unavailable
    );
  }
}

export async function DELETE(request: Request) {
  try {
    const body: unknown = await request.json();
    if (!isDeleteProjectPayload(body)) {
      return NextResponse.json(
        { error: 'Invalid request body: owner, repo, and repo_type are required and must be non-empty strings.' },
        { status: 400 }
      );
    }
    const { owner, repo, repo_type, authorization_code } = body;

    // Call the full project deletion API which deletes:
    // - All wiki caches (all languages)
    // - Codemap cache
    // - Repos directory
    // - Database file
    const response = await fetch(PROJECT_DELETE_API_ENDPOINT, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner,
        repo,
        repo_type,
        authorization_code,
      }),
    });

    if (!response.ok) {
      let errorBody = { error: response.statusText };
      try {
        errorBody = await response.json();
      } catch {}
      console.error(`Error deleting project (${PROJECT_DELETE_API_ENDPOINT}): ${response.status} - ${JSON.stringify(errorBody)}`);
      return NextResponse.json(errorBody, { status: response.status });
    }

    const result = await response.json();
    return NextResponse.json({
      message: 'Project deleted successfully',
      deleted_items: result.deleted_items || []
    });
  } catch (error: unknown) {
    console.error('Error in DELETE /api/wiki/projects:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json({ error: `Failed to delete project: ${message}` }, { status: 500 });
  }
}