'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, usePathname, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { FaArrowLeft, FaExclamationTriangle } from 'react-icons/fa';
import ThemeToggle from '@/components/theme-toggle';
import { buildGitNexusPaths } from '@/lib/gitnexus-url';
import { seedGitNexusLLMSettings } from '@/lib/gitnexus-settings';

/**
 * 深度代码图谱页：使用官方「本地后端模式」。
 * - 后端：gitnexus serve（容器内 3001），由 Next 转发到同源 /gitnexus。
 * - 前端：官方 gitnexus-web 构建产物放在 /gitnexus-app/，通过 ?server=<同源>/gitnexus 连接（见 GitNexus README Local Backend Mode）。
 */

export default function GitNexusCodemapPage() {
  const params = useParams();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  
  const owner = params.owner as string;
  const repo = params.repo as string;
  
  const [iframeSrc, setIframeSrc] = useState<string>('');
  const [isIframeLoading, setIsIframeLoading] = useState(true);
  const [iframeError, setIframeError] = useState(false);

  const gitNexusPaths = useMemo(
    () =>
      buildGitNexusPaths({
        origin: typeof window === 'undefined' ? '' : window.location.origin,
        pathname,
        owner,
        repo,
      }),
    [owner, pathname, repo]
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    seedGitNexusLLMSettings({
      apiKey: process.env.NEXT_PUBLIC_GITNEXUS_DEFAULT_OPENAI_API_KEY || '',
      baseUrl: process.env.NEXT_PUBLIC_GITNEXUS_DEFAULT_OPENAI_BASE_URL || '',
      model: process.env.NEXT_PUBLIC_GITNEXUS_DEFAULT_OPENAI_MODEL || 'qwen-plus',
    });
    setIframeSrc(gitNexusPaths.iframeSrc);
  }, [gitNexusPaths]);

  return (
    <div className="flex flex-col h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden">
      <header className="flex-shrink-0 border-b border-[var(--border-color)] bg-[var(--card-bg)] relative z-10">
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
                {owner}/{repo} - 深度代码图谱 (GitNexus 本地后端模式)
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full h-full relative">
        {isIframeLoading && !iframeError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[var(--background)] z-0">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[var(--accent-primary)] mx-auto mb-4" />
            <p className="text-lg text-[var(--foreground)]">正在加载 GitNexus 图谱（本地后端模式）...</p>
          </div>
        )}
        {iframeError ? (
          <div className="flex items-center justify-center h-full">
            <div className="max-w-md text-center p-6">
              <FaExclamationTriangle className="w-16 h-16 text-[var(--highlight)] mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2 text-[var(--foreground)]">无法加载图谱</h2>
              <p className="text-[var(--muted)] mb-6">
                请确保已构建并部署 gitnexus-web 至 {gitNexusPaths.appBasePath}，且 gitnexus serve 已启动（由 {gitNexusPaths.prefix || '/'}
                gitnexus 转发）。
              </p>
              <button
                type="button"
                onClick={() => {
                  setIframeError(false);
                  setIsIframeLoading(true);
                  const iframe = document.getElementById('gitnexus-iframe') as HTMLIFrameElement;
                  if (iframe) iframe.src = iframe.src;
                }}
                className="px-6 py-3 bg-[var(--accent-primary)] text-white rounded-md hover:opacity-90 transition-opacity"
              >
                重试
              </button>
            </div>
          </div>
        ) : iframeSrc ? (
          <iframe
            id="gitnexus-iframe"
            src={iframeSrc}
            className="w-full h-full border-0"
            onLoad={() => setIsIframeLoading(false)}
            onError={() => {
              setIsIframeLoading(false);
              setIframeError(true);
            }}
            allow="fullscreen"
          />
        ) : null}
      </main>
    </div>
  );
}
