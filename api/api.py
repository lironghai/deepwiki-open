import os
import logging
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import List, Optional, Dict, Any, Literal
import json
from datetime import datetime
from pydantic import BaseModel, Field
import google.generativeai as genai
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging
from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# --- Background Task Management ---
# Thread pool for background repository preparation tasks
repo_prepare_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="repo_prepare")
# Track repository preparation status: repo_url -> {"status": "processing|ready|error", "message": str, "started_at": datetime}
preparing_repos: Dict[str, Dict[str, Any]] = {}
preparing_repos_lock = threading.Lock()

# Initialize FastAPI app
app = FastAPI(
    title="Streaming API",
    description="API for streaming chat completions"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Helper function to get adalflow root path
def get_adalflow_default_root_path():
    return os.path.expanduser(os.path.join("~", ".adalflow"))

# --- Pydantic Models ---
class WikiPage(BaseModel):
    """
    Model for a wiki page.
    """
    id: str
    title: str
    content: str
    filePaths: List[str]
    importance: str # Should ideally be Literal['high', 'medium', 'low']
    relatedPages: List[str]

class ProcessedProjectEntry(BaseModel):
    id: str  # Filename
    owner: str
    repo: str
    name: str  # owner/repo
    repo_type: str # Renamed from type to repo_type for clarity with existing models
    submittedAt: int # Timestamp
    language: str # Extracted from filename

class RepoInfo(BaseModel):
    owner: str
    repo: str
    type: str
    token: Optional[str] = None
    localPath: Optional[str] = None
    repoUrl: Optional[str] = None


class WikiSection(BaseModel):
    """
    Model for the wiki sections.
    """
    id: str
    title: str
    pages: List[str]
    subsections: Optional[List[str]] = None


class WikiStructureModel(BaseModel):
    """
    Model for the overall wiki structure.
    """
    id: str
    title: str
    description: str
    pages: List[WikiPage]
    sections: Optional[List[WikiSection]] = None
    rootSections: Optional[List[str]] = None

class WikiCacheData(BaseModel):
    """
    Model for the data to be stored in the wiki cache.
    """
    wiki_structure: WikiStructureModel
    generated_pages: Dict[str, WikiPage]
    repo_url: Optional[str] = None  #compatible for old cache
    repo: Optional[RepoInfo] = None
    provider: Optional[str] = None
    model: Optional[str] = None

class WikiCacheRequest(BaseModel):
    """
    Model for the request body when saving wiki cache.
    """
    repo: RepoInfo
    language: str
    wiki_structure: WikiStructureModel
    generated_pages: Dict[str, WikiPage]
    provider: str
    model: str

class WikiExportRequest(BaseModel):
    """
    Model for requesting a wiki export.
    """
    repo_url: str = Field(..., description="URL of the repository")
    pages: List[WikiPage] = Field(..., description="List of wiki pages to export")
    format: Literal["markdown", "json"] = Field(..., description="Export format (markdown or json)")

# --- Model Configuration Models ---
class Model(BaseModel):
    """
    Model for LLM model configuration
    """
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Display name for the model")

class Provider(BaseModel):
    """
    Model for LLM provider configuration
    """
    id: str = Field(..., description="Provider identifier")
    name: str = Field(..., description="Display name for the provider")
    models: List[Model] = Field(..., description="List of available models for this provider")
    supportsCustomModel: Optional[bool] = Field(False, description="Whether this provider supports custom models")

class ModelConfig(BaseModel):
    """
    Model for the entire model configuration
    """
    providers: List[Provider] = Field(..., description="List of available model providers")
    defaultProvider: str = Field(..., description="ID of the default provider")

class AuthorizationConfig(BaseModel):
    code: str = Field(..., description="Authorization code")

from api.config import configs, WIKI_AUTH_MODE, WIKI_AUTH_CODE

@app.get("/lang/config")
async def get_lang_config():
    return configs["lang_config"]

@app.get("/auth/status")
async def get_auth_status():
    """
    Check if authentication is required for the wiki.
    """
    return {"auth_required": WIKI_AUTH_MODE}

@app.post("/auth/validate")
async def validate_auth_code(request: AuthorizationConfig):
    """
    Check authorization code.
    """
    return {"success": WIKI_AUTH_CODE == request.code}

@app.get("/models/config", response_model=ModelConfig)
async def get_model_config():
    """
    Get available model providers and their models.

    This endpoint returns the configuration of available model providers and their
    respective models that can be used throughout the application.

    Returns:
        ModelConfig: A configuration object containing providers and their models
    """
    try:
        logger.info("Fetching model configurations")

        # Create providers from the config file
        providers = []
        default_provider = configs.get("default_provider", "google")

        # Add provider configuration based on config.py
        for provider_id, provider_config in configs["providers"].items():
            models = []
            # Add models from config
            for model_id in provider_config["models"].keys():
                # Get a more user-friendly display name if possible
                models.append(Model(id=model_id, name=model_id))

            # Add provider with its models
            providers.append(
                Provider(
                    id=provider_id,
                    name=f"{provider_id.capitalize()}",
                    supportsCustomModel=provider_config.get("supportsCustomModel", False),
                    models=models
                )
            )

        # Create and return the full configuration
        config = ModelConfig(
            providers=providers,
            defaultProvider=default_provider
        )
        return config

    except Exception as e:
        logger.error(f"Error creating model configuration: {str(e)}")
        # Return some default configuration in case of error
        return ModelConfig(
            providers=[
                Provider(
                    id="google",
                    name="Google",
                    supportsCustomModel=True,
                    models=[
                        Model(id="gemini-2.5-flash", name="Gemini 2.5 Flash")
                    ]
                )
            ],
            defaultProvider="google"
        )

@app.post("/export/wiki")
async def export_wiki(request: WikiExportRequest):
    """
    Export wiki content as Markdown or JSON.

    Args:
        request: The export request containing wiki pages and format

    Returns:
        A downloadable file in the requested format
    """
    try:
        logger.info(f"Exporting wiki for {request.repo_url} in {request.format} format")

        # Extract repository name from URL for the filename
        repo_parts = request.repo_url.rstrip('/').split('/')
        repo_name = repo_parts[-1] if len(repo_parts) > 0 else "wiki"

        # Get current timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if request.format == "markdown":
            # Generate Markdown content
            content = generate_markdown_export(request.repo_url, request.pages)
            filename = f"{repo_name}_wiki_{timestamp}.md"
            media_type = "text/markdown"
        else:  # JSON format
            # Generate JSON content
            content = generate_json_export(request.repo_url, request.pages)
            filename = f"{repo_name}_wiki_{timestamp}.json"
            media_type = "application/json"

        # Create response with appropriate headers for file download
        response = Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

        return response

    except Exception as e:
        error_msg = f"Error exporting wiki: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/local_repo/structure")
async def get_local_repo_structure(path: str = Query(None, description="Path to local repository")):
    """Return the file tree and README content for a local repository."""
    if not path:
        return JSONResponse(
            status_code=400,
            content={"error": "No path provided. Please provide a 'path' query parameter."}
        )

    if not os.path.isdir(path):
        return JSONResponse(
            status_code=404,
            content={"error": f"Directory not found: {path}"}
        )

    try:
        logger.info(f"Processing local repository at: {path}")
        file_tree_lines = []
        readme_content = ""

        for root, dirs, files in os.walk(path):
            # Exclude hidden dirs/files and virtual envs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'node_modules' and d != '.venv']
            for file in files:
                if file.startswith('.') or file == '__init__.py' or file == '.DS_Store':
                    continue
                rel_dir = os.path.relpath(root, path)
                rel_file = os.path.join(rel_dir, file) if rel_dir != '.' else file
                file_tree_lines.append(rel_file)
                # Find README.md (case-insensitive)
                if file.lower() == 'readme.md' and not readme_content:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            readme_content = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read README.md: {str(e)}")
                        readme_content = ""

        file_tree_str = '\n'.join(sorted(file_tree_lines))
        return {"file_tree": file_tree_str, "readme": readme_content}
    except Exception as e:
        logger.error(f"Error processing local repository: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing local repository: {str(e)}"}
        )

def generate_markdown_export(repo_url: str, pages: List[WikiPage]) -> str:
    """
    Generate Markdown export of wiki pages.

    Args:
        repo_url: The repository URL
        pages: List of wiki pages

    Returns:
        Markdown content as string
    """
    # Start with metadata
    markdown = f"# Wiki Documentation for {repo_url}\n\n"
    markdown += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # Add table of contents
    markdown += "## Table of Contents\n\n"
    for page in pages:
        markdown += f"- [{page.title}](#{page.id})\n"
    markdown += "\n"

    # Add each page
    for page in pages:
        markdown += f"<a id='{page.id}'></a>\n\n"
        markdown += f"## {page.title}\n\n"



        # Add related pages
        if page.relatedPages and len(page.relatedPages) > 0:
            markdown += "### Related Pages\n\n"
            related_titles = []
            for related_id in page.relatedPages:
                # Find the title of the related page
                related_page = next((p for p in pages if p.id == related_id), None)
                if related_page:
                    related_titles.append(f"[{related_page.title}](#{related_id})")

            if related_titles:
                markdown += "Related topics: " + ", ".join(related_titles) + "\n\n"

        # Add page content
        markdown += f"{page.content}\n\n"
        markdown += "---\n\n"

    return markdown

def generate_json_export(repo_url: str, pages: List[WikiPage]) -> str:
    """
    Generate JSON export of wiki pages.

    Args:
        repo_url: The repository URL
        pages: List of wiki pages

    Returns:
        JSON content as string
    """
    # Create a dictionary with metadata and pages
    export_data = {
        "metadata": {
            "repository": repo_url,
            "generated_at": datetime.now().isoformat(),
            "page_count": len(pages)
        },
        "pages": [page.model_dump() for page in pages]
    }

    # Convert to JSON string with pretty formatting
    return json.dumps(export_data, indent=2)

# Import the simplified chat implementation
from api.simple_chat import chat_completions_stream
from api.websocket_wiki import handle_websocket_chat

# Add the chat_completions_stream endpoint to the main app
app.add_api_route("/chat/completions/stream", chat_completions_stream, methods=["POST"])

# Add the WebSocket endpoint
app.add_websocket_route("/ws/chat", handle_websocket_chat)

# Import and add MCP routes
from api.mcp_server import get_mcp_app
app.include_router(get_mcp_app())

# --- Wiki Cache Helper Functions ---

WIKI_CACHE_DIR = os.path.join(get_adalflow_default_root_path(), "wikicache")
os.makedirs(WIKI_CACHE_DIR, exist_ok=True)

def get_wiki_cache_path(owner: str, repo: str, repo_type: str, language: str) -> str:
    """Generates the file path for a given wiki cache."""
    filename = f"deepwiki_cache_{repo_type}_{owner}_{repo}_{language}.json"
    return os.path.join(WIKI_CACHE_DIR, filename)

async def read_wiki_cache(owner: str, repo: str, repo_type: str, language: str) -> Optional[WikiCacheData]:
    """Reads wiki cache data from the file system."""
    cache_path = get_wiki_cache_path(owner, repo, repo_type, language)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return WikiCacheData(**data)
        except Exception as e:
            logger.error(f"Error reading wiki cache from {cache_path}: {e}")
            return None
    return None

async def save_wiki_cache(data: WikiCacheRequest) -> bool:
    """Saves wiki cache data to the file system."""
    cache_path = get_wiki_cache_path(data.repo.owner, data.repo.repo, data.repo.type, data.language)
    logger.info(f"Attempting to save wiki cache. Path: {cache_path}")
    try:
        payload = WikiCacheData(
            wiki_structure=data.wiki_structure,
            generated_pages=data.generated_pages,
            repo=data.repo,
            provider=data.provider,
            model=data.model
        )
        # Log size of data to be cached for debugging (avoid logging full content if large)
        try:
            payload_json = payload.model_dump_json()
            payload_size = len(payload_json.encode('utf-8'))
            logger.info(f"Payload prepared for caching. Size: {payload_size} bytes.")
        except Exception as ser_e:
            logger.warning(f"Could not serialize payload for size logging: {ser_e}")


        logger.info(f"Writing cache file to: {cache_path}")
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(payload.model_dump(), f, indent=2)
        logger.info(f"Wiki cache successfully saved to {cache_path}")
        return True
    except IOError as e:
        logger.error(f"IOError saving wiki cache to {cache_path}: {e.strerror} (errno: {e.errno})", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving wiki cache to {cache_path}: {e}", exc_info=True)
        return False

# --- Wiki Cache API Endpoints ---

@app.get("/api/wiki_cache", response_model=Optional[WikiCacheData])
async def get_cached_wiki(
    owner: str = Query(..., description="Repository owner"),
    repo: str = Query(..., description="Repository name"),
    repo_type: str = Query(..., description="Repository type (e.g., github, gitlab)"),
    language: str = Query(..., description="Language of the wiki content")
):
    """
    Retrieves cached wiki data (structure and generated pages) for a repository.
    """
    # Language validation
    supported_langs = configs["lang_config"]["supported_languages"]
    if not supported_langs.__contains__(language):
        language = configs["lang_config"]["default"]

    logger.info(f"Attempting to retrieve wiki cache for {owner}/{repo} ({repo_type}), lang: {language}")
    cached_data = await read_wiki_cache(owner, repo, repo_type, language)
    if cached_data:
        return cached_data
    else:
        # Return 200 with null body if not found, as frontend expects this behavior
        # Or, raise HTTPException(status_code=404, detail="Wiki cache not found") if preferred
        logger.info(f"Wiki cache not found for {owner}/{repo} ({repo_type}), lang: {language}")
        return None

@app.post("/api/wiki_cache")
async def store_wiki_cache(request_data: WikiCacheRequest):
    """
    Stores generated wiki data (structure and pages) to the server-side cache.
    """
    # Language validation
    supported_langs = configs["lang_config"]["supported_languages"]

    if not supported_langs.__contains__(request_data.language):
        request_data.language = configs["lang_config"]["default"]

    logger.info(f"Attempting to save wiki cache for {request_data.repo.owner}/{request_data.repo.repo} ({request_data.repo.type}), lang: {request_data.language}")
    success = await save_wiki_cache(request_data)
    if success:
        return {"message": "Wiki cache saved successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save wiki cache")

@app.delete("/api/wiki_cache")
async def delete_wiki_cache(
    owner: str = Query(..., description="Repository owner"),
    repo: str = Query(..., description="Repository name"),
    repo_type: str = Query(..., description="Repository type (e.g., github, gitlab)"),
    language: str = Query(..., description="Language of the wiki content"),
    authorization_code: Optional[str] = Query(None, description="Authorization code")
):
    """
    Deletes a specific wiki cache from the file system.
    """
    # Language validation
    supported_langs = configs["lang_config"]["supported_languages"]
    if not supported_langs.__contains__(language):
        raise HTTPException(status_code=400, detail="Language is not supported")

    if WIKI_AUTH_MODE:
        logger.info("check the authorization code")
        if not authorization_code or WIKI_AUTH_CODE != authorization_code:
            raise HTTPException(status_code=401, detail="Authorization code is invalid")

    logger.info(f"Attempting to delete wiki cache for {owner}/{repo} ({repo_type}), lang: {language}")
    cache_path = get_wiki_cache_path(owner, repo, repo_type, language)

    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            logger.info(f"Successfully deleted wiki cache: {cache_path}")
            return {"message": f"Wiki cache for {owner}/{repo} ({language}) deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting wiki cache {cache_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete wiki cache: {str(e)}")
    else:
        logger.warning(f"Wiki cache not found, cannot delete: {cache_path}")
        raise HTTPException(status_code=404, detail="Wiki cache not found")

# --- Repository Status Check Endpoint ---
class RepoStatusRequest(BaseModel):
    """Model for repository status check request."""
    repo_url: str = Field(..., description="URL or path of the repository")
    repo_type: str = Field("github", description="Type of repository (github, gitlab, bitbucket, local)")
    token: Optional[str] = Field(None, description="Access token for private repositories")

class RepoStatusResponse(BaseModel):
    """Model for repository status response."""
    status: str = Field(..., description="Status of the repository: 'ready', 'processing', 'not_found', 'error'")
    message: str = Field(..., description="Human-readable status message")
    has_embeddings: bool = Field(False, description="Whether the repository has embedding data")
    document_count: int = Field(0, description="Number of documents if ready")
    file_paths: List[str] = Field(default_factory=list, description="List of file paths actually processed by the server")

# --- Repository Prepare Endpoint (Async Background Processing) ---
class RepoPrepareRequest(BaseModel):
    """Model for repository prepare request."""
    repo_url: str = Field(..., description="URL or path of the repository")
    repo_type: str = Field("github", description="Type of repository (github, gitlab, bitbucket, local)")
    token: Optional[str] = Field(None, description="Access token for private repositories")
    excluded_dirs: Optional[str] = Field(None, description="Comma or newline separated directories to exclude")
    excluded_files: Optional[str] = Field(None, description="Comma or newline separated files to exclude")
    included_dirs: Optional[str] = Field(None, description="Comma or newline separated directories to include exclusively")
    included_files: Optional[str] = Field(None, description="Comma or newline separated files to include exclusively")

class RepoPrepareResponse(BaseModel):
    """Model for repository prepare response."""
    status: str = Field(..., description="Status: 'accepted', 'processing', 'ready', 'error'")
    message: str = Field(..., description="Human-readable message")

def _extract_repo_name(repo_url: str, repo_type: str) -> str:
    """Extract repository name from URL for storage purposes."""
    url_parts = repo_url.rstrip('/').split('/')
    if repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
        owner = url_parts[-2]
        repo = url_parts[-1].replace(".git", "")
        return f"{owner}_{repo}"
    else:
        return url_parts[-1].replace(".git", "")

def _background_prepare_repo(repo_url: str, repo_type: str, token: Optional[str],
                             excluded_dirs: Optional[str], excluded_files: Optional[str],
                             included_dirs: Optional[str], included_files: Optional[str]):
    """Background task to prepare repository (clone + embedding).
    
    This only prepares the database (clone + embedding), without initializing
    the full RAG pipeline which requires model configuration.
    """
    from urllib.parse import unquote
    
    try:
        logger.info(f"Background prepare started for: {repo_url}")
        
        # Update status to processing
        with preparing_repos_lock:
            preparing_repos[repo_url] = {
                "status": "processing",
                "message": "Cloning repository and generating embeddings...",
                "started_at": datetime.now()
            }
        
        # Import DatabaseManager directly instead of RAG to avoid model configuration requirements
        from api.data_pipeline import DatabaseManager
        from api.config import get_embedder_type
        
        # Parse filter parameters
        parsed_excluded_dirs = None
        parsed_excluded_files = None
        parsed_included_dirs = None
        parsed_included_files = None
        
        if excluded_dirs:
            parsed_excluded_dirs = [unquote(d) for d in excluded_dirs.split('\n') if d.strip()]
        if excluded_files:
            parsed_excluded_files = [unquote(f) for f in excluded_files.split('\n') if f.strip()]
        if included_dirs:
            parsed_included_dirs = [unquote(d) for d in included_dirs.split('\n') if d.strip()]
        if included_files:
            parsed_included_files = [unquote(f) for f in included_files.split('\n') if f.strip()]
        
        # Use DatabaseManager directly to prepare database (clone + embedding)
        # This avoids the need for model configuration (GOOGLE_API_KEY etc.)
        db_manager = DatabaseManager()
        embedder_type = get_embedder_type()
        
        db_manager.prepare_database(
            repo_url, 
            repo_type, 
            token,
            embedder_type=embedder_type,
            excluded_dirs=parsed_excluded_dirs,
            excluded_files=parsed_excluded_files,
            included_dirs=parsed_included_dirs,
            included_files=parsed_included_files
        )
        
        # Update status to ready
        with preparing_repos_lock:
            preparing_repos[repo_url] = {
                "status": "ready",
                "message": "Repository prepared successfully",
                "completed_at": datetime.now()
            }
        
        logger.info(f"Background prepare completed for: {repo_url}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Background prepare failed for {repo_url}: {error_msg}")
        
        with preparing_repos_lock:
            preparing_repos[repo_url] = {
                "status": "error",
                "message": f"Preparation failed: {error_msg}",
                "error_at": datetime.now()
            }

@app.post("/api/repo/prepare", response_model=RepoPrepareResponse)
async def prepare_repo(request: RepoPrepareRequest):
    """
    Asynchronously start repository preparation (clone + embedding).
    
    This endpoint returns immediately with status 'accepted' and starts
    background processing. Use /api/repo_status to check when processing is complete.
    
    Returns:
        - 'accepted': Background preparation started
        - 'processing': Already being processed
        - 'ready': Repository already prepared
        - 'error': An error occurred
    """
    repo_url = request.repo_url.strip()
    
    try:
        # Check if already being prepared
        with preparing_repos_lock:
            if repo_url in preparing_repos:
                prep_status = preparing_repos[repo_url]
                if prep_status["status"] == "processing":
                    return RepoPrepareResponse(
                        status="processing",
                        message="Repository is already being prepared"
                    )
                elif prep_status["status"] == "ready":
                    # Check if the database actually exists
                    pass  # Will be verified below
        
        # Check if repository is already ready (database exists)
        root_path = get_adalflow_default_root_path()
        repo_name = _extract_repo_name(repo_url, request.repo_type)
        db_file = os.path.join(root_path, "databases", f"{repo_name}.pkl")
        
        if os.path.exists(db_file) and os.path.getsize(db_file) > 0:
            try:
                from adalflow.core.db import LocalDB
                db = LocalDB.load_state(db_file)
                documents = db.get_transformed_data(key="split_and_embed")
                
                if documents and len(documents) > 0:
                    valid_docs = [doc for doc in documents if hasattr(doc, 'vector') and doc.vector and len(doc.vector) > 0]
                    if valid_docs:
                        logger.info(f"Repository {repo_name} already prepared with {len(valid_docs)} documents")
                        return RepoPrepareResponse(
                            status="ready",
                            message=f"Repository already prepared with {len(valid_docs)} embedded documents"
                        )
            except Exception as e:
                logger.warning(f"Error loading existing database, will re-prepare: {e}")
        
        # Start background preparation
        logger.info(f"Starting background preparation for: {repo_url}")
        
        repo_prepare_executor.submit(
            _background_prepare_repo,
            repo_url,
            request.repo_type,
            request.token,
            request.excluded_dirs,
            request.excluded_files,
            request.included_dirs,
            request.included_files
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Repository preparation started. Use /api/repo_status to check progress."
            }
        )
        
    except Exception as e:
        logger.error(f"Error starting repository preparation: {e}")
        return RepoPrepareResponse(
            status="error",
            message=f"Failed to start preparation: {str(e)}"
        )

@app.post("/api/repo_status", response_model=RepoStatusResponse)
async def check_repo_status(request: RepoStatusRequest):
    """
    Check if a repository's embedding data is ready for RAG queries.
    This endpoint allows the frontend to check if a repository has been processed
    before attempting to make chat requests.
    
    Returns:
        - 'ready': Repository has been processed and embeddings are available
        - 'processing': Repository is currently being prepared
        - 'not_found': Repository has not been processed yet
        - 'error': An error occurred while checking status
    """
    try:
        from api.data_pipeline import DatabaseManager
        
        # Initialize database manager to check repository status
        db_manager = DatabaseManager()
        
        # Strip whitespace from URL
        repo_url = request.repo_url.strip()
        
        # First check if repository is currently being prepared in background
        with preparing_repos_lock:
            if repo_url in preparing_repos:
                prep_status = preparing_repos[repo_url]
                if prep_status["status"] == "processing":
                    return RepoStatusResponse(
                        status="processing",
                        message=prep_status.get("message", "Repository is being prepared..."),
                        has_embeddings=False,
                        document_count=0
                    )
                # If status is "error" or "ready", continue to check the actual database
                # The database might have been prepared by another process (e.g., WebSocket handler)
        
        # Get the root path for database storage
        root_path = get_adalflow_default_root_path()
        
        # Extract repository name to find the database file
        url_parts = repo_url.rstrip('/').split('/')
        if request.repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
            owner = url_parts[-2]
            repo = url_parts[-1].replace(".git", "")
            repo_name = f"{owner}_{repo}"
        else:
            repo_name = url_parts[-1].replace(".git", "")
        
        # Check if database file exists
        db_file = os.path.join(root_path, "databases", f"{repo_name}.pkl")
        repo_dir = os.path.join(root_path, "repos", repo_name)
        
        logger.info(f"Checking repository status for {repo_name}: db_file={db_file}, repo_dir={repo_dir}")
        
        if os.path.exists(db_file):
            # Check file size first - empty files are definitely corrupted
            file_size = os.path.getsize(db_file)
            if file_size == 0:
                logger.warning(f"Database file is empty, removing: {db_file}")
                try:
                    os.remove(db_file)
                except Exception as remove_err:
                    logger.error(f"Failed to remove empty database file: {remove_err}")
                return RepoStatusResponse(
                    status="not_found",
                    message="Database file was empty and has been removed. Please reprocess the repository.",
                    has_embeddings=False,
                    document_count=0
                )
            
            # Database file exists, try to load and verify
            try:
                from adalflow.core.db import LocalDB
                db = LocalDB.load_state(db_file)
                documents = db.get_transformed_data(key="split_and_embed")
                
                if documents and len(documents) > 0:
                    # Check if documents have valid embeddings
                    valid_docs = [doc for doc in documents if hasattr(doc, 'vector') and doc.vector and len(doc.vector) > 0]
                    if valid_docs:
                        # Extract unique file paths from the documents
                        unique_file_paths = list(set(
                            doc.meta_data.get('file_path', '') 
                            for doc in valid_docs 
                            if hasattr(doc, 'meta_data') and doc.meta_data.get('file_path')
                        ))
                        unique_file_paths.sort()  # Sort for consistent ordering
                        
                        # Clear any stale error status in preparing_repos since database is ready
                        with preparing_repos_lock:
                            if repo_url in preparing_repos:
                                del preparing_repos[repo_url]
                        
                        return RepoStatusResponse(
                            status="ready",
                            message=f"Repository is ready with {len(valid_docs)} embedded documents",
                            has_embeddings=True,
                            document_count=len(valid_docs),
                            file_paths=unique_file_paths
                        )
                    else:
                        return RepoStatusResponse(
                            status="processing",
                            message="Repository data exists but embeddings are not complete",
                            has_embeddings=False,
                            document_count=0
                        )
                else:
                    return RepoStatusResponse(
                        status="processing",
                        message="Repository database exists but no documents found",
                        has_embeddings=False,
                        document_count=0
                    )
            except (EOFError, Exception) as e:
                error_str = str(e)
                # Check for pickle corruption errors
                is_corrupted = (
                    isinstance(e, EOFError) or 
                    "Ran out of input" in error_str or 
                    "could not find MARK" in error_str or
                    "unpickling" in error_str.lower()
                )
                
                if is_corrupted:
                    logger.warning(f"Database file corrupted for {repo_name}: {e}, removing file")
                    try:
                        os.remove(db_file)
                        logger.info(f"Removed corrupted database file: {db_file}")
                    except Exception as remove_err:
                        logger.error(f"Failed to remove corrupted database: {remove_err}")
                    
                    return RepoStatusResponse(
                        status="not_found",
                        message="Database file was corrupted and has been removed. Please reprocess the repository.",
                        has_embeddings=False,
                        document_count=0
                    )
                else:
                    logger.warning(f"Error loading database for {repo_name}: {e}")
                    return RepoStatusResponse(
                        status="processing",
                        message="Repository database exists but may be corrupted or incomplete",
                        has_embeddings=False,
                        document_count=0
                    )
        elif os.path.exists(repo_dir):
            # Repository directory exists but database not yet created
            return RepoStatusResponse(
                status="processing",
                message="Repository has been cloned but embeddings are not yet complete",
                has_embeddings=False,
                document_count=0
            )
        else:
            # Repository not found at all
            return RepoStatusResponse(
                status="not_found",
                message="Repository has not been processed yet",
                has_embeddings=False,
                document_count=0
            )
            
    except Exception as e:
        logger.error(f"Error checking repository status: {e}")
        return RepoStatusResponse(
            status="error",
            message=f"Error checking repository status: {str(e)}",
            has_embeddings=False,
            document_count=0
        )

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "deepwiki-api"
    }

@app.get("/")
async def root():
    """Root endpoint to check if the API is running and list available endpoints dynamically."""
    # Collect routes dynamically from the FastAPI app
    endpoints = {}
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            # Skip docs and static routes
            if route.path in ["/openapi.json", "/docs", "/redoc", "/favicon.ico"]:
                continue
            # Group endpoints by first path segment
            path_parts = route.path.strip("/").split("/")
            group = path_parts[0].capitalize() if path_parts[0] else "Root"
            method_list = list(route.methods - {"HEAD", "OPTIONS"})
            for method in method_list:
                endpoints.setdefault(group, []).append(f"{method} {route.path}")

    # Optionally, sort endpoints for readability
    for group in endpoints:
        endpoints[group].sort()

    return {
        "message": "Welcome to Streaming API",
        "version": "1.0.0",
        "endpoints": endpoints
    }

# --- Processed Projects Endpoint --- (New Endpoint)
@app.get("/api/processed_projects", response_model=List[ProcessedProjectEntry])
async def get_processed_projects():
    """
    Lists all processed projects found in the wiki cache directory.
    Projects are identified by files named like: deepwiki_cache_{repo_type}_{owner}_{repo}_{language}.json
    """
    project_entries: List[ProcessedProjectEntry] = []
    # WIKI_CACHE_DIR is already defined globally in the file

    try:
        if not os.path.exists(WIKI_CACHE_DIR):
            logger.info(f"Cache directory {WIKI_CACHE_DIR} not found. Returning empty list.")
            return []

        logger.info(f"Scanning for project cache files in: {WIKI_CACHE_DIR}")
        filenames = await asyncio.to_thread(os.listdir, WIKI_CACHE_DIR) # Use asyncio.to_thread for os.listdir

        for filename in filenames:
            if filename.startswith("deepwiki_cache_") and filename.endswith(".json"):
                file_path = os.path.join(WIKI_CACHE_DIR, filename)
                try:
                    stats = await asyncio.to_thread(os.stat, file_path) # Use asyncio.to_thread for os.stat
                    parts = filename.replace("deepwiki_cache_", "").replace(".json", "").split('_')

                    # Expecting repo_type_owner_repo_language
                    # Example: deepwiki_cache_github_AsyncFuncAI_deepwiki-open_en.json
                    # parts = [github, AsyncFuncAI, deepwiki-open, en]
                    if len(parts) >= 4:
                        repo_type = parts[0]
                        owner = parts[1]
                        language = parts[-1] # language is the last part
                        repo = "_".join(parts[2:-1]) # repo can contain underscores

                        project_entries.append(
                            ProcessedProjectEntry(
                                id=filename,
                                owner=owner,
                                repo=repo,
                                name=f"{owner}/{repo}",
                                repo_type=repo_type,
                                submittedAt=int(stats.st_mtime * 1000), # Convert to milliseconds
                                language=language
                            )
                        )
                    else:
                        logger.warning(f"Could not parse project details from filename: {filename}")
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue # Skip this file on error

        # Sort by most recent first
        project_entries.sort(key=lambda p: p.submittedAt, reverse=True)
        logger.info(f"Found {len(project_entries)} processed project entries.")
        return project_entries

    except Exception as e:
        logger.error(f"Error listing processed projects from {WIKI_CACHE_DIR}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list processed projects from server cache.")
