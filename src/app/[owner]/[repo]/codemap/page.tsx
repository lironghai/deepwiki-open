'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { FaArrowLeft, FaSync, FaDownload, FaExclamationTriangle } from 'react-icons/fa';
import dynamic from 'next/dynamic';
import ThemeToggle from '@/components/theme-toggle';
import { useLanguage } from '@/contexts/LanguageContext';

// 动态导入Codemap组件（客户端渲染）
// 使用更稳定的导入方式，避免chunk文件缺失问题
const Codemap = dynamic(
  () => import('@/components/Codemap').catch((err) => {
    console.error('Failed to load Codemap component:', err);
    // 返回一个错误占位组件
    return {
      default: () => (
        <div className="flex items-center justify-center h-full">
          <div className="text-center p-6">
            <FaExclamationTriangle className="w-16 h-16 text-[var(--highlight)] mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2 text-[var(--foreground)]">
              组件加载失败
            </h2>
            <p className="text-[var(--muted)] mb-4">
              请刷新页面重试，或检查浏览器控制台错误信息
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-md hover:opacity-90"
            >
              刷新页面
            </button>
          </div>
        </div>
      ),
    };
  }),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--accent-primary)] mx-auto mb-4"></div>
          <p className="text-[var(--muted)]">加载代码地图组件...</p>
        </div>
      </div>
    ),
  }
);

interface CodeNode {
  id: string;
  name: string;
  type: string;
  path: string;
  language?: string;
  start_line?: number;
  end_line?: number;
  description?: string;
  metadata?: Record<string, any>;
}

interface CodemapData {
  nodes: CodeNode[];
  edges: any[];
  metadata: {
    repo_url?: string;
    repo_type?: string;
    owner?: string;
    repo?: string;
    total_files: number;
    total_lines: number;
    languages: Record<string, number>;
    node_count: number;
    edge_count: number;
    generated_at?: string;
  };
}

export default function CodemapPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { messages } = useLanguage();

  const owner = params.owner as string;
  const repo = params.repo as string;
  const token = searchParams.get('token') || '';
  const repoUrl = searchParams.get('repo_url') ? decodeURIComponent(searchParams.get('repo_url') || '') : undefined;
  const repoHost = (() => {
    if (!repoUrl) return '';
    try {
      return new URL(repoUrl).hostname.toLowerCase();
    } catch (e) {
      return '';
    }
  })();
  const repoType = repoHost?.includes('bitbucket')
    ? 'bitbucket'
    : repoHost?.includes('gitlab')
      ? 'gitlab'
      : repoHost?.includes('github')
        ? 'github'
        : searchParams.get('type') || 'github';

  const [codemapData, setCodemapData] = useState<CodemapData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // 加载缓存的代码地图
  const loadCachedCodemap = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const params = new URLSearchParams({
        owner,
        repo,
        repo_type: repoType,
      });

      const response = await fetch(`/api/codemap?${params.toString()}`);

      if (response.ok) {
        const data = await response.json();
        setCodemapData(data);
      } else if (response.status === 404) {
        // 没有缓存，需要生成
        setError('代码地图尚未生成，请点击"生成代码地图"按钮。');
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `Failed to load codemap: ${response.status}`);
      }
    } catch (err) {
      console.error('Error loading codemap:', err);
      setError(err instanceof Error ? err.message : 'Failed to load codemap');
    } finally {
      setIsLoading(false);
    }
  }, [owner, repo, repoType]);

  // 生成代码地图
  const generateCodemap = useCallback(async () => {
    try {
      setIsGenerating(true);
      setError(null);

      const requestBody: any = {
        repo_url: repoUrl || `https://github.com/${owner}/${repo}`,
        repo_type: repoType,
        options: {
          include_tests: true,
          max_depth: 10,
        },
      };

      if (token) {
        requestBody.token = token;
      }

      const response = await fetch('/api/codemap/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Failed to generate codemap: ${response.status}`);
      }

      const data = await response.json();
      setCodemapData(data);
      setError(null);
    } catch (err) {
      console.error('Error generating codemap:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate codemap');
    } finally {
      setIsGenerating(false);
    }
  }, [owner, repo, repoUrl, repoType, token]);

  // 页面加载时尝试加载缓存
  useEffect(() => {
    loadCachedCodemap();
  }, [loadCachedCodemap]);

  // 处理节点点击
  const handleNodeClick = useCallback(
    (node: CodeNode) => {
      console.log('Node clicked:', node);
      
      // 如果有仓库URL，构造文件跳转链接
      if (codemapData?.metadata.repo_url && node.type === 'file') {
        const fileUrl = `${codemapData.metadata.repo_url}/blob/main/${node.path}`;
        if (node.start_line) {
          window.open(`${fileUrl}#L${node.start_line}`, '_blank');
        } else {
          window.open(fileUrl, '_blank');
        }
      }
    },
    [codemapData]
  );

  // 导出代码地图数据
  const exportCodemap = useCallback(() => {
    if (!codemapData) return;

    const dataStr = JSON.stringify(codemapData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `codemap_${owner}_${repo}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [codemapData, owner, repo]);

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* 顶部导航栏 */}
      <header className="border-b border-[var(--border-color)] bg-[var(--card-bg)]">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href={`/${owner}/${repo}?${searchParams.toString()}`}
                className="flex items-center gap-2 text-[var(--accent-primary)] hover:text-[var(--highlight)] transition-colors"
              >
                <FaArrowLeft className="w-4 h-4" />
                <span>返回 Wiki</span>
              </Link>
              <div className="h-6 w-px bg-[var(--border-color)]" />
              <h1 className="text-xl font-semibold">
                {owner}/{repo} - 代码地图
              </h1>
            </div>

            <div className="flex items-center gap-3">
              {codemapData && (
                <>
                  <button
                    onClick={exportCodemap}
                    className="flex items-center gap-2 px-4 py-2 bg-[var(--background)] border border-[var(--border-color)] rounded-md hover:bg-[var(--accent-primary)]/10 transition-colors"
                    title="导出代码地图"
                  >
                    <FaDownload className="w-4 h-4" />
                    <span className="hidden sm:inline">导出</span>
                  </button>
                  <button
                    onClick={generateCodemap}
                    disabled={isGenerating}
                    className="flex items-center gap-2 px-4 py-2 bg-[var(--accent-primary)] text-white rounded-md hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                    title="重新生成代码地图"
                  >
                    <FaSync className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
                    <span className="hidden sm:inline">
                      {isGenerating ? '生成中...' : '重新生成'}
                    </span>
                  </button>
                </>
              )}
              <ThemeToggle />
            </div>
          </div>

          {/* 元数据信息 */}
          {codemapData && (
            <div className="mt-4 flex flex-wrap gap-4 text-sm text-[var(--muted)]">
              <div>文件: {codemapData.metadata.total_files}</div>
              <div>节点: {codemapData.metadata.node_count}</div>
              <div>关系: {codemapData.metadata.edge_count}</div>
              <div>代码行: {codemapData.metadata.total_lines.toLocaleString()}</div>
              {codemapData.metadata.generated_at && (
                <div>
                  生成时间: {new Date(codemapData.metadata.generated_at).toLocaleString('zh-CN')}
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      {/* 主内容区 */}
      <main className="h-[calc(100vh-8rem)]">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[var(--accent-primary)] mx-auto mb-4"></div>
              <p className="text-lg text-[var(--foreground)]">加载代码地图...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="max-w-md text-center p-6">
              <FaExclamationTriangle className="w-16 h-16 text-[var(--highlight)] mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2 text-[var(--foreground)]">
                {error.includes('尚未生成') ? '代码地图尚未生成' : '加载失败'}
              </h2>
              <p className="text-[var(--muted)] mb-6">{error}</p>
              <button
                onClick={generateCodemap}
                disabled={isGenerating}
                className="px-6 py-3 bg-[var(--accent-primary)] text-white rounded-md hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <>
                    <FaSync className="inline-block w-4 h-4 mr-2 animate-spin" />
                    生成中...
                  </>
                ) : (
                  '生成代码地图'
                )}
              </button>
            </div>
          </div>
        ) : codemapData ? (
          <Codemap data={codemapData} onNodeClick={handleNodeClick} />
        ) : null}
      </main>
    </div>
  );
}

