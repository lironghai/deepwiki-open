from typing import Sequence, List
from copy import deepcopy
from tqdm import tqdm
import logging
import adalflow as adal
from adalflow.core.types import Document
from adalflow.core.component import DataComponent
import requests
import os
import time
import threading

# Configure logging
from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    Supports both RPM (requests per minute) and TPM (tokens per minute) limits.
    """
    
    def __init__(self, rpm: int = None, tpm: int = None):
        """
        Initialize rate limiter.
        
        Args:
            rpm: Requests per minute limit
            tpm: Tokens per minute limit
        """
        self.rpm = rpm
        self.tpm = tpm
        self.lock = threading.Lock()
        
        # Request tracking
        self.request_timestamps: List[float] = []
        self.token_usage: List[tuple] = []  # (timestamp, tokens)
        
        # Calculate minimum interval between requests based on RPM
        if rpm and rpm > 0:
            self.min_request_interval = 60.0 / rpm
        else:
            self.min_request_interval = 0
        
        self.last_request_time = 0
        
        logger.info(f"RateLimiter initialized: RPM={rpm}, TPM={tpm}, min_interval={self.min_request_interval:.3f}s")
    
    def _cleanup_old_records(self, current_time: float):
        """Remove records older than 1 minute."""
        cutoff_time = current_time - 60.0
        
        # Cleanup request timestamps
        self.request_timestamps = [t for t in self.request_timestamps if t > cutoff_time]
        
        # Cleanup token usage
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff_time]
    
    def wait_if_needed(self, estimated_tokens: int = 0):
        """
        Wait if necessary to respect rate limits.
        
        Args:
            estimated_tokens: Estimated number of tokens for this request
        """
        with self.lock:
            current_time = time.time()
            self._cleanup_old_records(current_time)
            
            wait_time = 0
            
            # Check RPM limit
            if self.rpm and len(self.request_timestamps) >= self.rpm:
                # Need to wait until oldest request expires
                oldest_request = min(self.request_timestamps)
                wait_for_rpm = (oldest_request + 60.0) - current_time
                if wait_for_rpm > 0:
                    wait_time = max(wait_time, wait_for_rpm)
                    logger.debug(f"RPM limit reached, need to wait {wait_for_rpm:.2f}s")
            
            # Check TPM limit
            if self.tpm and estimated_tokens > 0:
                current_token_usage = sum(tokens for _, tokens in self.token_usage)
                if current_token_usage + estimated_tokens > self.tpm:
                    # Need to wait until enough tokens expire
                    if self.token_usage:
                        oldest_token_time = min(t for t, _ in self.token_usage)
                        wait_for_tpm = (oldest_token_time + 60.0) - current_time
                        if wait_for_tpm > 0:
                            wait_time = max(wait_time, wait_for_tpm)
                            logger.debug(f"TPM limit approaching, need to wait {wait_for_tpm:.2f}s")
            
            # Ensure minimum interval between requests
            if self.min_request_interval > 0:
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_request_interval:
                    interval_wait = self.min_request_interval - time_since_last
                    wait_time = max(wait_time, interval_wait)
            
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.2f}s before next request")
                time.sleep(wait_time)
                current_time = time.time()
            
            # Record this request
            self.request_timestamps.append(current_time)
            if estimated_tokens > 0:
                self.token_usage.append((current_time, estimated_tokens))
            self.last_request_time = current_time
    
    def record_tokens(self, actual_tokens: int):
        """
        Record actual token usage after a request completes.
        Call this to update token tracking with actual usage.
        """
        with self.lock:
            current_time = time.time()
            # Update the most recent token record with actual usage
            if self.token_usage and abs(self.token_usage[-1][0] - self.last_request_time) < 1:
                # Replace estimated with actual
                self.token_usage[-1] = (self.token_usage[-1][0], actual_tokens)

    def __getstate__(self):
        """
        Customize serialization to exclude non-picklable threading.Lock object.
        This method is called by pickle when saving the object's state.
        """
        state = self.__dict__.copy()
        # Remove the unpicklable lock object
        if 'lock' in state:
            del state['lock']
        return state

    def __setstate__(self, state):
        """
        Customize deserialization to re-create the threading.Lock object.
        This method is called by pickle when loading the object's state.
        """
        self.__dict__.update(state)
        # Re-initialize the lock after unpickling
        self.lock = threading.Lock()


class RateLimitedEmbeddingProcessor(DataComponent):
    """
    Process documents for embeddings with rate limiting support.
    Respects RPM and TPM limits from configuration.
    """
    
    def __init__(self, embedder: adal.Embedder, batch_size: int = 10, 
                 rpm: int = None, tpm: int = None) -> None:
        super().__init__()
        self.embedder = embedder
        self.batch_size = batch_size
        self.rate_limiter = RateLimiter(rpm=rpm, tpm=tpm)
        
        # Retry configuration
        self.max_retries = 5
        self.base_retry_delay = 65  # Base delay in seconds
        self.max_retry_delay = 180  # Maximum delay in seconds
        
        logger.info(f"RateLimitedEmbeddingProcessor initialized: batch_size={batch_size}, rpm={rpm}, tpm={tpm}")
    
    def _estimate_tokens(self, texts: List[str]) -> int:
        """Estimate token count for a batch of texts."""
        # Rough estimation: ~4 characters per token for most languages
        # Add 20% buffer for safety
        total_chars = sum(len(text) for text in texts)
        estimated_tokens = int(total_chars / 4 * 1.2)
        return estimated_tokens
    
    def _process_batch_with_retry(self, texts: List[str], batch_idx: int) -> List:
        """Process a batch with retry logic for rate limit errors."""
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # Estimate tokens for rate limiting
                estimated_tokens = self._estimate_tokens(texts)
                
                # Wait if needed based on rate limits
                self.rate_limiter.wait_if_needed(estimated_tokens)
                
                # Make the API call
                result = self.embedder(input=texts)
                
                if result.data:
                    return [item.embedding for item in result.data]
                else:
                    logger.warning(f"Batch {batch_idx}: No embeddings returned")
                    return []
                    
            except Exception as e:
                error_str = str(e)
                
                # Check for rate limit error (429)
                if "429" in error_str or "Too Many Requests" in error_str or "rate limit" in error_str.lower():
                    retry_count += 1
                    
                    if retry_count > self.max_retries:
                        logger.error(f"Batch {batch_idx}: Max retries ({self.max_retries}) exceeded for rate limit error")
                        raise
                    
                    # Exponential backoff with jitter
                    delay = min(
                        self.base_retry_delay * (2 ** (retry_count - 1)),
                        self.max_retry_delay
                    )
                    # Add some jitter (10-30% of delay)
                    import random
                    jitter = delay * random.uniform(0.1, 0.3)
                    actual_delay = delay + jitter
                    
                    logger.warning(
                        f"Batch {batch_idx}: Rate limit hit (429), retry {retry_count}/{self.max_retries} "
                        f"after {actual_delay:.1f}s delay"
                    )
                    time.sleep(actual_delay)
                else:
                    # Non-rate-limit error, don't retry
                    logger.error(f"Batch {batch_idx}: Error processing batch: {e}")
                    raise
        
        return []
    
    def __call__(self, documents: Sequence[Document]) -> Sequence[Document]:
        output = deepcopy(documents)
        total_docs = len(output)
        
        logger.info(f"Processing {total_docs} documents with rate-limited embeddings (batch_size={self.batch_size})")
        
        # Process in batches
        successful_docs = []
        expected_embedding_size = None
        
        for batch_start in tqdm(range(0, total_docs, self.batch_size), desc="Processing embedding batches"):
            batch_end = min(batch_start + self.batch_size, total_docs)
            batch_docs = output[batch_start:batch_end]
            batch_texts = [doc.text for doc in batch_docs]
            batch_idx = batch_start // self.batch_size + 1
            
            try:
                embeddings = self._process_batch_with_retry(batch_texts, batch_idx)
                
                if embeddings and len(embeddings) == len(batch_docs):
                    for i, embedding in enumerate(embeddings):
                        doc_idx = batch_start + i
                        
                        # Validate embedding size consistency
                        if expected_embedding_size is None:
                            expected_embedding_size = len(embedding)
                            logger.info(f"Expected embedding size set to: {expected_embedding_size}")
                        elif len(embedding) != expected_embedding_size:
                            file_path = batch_docs[i].meta_data.get('file_path', f'document_{doc_idx}')
                            logger.warning(
                                f"Document '{file_path}' has inconsistent embedding size "
                                f"{len(embedding)} != {expected_embedding_size}, skipping"
                            )
                            continue
                        
                        output[doc_idx].vector = embedding
                        successful_docs.append(output[doc_idx])
                else:
                    logger.warning(
                        f"Batch {batch_idx}: Expected {len(batch_docs)} embeddings, got {len(embeddings) if embeddings else 0}"
                    )
                    
            except Exception as e:
                logger.error(f"Batch {batch_idx}: Failed to process batch: {e}")
                # Continue with next batch instead of failing completely
                continue
        
        logger.info(f"Successfully processed {len(successful_docs)}/{total_docs} documents with embeddings")
        return successful_docs

    def __getstate__(self):
        """
        Customize serialization to exclude non-picklable objects.
        This method is called by pickle when saving the object's state.
        """
        state = self.__dict__.copy()
        # The rate_limiter contains a threading.Lock which cannot be pickled,
        # but RateLimiter now has its own __getstate__/__setstate__ methods
        # so it will handle its own serialization properly.
        return state

    def __setstate__(self, state):
        """
        Customize deserialization to restore the object's state.
        This method is called by pickle when loading the object's state.
        """
        self.__dict__.update(state)
        # rate_limiter will be restored by its own __setstate__ method


class OllamaModelNotFoundError(Exception):
    """Custom exception for when Ollama model is not found"""
    pass

def check_ollama_model_exists(model_name: str, ollama_host: str = None) -> bool:
    """
    Check if an Ollama model exists before attempting to use it.
    
    Args:
        model_name: Name of the model to check
        ollama_host: Ollama host URL, defaults to localhost:11434
        
    Returns:
        bool: True if model exists, False otherwise
    """
    if ollama_host is None:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        # Remove /api prefix if present and add it back
        if ollama_host.endswith('/api'):
            ollama_host = ollama_host[:-4]
        
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            available_models = [model.get('name', '').split(':')[0] for model in models_data.get('models', [])]
            model_base_name = model_name.split(':')[0]  # Remove tag if present
            
            is_available = model_base_name in available_models
            if is_available:
                logger.info(f"Ollama model '{model_name}' is available")
            else:
                logger.warning(f"Ollama model '{model_name}' is not available. Available models: {available_models}")
            return is_available
        else:
            logger.warning(f"Could not check Ollama models, status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not connect to Ollama to check models: {e}")
        return False
    except Exception as e:
        logger.warning(f"Error checking Ollama model availability: {e}")
        return False

class OllamaDocumentProcessor(DataComponent):
    """
    Process documents for Ollama embeddings by processing one document at a time.
    Adalflow Ollama Client does not support batch embedding, so we need to process each document individually.
    """
    def __init__(self, embedder: adal.Embedder) -> None:
        super().__init__()
        self.embedder = embedder

    def __call__(self, documents: Sequence[Document]) -> Sequence[Document]:
        output = deepcopy(documents)
        logger.info(f"Processing {len(output)} documents individually for Ollama embeddings")

        successful_docs = []
        expected_embedding_size = None

        for i, doc in enumerate(tqdm(output, desc="Processing documents for Ollama embeddings")):
            try:
                # Get embedding for a single document
                result = self.embedder(input=doc.text)
                if result.data and len(result.data) > 0:
                    embedding = result.data[0].embedding

                    # Validate embedding size consistency
                    if expected_embedding_size is None:
                        expected_embedding_size = len(embedding)
                        logger.info(f"Expected embedding size set to: {expected_embedding_size}")
                    elif len(embedding) != expected_embedding_size:
                        file_path = getattr(doc, 'meta_data', {}).get('file_path', f'document_{i}')
                        logger.warning(f"Document '{file_path}' has inconsistent embedding size {len(embedding)} != {expected_embedding_size}, skipping")
                        continue

                    # Assign the embedding to the document
                    output[i].vector = embedding
                    successful_docs.append(output[i])
                else:
                    file_path = getattr(doc, 'meta_data', {}).get('file_path', f'document_{i}')
                    logger.warning(f"Failed to get embedding for document '{file_path}', skipping")
            except Exception as e:
                file_path = getattr(doc, 'meta_data', {}).get('file_path', f'document_{i}')
                logger.error(f"Error processing document '{file_path}': {e}, skipping")

        logger.info(f"Successfully processed {len(successful_docs)}/{len(output)} documents with consistent embeddings")
        return successful_docs