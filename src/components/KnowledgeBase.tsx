'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { FaDatabase, FaSearch, FaFileCode, FaCube, FaChevronDown, FaChevronRight, FaSpinner } from 'react-icons/fa';
import { RepoInfo } from '@/types/repoinfo';
import getRepoUrl from '@/utils/getRepoUrl';

interface KBStats {
  status: string;
  total_documents: number;
  valid_documents: number;
  embedding_dimension: number;
  unique_files: number;
  file_paths: string[];
  db_file_size_bytes: number;
  file_type_distribution: Record<string, number>;
  chunk_details: Array<{
    index: number;
    file_path: string;
    type: string;
    title: string;
    token_count: number;
    is_chunk: boolean;
    chunk_index: number | null;
    text_preview: string;
  }>;
}

interface RetrievedChunk {
  index: number;
  file_path: string;
  title: string;
  text: string;
  token_count: number;
  is_chunk: boolean;
  chunk_index: number | null;
  meta_data: Record<string, unknown>;
}

interface RetrievalResult {
  status: string;
  query: string;
  total_retrieved: number;
  chunks: RetrievedChunk[];
  error_message?: string;
}

interface KnowledgeBaseProps {
  repoInfo: RepoInfo;
  provider?: string;
  model?: string;
  language?: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

const KnowledgeBase: React.FC<KnowledgeBaseProps> = ({
  repoInfo,
  provider = 'google',
  model = '',
  language = 'en',
}) => {
  const [stats, setStats] = useState<KBStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [retrievalResult, setRetrievalResult] = useState<RetrievalResult | null>(null);
  const [retrievalLoading, setRetrievalLoading] = useState(false);

  const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set());
  const [showAllChunkDetails, setShowAllChunkDetails] = useState(false);

  const repoUrl = getRepoUrl(repoInfo);

  const loadStats = useCallback(async () => {
    if (!repoUrl) return;
    setStatsLoading(true);
    setStatsError(null);
    try {
      const res = await fetch('/api/kb/stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          repo_type: repoInfo.type,
          token: repoInfo.token,
        }),
      });
      const data: KBStats = await res.json();
      if (data.status === 'error') {
        setStatsError('Failed to load knowledge base statistics');
      } else {
        setStats(data);
      }
    } catch (e) {
      setStatsError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setStatsLoading(false);
    }
  }, [repoUrl, repoInfo.type, repoInfo.token]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const runRetrievalTest = async () => {
    if (!query.trim() || !repoUrl) return;
    setRetrievalLoading(true);
    setRetrievalResult(null);
    setExpandedChunks(new Set());
    try {
      const res = await fetch('/api/kb/retrieval_test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          repo_type: repoInfo.type,
          token: repoInfo.token,
          query: query.trim(),
          provider,
          model: model || undefined,
          language,
        }),
      });
      const data: RetrievalResult = await res.json();
      setRetrievalResult(data);
    } catch (e) {
      setRetrievalResult({
        status: 'error',
        query: query.trim(),
        total_retrieved: 0,
        chunks: [],
        error_message: e instanceof Error ? e.message : 'Unknown error',
      });
    } finally {
      setRetrievalLoading(false);
    }
  };

  const toggleChunk = (index: number) => {
    setExpandedChunks(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="w-full h-full flex flex-col gap-6 overflow-y-auto">
      {/* Stats Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <FaDatabase className="text-[var(--accent-primary)]" />
          <h3 className="text-lg font-bold text-[var(--foreground)] font-serif">Knowledge Base Overview</h3>
          <button
            onClick={loadStats}
            disabled={statsLoading}
            className="ml-auto text-xs px-3 py-1 rounded-md bg-[var(--background)] border border-[var(--border-color)] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors disabled:opacity-50"
          >
            {statsLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {statsError && (
          <div className="p-3 rounded-md bg-red-500/10 text-red-500 text-sm border border-red-500/20 mb-4">
            {statsError}
          </div>
        )}

        {statsLoading && !stats && (
          <div className="flex items-center gap-2 text-[var(--muted)] text-sm py-8 justify-center">
            <FaSpinner className="animate-spin" /> Loading statistics...
          </div>
        )}

        {stats && stats.status === 'not_found' && (
          <div className="p-4 rounded-md bg-[var(--background)] border border-[var(--border-color)] text-[var(--muted)] text-sm">
            Knowledge base not found. Please generate the wiki first.
          </div>
        )}

        {stats && stats.status === 'ready' && (
          <div className="space-y-4">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard
                icon={<FaCube className="text-blue-500" />}
                label="Total Chunks"
                value={stats.valid_documents.toLocaleString()}
                sub={`${stats.total_documents} total docs`}
              />
              <StatCard
                icon={<FaFileCode className="text-green-500" />}
                label="Source Files"
                value={stats.unique_files.toLocaleString()}
              />
              <StatCard
                icon={<FaDatabase className="text-purple-500" />}
                label="DB Size"
                value={formatBytes(stats.db_file_size_bytes)}
              />
              <StatCard
                icon={<FaCube className="text-orange-500" />}
                label="Embedding Dim"
                value={stats.embedding_dimension.toLocaleString()}
              />
            </div>

            {/* File Type Distribution */}
            {Object.keys(stats.file_type_distribution).length > 0 && (
              <div className="p-4 rounded-md bg-[var(--background)] border border-[var(--border-color)]">
                <h4 className="text-sm font-semibold text-[var(--foreground)] mb-3">File Type Distribution</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(stats.file_type_distribution)
                    .sort(([, a], [, b]) => b - a)
                    .map(([ext, count]) => (
                      <span
                        key={ext}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border border-[var(--accent-primary)]/20"
                      >
                        {ext || 'no ext'} <strong>{count}</strong>
                      </span>
                    ))}
                </div>
              </div>
            )}

            {/* Chunk Details */}
            <div className="p-4 rounded-md bg-[var(--background)] border border-[var(--border-color)]">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-[var(--foreground)]">
                  All Chunks ({stats.chunk_details.length})
                </h4>
                <button
                  onClick={() => setShowAllChunkDetails(!showAllChunkDetails)}
                  className="text-xs px-2 py-1 rounded bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                >
                  {showAllChunkDetails ? 'Collapse' : 'Expand All'}
                </button>
              </div>
              {showAllChunkDetails && (
                <div className="space-y-1 max-h-[400px] overflow-y-auto">
                  {stats.chunk_details.map((chunk) => (
                    <div
                      key={chunk.index}
                      className="text-xs p-2 rounded bg-[var(--card-bg)] border border-[var(--border-color)] hover:border-[var(--accent-primary)]/30 transition-colors"
                    >
                      <div className="flex items-center gap-2 text-[var(--muted)]">
                        <span className="font-mono text-[10px] bg-[var(--background)] px-1 rounded">#{chunk.index}</span>
                        <span className="text-[var(--foreground)] font-medium truncate flex-1">{chunk.file_path || 'unknown'}</span>
                        {chunk.token_count > 0 && (
                          <span className="text-[10px]">{chunk.token_count} tokens</span>
                        )}
                      </div>
                      <p className="mt-1 text-[var(--muted)] line-clamp-2">{chunk.text_preview}</p>
                    </div>
                  ))}
                </div>
              )}
              {!showAllChunkDetails && stats.chunk_details.length > 0 && (
                <p className="text-xs text-[var(--muted)]">
                  Click &quot;Expand All&quot; to view all {stats.chunk_details.length} chunks
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Retrieval Test Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <FaSearch className="text-[var(--accent-primary)]" />
          <h3 className="text-lg font-bold text-[var(--foreground)] font-serif">Retrieval Test</h3>
        </div>
        <p className="text-xs text-[var(--muted)] mb-3">
          Test RAG retrieval with the same logic used in Wiki Q&amp;A. See which chunks are retrieved for your query.
        </p>

        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !retrievalLoading && runRetrievalTest()}
            placeholder="Enter a test query..."
            className="flex-1 px-3 py-2 rounded-md bg-[var(--background)] border border-[var(--border-color)] text-[var(--foreground)] text-sm placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
          />
          <button
            onClick={runRetrievalTest}
            disabled={retrievalLoading || !query.trim()}
            className="px-4 py-2 rounded-md bg-[var(--accent-primary)] text-white text-sm font-medium hover:bg-[var(--accent-primary)]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {retrievalLoading ? (
              <>
                <FaSpinner className="animate-spin" /> Retrieving...
              </>
            ) : (
              <>
                <FaSearch /> Retrieve
              </>
            )}
          </button>
        </div>

        {/* Retrieval Results */}
        {retrievalResult && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-sm">
              <span className="text-[var(--muted)]">Query:</span>
              <span className="text-[var(--foreground)] font-medium">&ldquo;{retrievalResult.query}&rdquo;</span>
              <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border border-[var(--accent-primary)]/20">
                {retrievalResult.total_retrieved} chunks retrieved
              </span>
            </div>

            {retrievalResult.status === 'error' && (
              <div className="p-3 rounded-md bg-red-500/10 text-red-500 text-sm border border-red-500/20">
                {retrievalResult.error_message}
              </div>
            )}

            {retrievalResult.chunks.length === 0 && retrievalResult.status === 'success' && (
              <div className="p-4 rounded-md bg-[var(--background)] border border-[var(--border-color)] text-[var(--muted)] text-sm text-center">
                No chunks were retrieved for this query.
              </div>
            )}

            {retrievalResult.chunks.map((chunk) => (
              <div
                key={chunk.index}
                className="rounded-md border border-[var(--border-color)] bg-[var(--background)] overflow-hidden"
              >
                <button
                  onClick={() => toggleChunk(chunk.index)}
                  className="w-full flex items-center gap-2 p-3 text-left hover:bg-[var(--card-bg)] transition-colors"
                >
                  {expandedChunks.has(chunk.index) ? (
                    <FaChevronDown className="text-[var(--muted)] text-xs flex-shrink-0" />
                  ) : (
                    <FaChevronRight className="text-[var(--muted)] text-xs flex-shrink-0" />
                  )}
                  <span className="font-mono text-xs text-[var(--accent-primary)] bg-[var(--accent-primary)]/10 px-1.5 py-0.5 rounded flex-shrink-0">
                    #{chunk.index}
                  </span>
                  <span className="text-sm text-[var(--foreground)] font-medium truncate flex-1">
                    {chunk.file_path || 'unknown'}
                  </span>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {chunk.token_count > 0 && (
                      <span className="text-[10px] text-[var(--muted)] bg-[var(--background)] px-1.5 py-0.5 rounded border border-[var(--border-color)]">
                        {chunk.token_count} tokens
                      </span>
                    )}
                    {chunk.is_chunk && chunk.chunk_index !== null && (
                      <span className="text-[10px] text-[var(--muted)] bg-[var(--background)] px-1.5 py-0.5 rounded border border-[var(--border-color)]">
                        chunk #{chunk.chunk_index}
                      </span>
                    )}
                  </div>
                </button>

                {expandedChunks.has(chunk.index) && (
                  <div className="border-t border-[var(--border-color)]">
                    {/* Meta info */}
                    <div className="px-3 py-2 bg-[var(--card-bg)] border-b border-[var(--border-color)]">
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[var(--muted)]">
                        {chunk.title && <span>Title: <strong>{chunk.title}</strong></span>}
                        {chunk.meta_data.type && <span>Type: <strong>{String(chunk.meta_data.type)}</strong></span>}
                        {chunk.meta_data.is_code !== undefined && (
                          <span>Code: <strong>{chunk.meta_data.is_code ? 'Yes' : 'No'}</strong></span>
                        )}
                      </div>
                    </div>
                    {/* Full text content */}
                    <div className="p-3 max-h-[400px] overflow-y-auto">
                      <pre className="text-xs text-[var(--foreground)] whitespace-pre-wrap break-words font-mono leading-relaxed">
                        {chunk.text}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="p-3 rounded-md bg-[var(--background)] border border-[var(--border-color)] flex items-start gap-3">
      <div className="mt-0.5">{icon}</div>
      <div>
        <p className="text-xs text-[var(--muted)]">{label}</p>
        <p className="text-lg font-bold text-[var(--foreground)]">{value}</p>
        {sub && <p className="text-[10px] text-[var(--muted)]">{sub}</p>}
      </div>
    </div>
  );
}

export default KnowledgeBase;
