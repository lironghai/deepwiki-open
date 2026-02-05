# DeepWiki Workflow Audit Report

**Date**: 2026-01-26
**Scope**: Wiki Generation & Q&A Workflows
**Severity Levels**: 🔴 Critical | 🟡 Warning | 🔵 Info

---

## Executive Summary

This audit identifies **15 issues** across wiki generation and Q&A workflows:
- **3 Critical**: Resource leaks, race conditions, security vulnerabilities
- **8 Warnings**: Error handling, performance, reliability concerns
- **4 Info**: Code quality, maintainability improvements

### Overall Assessment
- **Wiki Generation**: ⚠️ Moderate Risk - Needs error handling improvements
- **Q&A Workflow**: ⚠️ Moderate Risk - Resource management and timeout issues
- **Code Quality**: ✅ Good - Well-structured but needs hardening

---

## Part 1: Wiki Generation Workflow Analysis

### Architecture Overview
```
Frontend Request → WebSocket (websocket_wiki_parallel.py)
                → ParallelWikiGenerator (tools/wiki_generator.py)
                → LLM Service (per page, max 5 workers)
                → Codemap Cache (tools/codemap_cache.py)
                → MermaidPreprocessor → Response
```

### Issues Found

#### 🔴 CRITICAL-1: WebSocket Connection Without Timeout Protection
**File**: `api/websocket_wiki_parallel.py:79-203`
**Issue**: WebSocket connections can hang indefinitely if client disconnects or LLM service stalls
```python
async def handle_websocket_wiki_generate(websocket: WebSocket):
    await websocket.accept()  # ❌ No timeout, no keepalive

    try:
        request_data = await websocket.receive_json()  # ❌ Can block forever
        # ... long-running generation ...
```

**Impact**:
- Server resources tied up indefinitely
- Zombie connections accumulate
- No client heartbeat/keepalive mechanism

**Recommendation**:
```python
# Add timeout wrapper
async def handle_websocket_wiki_generate(websocket: WebSocket):
    await websocket.accept()

    try:
        # Add timeout for receiving request
        request_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=30.0  # 30 seconds
        )

        # Add periodic keepalive during generation
        # ... (implement heartbeat mechanism)
```

---

#### 🔴 CRITICAL-2: Race Condition in Progress Callback
**File**: `api/websocket_wiki_parallel.py:136-146`
**Issue**: Progress callback creates async tasks without tracking, leading to potential race conditions
```python
def progress_callback(completed: int, total: int):
    completed_count[0] = completed
    # ❌ Creates fire-and-forget task, no error handling
    asyncio.create_task(websocket.send_json({
        "stage": "generating",
        "progress": int(40 + (completed / total) * 50),
        "completed": completed,
        "total": total
    }))
```

**Impact**:
- Progress updates can fail silently
- Out-of-order progress messages
- WebSocket send errors not caught
- Tasks not awaited = resource leak potential

**Recommendation**:
```python
# Use proper async pattern
async def progress_callback(completed: int, total: int):
    try:
        await websocket.send_json({
            "stage": "generating",
            "progress": int(40 + (completed / total) * 50),
            "completed": completed,
            "total": total
        })
    except Exception as e:
        logger.warning(f"Failed to send progress update: {e}")

# Or use queue pattern for batching
```

---

#### 🟡 WARNING-1: LLM Service Initialization Failure Handling
**File**: `api/websocket_wiki_parallel.py:117-126`
**Issue**: LLM service creation failure closes WebSocket but doesn't clean up resources
```python
try:
    llm_service = get_llm_service(request.provider, request.model)
except Exception as e:
    logger.error(f"Failed to create LLM service: {e}")
    await websocket.send_json({
        "stage": "error",
        "error": f"Failed to initialize LLM service: {str(e)}"
    })
    await websocket.close()
    return  # ❌ No cleanup of RAG resources
```

**Impact**:
- RAG instance (`request_rag`) not cleaned up
- Potential memory leak from prepared retriever
- Database connections may stay open

**Recommendation**:
```python
request_rag = None
try:
    request_rag = RAG(provider=request.provider, model=request.model)
    # ... prepare retriever ...
    llm_service = get_llm_service(request.provider, request.model)
except Exception as e:
    # Clean up on failure
    if request_rag and hasattr(request_rag, 'cleanup'):
        request_rag.cleanup()
    # ... send error and close ...
```

---

#### 🟡 WARNING-2: Codemap Cache Thread-Safety Concerns
**File**: `api/tools/codemap_cache.py:110-128`
**Issue**: TTL-based cache expiration check is not atomic
```python
def get(self, repo_path: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
    with self._cache_lock:
        if not force_reload and cache_key in self._cache:
            entry = self._cache[cache_key]

            # ❌ Time check outside atomic operation
            age = datetime.now() - entry.loaded_at
            if age < self._ttl:
                return entry.data
            else:
                # ❌ Another thread could access expired entry before deletion
                del self._cache[cache_key]
```

**Impact**:
- Potential for returning expired data in high concurrency
- Cache coherency issues

**Recommendation**:
```python
# Use RLock properly with atomic checks
with self._cache_lock:
    if cache_key in self._cache:
        entry = self._cache[cache_key]
        if datetime.now() - entry.loaded_at < self._ttl:
            return entry.data
        # Atomically remove expired entry
        del self._cache[cache_key]

    # Load from file under lock
    return self._load_from_file(repo_path)
```

---

#### 🟡 WARNING-3: Missing Rate Limiting
**File**: `api/websocket_wiki_parallel.py`, `api/api.py`
**Issue**: No rate limiting on wiki generation or Q&A endpoints

**Impact**:
- Vulnerable to abuse/DoS
- LLM API cost explosion
- Server resource exhaustion

**Recommendation**:
```python
# Add rate limiting middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("10/hour")  # 10 wiki generations per hour
async def handle_websocket_wiki_generate(websocket: WebSocket):
    # ...
```

---

#### 🟡 WARNING-4: Incomplete Error Recovery in Parallel Generation
**File**: `api/tools/wiki_generator.py:106-130`
**Issue**: Error in one page doesn't prevent progress callback issues
```python
for coro in asyncio.as_completed(tasks):
    try:
        result = await coro
        results.append(result)
        completed += 1

        if progress_callback:
            progress_callback(completed, len(pages))  # ❌ Can raise

    except Exception as e:
        # ❌ Doesn't handle callback failures
        error_result = PageGenerationResult(...)
        results.append(error_result)
        completed += 1
```

**Impact**:
- Callback exception can break entire generation
- Progress tracking becomes unreliable

**Recommendation**:
```python
# Wrap callback with error handling
if progress_callback:
    try:
        await progress_callback(completed, len(pages))
    except Exception as callback_err:
        logger.warning(f"Progress callback failed: {callback_err}")
        # Continue generation regardless
```

---

#### 🔵 INFO-1: Hard-Coded Worker Pool Size
**File**: `api/tools/wiki_generator.py:44-62`
**Issue**: `max_workers=5` is hard-coded, not configurable

**Recommendation**:
```python
# Make configurable via environment
MAX_WORKERS = int(os.getenv("WIKI_MAX_WORKERS", "5"))

def __init__(self, llm_service=None, max_workers=MAX_WORKERS, ...):
    # ...
```

---

#### 🔵 INFO-2: Mermaid Preprocessing Happens After All Pages Complete
**File**: `api/websocket_wiki_parallel.py:156-173`
**Issue**: All pages are generated first, then Mermaid is processed sequentially

**Impact**:
- Could be parallelized for better performance
- User waits longer for final result

**Recommendation**:
```python
# Process Mermaid during generation
async def _generate_single_page(...):
    content = await self._generate_content(...)
    # Process Mermaid immediately
    processed_content = MermaidPreprocessor.extract_and_process_mermaid_blocks(content)
    return processed_content
```

---

## Part 2: Q&A Workflow Analysis

### Architecture Overview
```
Frontend → WebSocket (websocket_wiki.py)
        → RAG.prepare_retriever() → Database + Embeddings
        → RAG.call(query) → LayeredRAG (if enabled)
                          → Retriever (FAISS)
                          → LLM Generator
        → Stream Response → Frontend
```

### Issues Found

#### 🔴 CRITICAL-3: RAG Retrieval Without Timeout
**File**: `api/websocket_wiki.py:298-331`
**Issue**: RAG retrieval can hang indefinitely on slow embeddings or FAISS queries
```python
try:
    # ❌ No timeout protection
    retrieved_documents = request_rag(rag_query, language=request.language)

    if retrieved_documents and retrieved_documents[0].documents:
        # ... process documents ...
```

**Impact**:
- WebSocket connection hangs
- User receives no response
- Server resources tied up

**Recommendation**:
```python
# Add timeout for retrieval
try:
    retrieved_documents = await asyncio.wait_for(
        asyncio.to_thread(request_rag, rag_query, language=request.language),
        timeout=30.0  # 30 seconds max
    )
except asyncio.TimeoutError:
    logger.warning("RAG retrieval timed out, continuing without context")
    retrieved_documents = None
```

---

#### 🟡 WARNING-5: Memory Leak in Conversation History
**File**: `api/rag.py:28-89`
**Issue**: `CustomConversation.dialog_turns` grows unbounded
```python
class CustomConversation:
    def __init__(self):
        self.dialog_turns = []  # ❌ No size limit

    def append_dialog_turn(self, dialog_turn):
        if not hasattr(self, 'dialog_turns'):
            self.dialog_turns = []
        self.dialog_turns.append(dialog_turn)  # ❌ Unbounded growth
```

**Impact**:
- Memory usage grows with long conversations
- No conversation cleanup mechanism

**Recommendation**:
```python
class CustomConversation:
    MAX_TURNS = 50  # Reasonable limit

    def append_dialog_turn(self, dialog_turn):
        if not hasattr(self, 'dialog_turns'):
            self.dialog_turns = []

        self.dialog_turns.append(dialog_turn)

        # Keep only recent turns
        if len(self.dialog_turns) > self.MAX_TURNS:
            self.dialog_turns = self.dialog_turns[-self.MAX_TURNS:]
```

---

#### 🟡 WARNING-6: Insufficient Input Validation
**File**: `api/websocket_wiki.py:79-88`
**Issue**: Query size check is based on token count but no content sanitization
```python
if hasattr(last_message, 'content') and last_message.content:
    tokens = count_tokens(last_message.content, request.provider == "ollama")
    logger.info(f"Request size: {tokens} tokens")
    if tokens > 8000:
        logger.warning(f"Request exceeds recommended token limit ({tokens} > 7500)")
        input_too_large = True  # ❌ Just a flag, no enforcement
```

**Impact**:
- No prevention of excessively long queries
- No sanitization of malicious input
- No length limit enforcement

**Recommendation**:
```python
# Add strict validation
MAX_QUERY_LENGTH = 10000  # characters
MAX_TOKENS = 7500

if len(last_message.content) > MAX_QUERY_LENGTH:
    await websocket.send_text(f"Error: Query too long (max {MAX_QUERY_LENGTH} characters)")
    await websocket.close()
    return

# Sanitize input
sanitized_content = sanitize_user_input(last_message.content)
last_message.content = sanitized_content
```

---

#### 🟡 WARNING-7: Embedding Size Inconsistency Error Handling
**File**: `api/websocket_wiki.py:132-140`
**Issue**: Generic error message for embedding issues
```python
except Exception as e:
    logger.error(f"Error preparing retriever: {str(e)}")
    if "All embeddings should be of the same size" in str(e):
        await websocket.send_text("Error: Inconsistent embedding sizes...")
    else:
        await websocket.send_text(f"Error preparing retriever: {str(e)}")
    # ❌ Doesn't identify which documents failed
    # ❌ No retry mechanism
```

**Impact**:
- User doesn't know which files caused issues
- No automatic recovery
- Difficult to debug

**Recommendation**:
```python
# Add detailed error reporting
try:
    request_rag.prepare_retriever(...)
except EmbeddingError as e:
    # Identify problematic documents
    failed_docs = e.get_failed_documents()
    logger.error(f"Embedding failed for {len(failed_docs)} documents: {failed_docs}")

    # Offer retry with problematic docs excluded
    await websocket.send_json({
        "error": "Some documents failed to embed",
        "failed_files": failed_docs,
        "suggestion": "Retry with these files excluded?"
    })
```

---

#### 🟡 WARNING-8: LayeredRAG Fallback Strategy
**File**: `api/rag.py:478-510`
**Issue**: LayeredRAG failure falls back to standard RAG but loses context
```python
try:
    layer_result = self.layered_rag.retrieve(query, self.repo_path, num_docs=10)
    # ... use layer_result ...
except Exception as e:
    logger.warning(f"LayeredRAG failed: {e}. Falling back to standard RAG.")
    # ❌ Loses codemap context benefits
    retrieved_documents = self.retriever(query)
```

**Impact**:
- Quality degradation when LayeredRAG fails
- User not informed of fallback

**Recommendation**:
```python
# Graceful degradation with notification
try:
    layer_result = self.layered_rag.retrieve(...)
    # ... use layer_result ...
except Exception as e:
    logger.warning(f"LayeredRAG failed: {e}. Falling back to standard RAG.")

    # Notify user of degraded mode
    if user_notification_callback:
        user_notification_callback("Using standard retrieval (codemap unavailable)")

    retrieved_documents = self.retriever(query)
```

---

#### 🔵 INFO-3: Hard-Coded Deep Research Iterations
**File**: `api/websocket_wiki.py:179-182, 355`
**Issue**: Deep Research limited to 5 iterations (hard-coded)
```python
if is_deep_research:
    research_iteration = sum(1 for msg in request.messages if msg.role == 'assistant') + 1
    # ...
    is_final_iteration = research_iteration >= 5  # ❌ Hard-coded
```

**Recommendation**:
```python
# Make configurable
DEEP_RESEARCH_MAX_ITERATIONS = int(os.getenv("DEEP_RESEARCH_MAX_ITERATIONS", "5"))

is_final_iteration = research_iteration >= DEEP_RESEARCH_MAX_ITERATIONS
```

---

#### 🔵 INFO-4: Codemap Context Cache Validity Hard-Coded
**File**: `api/websocket_wiki.py:228-230`
**Issue**: 1-hour cache validity is hard-coded
```python
cache_age = time.time() - os.path.getmtime(cache_file)
if cache_age < 3600:  # ❌ Hard-coded 1 hour
    # ... use cache ...
```

**Recommendation**:
```python
# Make configurable
CODEMAP_CACHE_TTL = int(os.getenv("CODEMAP_CACHE_TTL_SECONDS", "3600"))

if cache_age < CODEMAP_CACHE_TTL:
    # ... use cache ...
```

---

## Part 3: Cross-Cutting Concerns

### Error Handling Inconsistencies
**Locations**: Multiple files
**Issue**: Mix of error handling patterns:
- Some return error objects
- Some raise exceptions
- Some send WebSocket messages
- Some log and continue

**Recommendation**: Standardize error handling with custom exception hierarchy:
```python
# api/exceptions.py
class DeepWikiException(Exception):
    """Base exception for DeepWiki"""
    pass

class WikiGenerationError(DeepWikiException):
    """Wiki generation failed"""
    pass

class RAGRetrievalError(DeepWikiException):
    """RAG retrieval failed"""
    pass

class EmbeddingError(DeepWikiException):
    """Embedding generation failed"""
    def __init__(self, message, failed_documents=None):
        super().__init__(message)
        self.failed_documents = failed_documents or []
```

---

### Logging Quality
**Issue**: Inconsistent log levels and missing context
- Some errors logged as warnings
- Missing request IDs for tracing
- No structured logging (JSON format)

**Recommendation**:
```python
# Add structured logging with context
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "wiki_generation_started",
    request_id=request_id,
    repo_url=repo_url,
    pages_count=len(pages)
)
```

---

### Resource Cleanup
**Issue**: Missing cleanup in error paths
- RAG instances not explicitly closed
- Database connections not released
- Thread pools not shut down
- WebSocket connections not properly closed

**Recommendation**: Implement context managers and cleanup handlers:
```python
class RAG:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        if hasattr(self, 'retriever'):
            # Close retriever resources
            pass
```

---

## Recommendations Summary

### Immediate Actions (Critical)
1. ✅ Add WebSocket timeout protection (CRITICAL-1)
2. ✅ Fix progress callback race condition (CRITICAL-2)
3. ✅ Add RAG retrieval timeout (CRITICAL-3)

### Short-Term (1-2 weeks)
4. ✅ Implement proper resource cleanup
5. ✅ Add rate limiting
6. ✅ Fix codemap cache atomicity
7. ✅ Add conversation history size limits
8. ✅ Improve input validation and sanitization

### Medium-Term (1 month)
9. ✅ Standardize error handling with exception hierarchy
10. ✅ Implement structured logging
11. ✅ Add comprehensive monitoring and alerting
12. ✅ Parallelize Mermaid preprocessing
13. ✅ Make configuration values environment-based

### Long-Term (3 months)
14. ✅ Add comprehensive integration tests
15. ✅ Implement circuit breakers for external services
16. ✅ Add request tracing (OpenTelemetry)
17. ✅ Performance profiling and optimization
18. ✅ Add health check endpoints

---

## Testing Recommendations

### Unit Tests Needed
- [ ] `ParallelWikiGenerator` error scenarios
- [ ] `CodemapCacheManager` thread safety
- [ ] `CustomConversation` size limits
- [ ] `LayeredRAG` fallback behavior

### Integration Tests Needed
- [ ] End-to-end wiki generation with failures
- [ ] Q&A with retrieval timeouts
- [ ] WebSocket reconnection handling
- [ ] Concurrent request handling

### Load Tests Needed
- [ ] 100 concurrent wiki generations
- [ ] 1000 concurrent Q&A requests
- [ ] Long-running conversation memory usage
- [ ] Codemap cache under high concurrency

---

## Conclusion

The codebase is **well-structured** but needs **hardening** in several areas:

**Strengths**:
- ✅ Clean separation of concerns
- ✅ Good use of async/await patterns
- ✅ Comprehensive feature set
- ✅ Proper use of caching

**Weaknesses**:
- ⚠️ Insufficient timeout protection
- ⚠️ Inconsistent error handling
- ⚠️ Resource cleanup gaps
- ⚠️ Missing rate limiting

**Risk Level**: **MODERATE** - No critical security vulnerabilities, but reliability and resource management need improvement.

**Recommended Priority**: Address all Critical issues within 1 week, Warnings within 1 month.
