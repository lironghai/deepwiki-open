import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
// We'll use dynamic import for svg-pan-zoom

// Initialize mermaid with defaults - Japanese aesthetic
mermaid.initialize({
  startOnLoad: true,
  theme: 'neutral',
  securityLevel: 'loose',
  suppressErrorRendering: true,
  logLevel: 'error',
  maxTextSize: 100000, // Increase text size limit
  htmlLabels: true,
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
    nodeSpacing: 60,
    rankSpacing: 60,
    padding: 20,
  },
  themeCSS: `
    /* Japanese aesthetic styles for all diagrams */
    .node rect, .node circle, .node ellipse, .node polygon, .node path {
      fill: #f8f4e6;
      stroke: #d7c4bb;
      stroke-width: 1px;
    }
    .edgePath .path {
      stroke: #9b7cb9;
      stroke-width: 1.5px;
    }
    .edgeLabel {
      background-color: transparent;
      color: #333333;
      p {
        background-color: transparent !important;
      }
    }
    .label {
      color: #333333;
    }
    .cluster rect {
      fill: #f8f4e6;
      stroke: #d7c4bb;
      stroke-width: 1px;
    }

    /* Sequence diagram specific styles */
    .actor {
      fill: #f8f4e6;
      stroke: #d7c4bb;
      stroke-width: 1px;
    }
    text.actor {
      fill: #333333;
      stroke: none;
    }
    .messageText {
      fill: #333333;
      stroke: none;
    }
    .messageLine0, .messageLine1 {
      stroke: #9b7cb9;
    }
    .noteText {
      fill: #333333;
    }

    /* Dark mode overrides - will be applied with data-theme="dark" */
    [data-theme="dark"] .node rect,
    [data-theme="dark"] .node circle,
    [data-theme="dark"] .node ellipse,
    [data-theme="dark"] .node polygon,
    [data-theme="dark"] .node path {
      fill: #222222;
      stroke: #5d4037;
    }
    [data-theme="dark"] .edgePath .path {
      stroke: #9370db;
    }
    [data-theme="dark"] .edgeLabel {
      background-color: transparent;
      color: #f0f0f0;
    }
    [data-theme="dark"] .label {
      color: #f0f0f0;
    }
    [data-theme="dark"] .cluster rect {
      fill: #222222;
      stroke: #5d4037;
    }
    [data-theme="dark"] .flowchart-link {
      stroke: #9370db;
    }

    /* Dark mode sequence diagram overrides */
    [data-theme="dark"] .actor {
      fill: #222222;
      stroke: #5d4037;
    }
    [data-theme="dark"] text.actor {
      fill: #f0f0f0;
      stroke: none;
    }
    [data-theme="dark"] .messageText {
      fill: #f0f0f0;
      stroke: none;
      font-weight: 500;
    }
    [data-theme="dark"] .messageLine0, [data-theme="dark"] .messageLine1 {
      stroke: #9370db;
      stroke-width: 1.5px;
    }
    [data-theme="dark"] .noteText {
      fill: #f0f0f0;
    }
    /* Additional styles for sequence diagram text */
    [data-theme="dark"] #sequenceNumber {
      fill: #f0f0f0;
    }
    [data-theme="dark"] text.sequenceText {
      fill: #f0f0f0;
      font-weight: 500;
    }
    [data-theme="dark"] text.loopText, [data-theme="dark"] text.loopText tspan {
      fill: #f0f0f0;
    }
    /* Add a subtle background to message text for better readability */
    [data-theme="dark"] .messageText, [data-theme="dark"] text.sequenceText {
      paint-order: stroke;
      stroke: #1a1a1a;
      stroke-width: 2px;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    /* Force text elements to be properly colored */
    text[text-anchor][dominant-baseline],
    text[text-anchor][alignment-baseline],
    .nodeLabel,
    .edgeLabel,
    .label,
    text {
      fill: #777 !important;
    }

    [data-theme="dark"] text[text-anchor][dominant-baseline],
    [data-theme="dark"] text[text-anchor][alignment-baseline],
    [data-theme="dark"] .nodeLabel,
    [data-theme="dark"] .edgeLabel,
    [data-theme="dark"] .label,
    [data-theme="dark"] text {
      fill: #f0f0f0 !important;
    }

    /* Add clickable element styles with subtle transitions */
    .clickable {
      transition: all 0.3s ease;
    }
    .clickable:hover {
      transform: scale(1.03);
      cursor: pointer;
    }
    .clickable:hover > * {
      filter: brightness(0.95);
    }
  `,
  fontFamily: 'var(--font-geist-sans), var(--font-serif-jp), sans-serif',
  fontSize: 12,
});

interface MermaidProps {
  chart: string;
  className?: string;
  zoomingEnabled?: boolean;
  showCodeToggle?: boolean; // New prop to enable code/diagram toggle
}

// Full screen modal component for the diagram
const FullScreenModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  onCopy: () => void;
}> = ({ isOpen, onClose, children, onCopy }) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  // Handle click on backdrop to close (not on modal content)
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Reset zoom when modal opens
  useEffect(() => {
    if (isOpen) {
      setZoom(1);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className="bg-[var(--card-bg)] rounded-lg shadow-custom w-[95vw] h-[95vh] max-w-[1800px] overflow-hidden flex flex-col card-japanese"
      >
        {/* Modal header with controls */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
          <div className="font-medium text-[var(--foreground)] font-serif">图表全屏</div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
                className="text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 p-2 rounded-md border border-[var(--border-color)] transition-colors"
                aria-label="Zoom out"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
              </button>
              <span className="text-sm text-[var(--muted)]">{Math.round(zoom * 100)}%</span>
              <button
                onClick={() => setZoom(Math.min(2, zoom + 0.1))}
                className="text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 p-2 rounded-md border border-[var(--border-color)] transition-colors"
                aria-label="Zoom in"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  <line x1="11" y1="8" x2="11" y2="14"></line>
                  <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
              </button>
              <button
                onClick={() => setZoom(1)}
                className="text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 p-2 rounded-md border border-[var(--border-color)] transition-colors"
                aria-label="Reset zoom"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path>
                  <path d="M21 3v5h-5"></path>
                </svg>
              </button>
            </div>
            <button
              onClick={onCopy}
              className="text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 p-2 rounded-md border border-[var(--border-color)] transition-colors"
              aria-label="Copy diagram code"
              title="复制图表代码"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
            <button
              onClick={onClose}
              className="text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 p-2 rounded-md border border-[var(--border-color)] transition-colors"
              aria-label="Close"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        {/* Modal content with zoom */}
        <div className="overflow-auto flex-1 bg-white dark:bg-gray-900">
          <div className="min-h-full p-6 flex items-center justify-center">
            <div
              style={{
                transform: `scale(${zoom})`,
                transformOrigin: 'center center',
                transition: 'transform 0.3s ease-out'
              }}
            >
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const Mermaid: React.FC<MermaidProps> = ({ chart, className = '', zoomingEnabled = false, showCodeToggle = true }) => {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showCode, setShowCode] = useState(false); // New state for toggling between diagram and code
  const mermaidRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(`mermaid-${Math.random().toString(36).substring(2, 9)}`);
  const isDarkModeRef = useRef(
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  );

  // Initialize pan-zoom functionality when SVG is rendered
  useEffect(() => {
    if (svg && zoomingEnabled && containerRef.current) {
      const initializePanZoom = async () => {
        const svgElement = containerRef.current?.querySelector("svg");
        if (svgElement) {
          // Remove any max-width constraints
          svgElement.style.maxWidth = "none";
          svgElement.style.width = "100%";
          svgElement.style.height = "100%";

          try {
            // Dynamically import svg-pan-zoom only when needed in the browser
            const svgPanZoom = (await import("svg-pan-zoom")).default;

            svgPanZoom(svgElement, {
              zoomEnabled: true,
              controlIconsEnabled: true,
              fit: true,
              center: true,
              minZoom: 0.1,
              maxZoom: 10,
              zoomScaleSensitivity: 0.3,
            });
          } catch (error) {
            console.error("Failed to load svg-pan-zoom:", error);
          }
        }
      };

      // Wait for the SVG to be rendered
      setTimeout(() => {
        void initializePanZoom();
      }, 100);
    }
  }, [svg, zoomingEnabled]);

  useEffect(() => {
    if (!chart) return;

    let isMounted = true;

    const renderChart = async () => {
      if (!isMounted) return;

      try {
        setError(null);
        setSvg('');

        // 清理可能导致解析错误的文本
        // 移除源代码引用格式（如 Sources: [file.ext]()）
        let cleanedChart = chart
          // === 第一步：移除所有Markdown链接和引用格式 ===
          // 移除 Sources: [filename]() 格式的引用
          .replace(/Sources:\s*\[[^\]]+\]\([^\)]*\)/gi, '')
          // 移除单独的 Markdown 链接格式（在 Mermaid 代码块中），保留链接文本
          .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
          // 移除可能的中文括号和特殊字符导致的解析问题
          .replace(/[（(]Sources:[^）)]+[）)]/g, '')
          // 移除其他可能的引用格式：Sources: filename.ext 或 [Sources: ...]
          .replace(/^\s*Sources?:\s*.*$/gmi, '')
          .replace(/\[Sources?:\s*[^\]]+\]/gi, '')

          // === 第二步：修复序列图常见语法错误 ===
          // 修复: autonumber 后面跟逗号和方括号 (autonumber    , [text] description)
          .replace(/(\s*autonumber\s*),\s*\[.*$/gm, '$1')
          // 修复: autonumber 后面跟任何逗号和额外内容
          .replace(/(\s*autonumber\s*),.*$/gm, '$1')
          // 修复: participant 后面跟逗号 (participant A, [text])
          .replace(/(participant\s+[A-Za-z0-9_]+(?:\s+as\s+[A-Za-z0-9_]+)?)\s*,\s*\[.*$/gm, '$1')
          // 修复: participant 后面跟逗号和任何内容
          .replace(/(participant\s+[A-Za-z0-9_]+(?:\s+as\s+[A-Za-z0-9_]+)?)\s*,.*$/gm, '$1')
          // 修复: 箭头后面跟逗号和方括号 (->>+    , [text])
          .replace(/(->>[\+\-]?[^:]*):([^,]*),\s*\[[^\]]*\](.*)$/gm, '$1:$2')
          // 更简单的箭头修复：移除箭头后冒号之后的 ", [...]" 模式
          .replace(/(->>[\+\-]?\s*\w+\s*:\s*[^,\n]*),\s*\[[^\]]*\]/g, '$1')
          // 修复: 箭头标签中的逗号（保留冒号后的第一个逗号之前的内容）
          .replace(/(->>?[\+\-]?\s*\w+\s*:\s*[^,\n]*),\s*([^,\n]*)/g, '$1 $2')
          // 修复: 任何Mermaid关键字后跟 ", [" 的错误模式
          .replace(/(activate|deactivate|loop|alt|opt|par|and|else|end|box|note|rect|critical|break)\s*,\s*\[.*$/gmi, '$1')
          // 修复: 关键字后跟逗号和任何内容
          .replace(/(activate|deactivate|loop|alt|opt|par|and|else|end|box|note|rect|critical|break)\s*,.*$/gmi, '$1')

          // === 第三步：修复箭头语法错误 ===
          // 修复: 参与者名称和箭头之间的逗号
          .replace(/([A-Za-z0-9_]+)\s*,\s*(->>?[\+\-]?)/g, '$1$2')
          // 修复: 箭头前的逗号（在参与者名和箭头之间）
          .replace(/([A-Za-z0-9_]+)\s*,\s*(->|--|->>|-->>|->x|-->>x|-\)|--\))/g, '$1$2')
          // 修复: 箭头标签中的多个逗号（只保留第一个冒号后的内容，移除后续逗号）
          .replace(/(->>?[\+\-]?\s*\w+\s*:\s*[^:,\n]+),\s*([^:\n]+)/g, '$1 $2')

          // === 第四步：清理流程图和类图的常见错误 ===
          // 修复: 流程图节点定义中的逗号问题
          .replace(/([A-Za-z0-9_]+)\s*\[([^\]]*)\]\s*,/g, '$1[$2]')
          // 修复: 类图关系中的逗号问题
          .replace(/([A-Za-z0-9_]+)\s*(-->|<\|--|<\|\.\.|--|\*--|o--)\s*([A-Za-z0-9_]+)\s*,/g, '$1$2$3')
          // 修复: ER图中的逗号问题
          .replace(/([A-Za-z0-9_]+)\s*\{\s*([^}]*)\s*\}\s*,/g, '$1{$2}')

          // === 第五步：清理孤立的方括号残留 ===
          // 移除孤立的右方括号及其后面的文本
          .replace(/^\s*[^\s\w-]+\].*/gm, '')
          // 移除包含孤立方括号的整行
          .replace(/^\s*\w+\]\s+.*/gm, '')
          // 移除行首的孤立左方括号
          .replace(/^\s*\[[^\]]*$/gm, '')

          // === 第六步：清理方括号内的无效内容 ===
          // 如果方括号在行首（缺少前置内容），移除整行
          .replace(/^\s*,?\s*\[.*?\].*$/gm, '')
          // 修复孤立的方括号（前面没有有效内容）
          .replace(/,\s*\[[^\]]+\]/g, '')
          // 移除方括号内的Markdown链接
          .replace(/\[([^\]]*)\[([^\]]+)\]\([^\)]+\)([^\]]*)\]/g, '[$1$2$3]')

          // === 第七步：清理无效的逗号 ===
          // 移除行尾的孤立逗号
          .replace(/,\s*$/gm, '')
          // 移除行首的逗号
          .replace(/^\s*,/gm, '')
          // 移除关键字后的逗号（在行尾）
          .replace(/(autonumber|activate|deactivate|end|else|and)\s*,(\s*$)/gmi, '$1$2')

          // === 第八步：清理其他无效字符和格式 ===
          // 移除Markdown格式标记（在Mermaid代码块中不应该存在）
          .replace(/\*\*([^*]+)\*\*/g, '$1') // 移除粗体
          .replace(/\*([^*]+)\*/g, '$1') // 移除斜体
          .replace(/`([^`]+)`/g, '$1') // 移除行内代码
          // 移除HTML标签（如果有）
          .replace(/<[^>]+>/g, '')
          // 规范化空白字符（多个空格变为单个空格，但保留换行）
          .replace(/[ \t]+/g, ' ')
          // 移除行尾空格
          .replace(/[ \t]+$/gm, '')

          // === 最终清理 ===
          // 移除空行或只有空白的行
          .replace(/^\s*$/gm, '')
          // 清理多余的空行（最多保留两个连续空行）
          .replace(/\n{3,}/g, '\n\n')
          // 移除开头的空行
          .replace(/^\n+/, '')
          // 移除结尾的空行
          .replace(/\n+$/, '')
          .trim();

        // Render the chart
        const { svg: renderedSvg } = await mermaid.render(idRef.current, cleanedChart);

        if (!isMounted) return;

        let processedSvg = renderedSvg;
        if (isDarkModeRef.current) {
          processedSvg = processedSvg.replace('<svg ', '<svg data-theme="dark" ');
        }

        setSvg(processedSvg);

        // Call mermaid.contentLoaded to ensure proper initialization
        setTimeout(() => {
          mermaid.contentLoaded();
        }, 50);
      } catch (err) {
        console.error('Mermaid rendering error:', err);

        const errorMessage = err instanceof Error ? err.message : String(err);

        // 尝试使用更激进的清理策略重试一次
        if (!isMounted) return;

        try {
          console.log('Attempting aggressive cleanup and retry...');

          // 更激进的清理：移除所有可能的问题字符
          const aggressivelyCleanedChart = cleanedChart
            // 移除所有方括号内容（可能是错误的标签）
            .replace(/\[[^\]]*\]/g, '')
            // 移除所有孤立的逗号
            .replace(/\s*,\s*/g, ' ')
            // 规范化空白字符
            .replace(/\s+/g, ' ')
            .replace(/\n\s+/g, '\n')
            // 清理空行
            .replace(/\n{2,}/g, '\n')
            .trim();

          const { svg: retryRenderedSvg } = await mermaid.render(idRef.current + '-retry', aggressivelyCleanedChart);

          if (!isMounted) return;

          console.log('Retry succeeded with aggressive cleanup');
          let processedSvg = retryRenderedSvg;
          if (isDarkModeRef.current) {
            processedSvg = processedSvg.replace('<svg ', '<svg data-theme="dark" ');
          }
          setSvg(processedSvg);

          setTimeout(() => {
            mermaid.contentLoaded();
          }, 50);
          return; // 重试成功，直接返回
        } catch (retryErr) {
          console.error('Retry also failed:', retryErr);
        }

        // 所有尝试都失败，显示友好的错误信息
        if (isMounted) {
          // 解析错误类型并提供帮助
          let friendlyError = '图表语法错误';
          let helpText = '请检查图表内容。';

          if (errorMessage.includes('Parse error')) {
            const match = errorMessage.match(/line (\d+)/);
            if (match) {
              const lineNum = match[1];
              friendlyError = `图表语法错误（第 ${lineNum} 行）`;
              helpText = 'Mermaid 语法解析失败，可能是 AI 生成的代码包含不支持的格式。已尝试自动修复但未成功。';
            }
          } else if (errorMessage.includes('Expecting')) {
            friendlyError = '图表语法错误：不期望的字符或格式';
            helpText = '可能包含了 Mermaid 不支持的语法或字符（如逗号、方括号等）。';
          }

          setError(friendlyError);

          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = `
              <div class="text-red-500 dark:text-red-400 text-xs mb-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-md border border-red-200 dark:border-red-800">
                <div class="flex items-start gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <div class="flex-1">
                    <strong class="font-semibold">${friendlyError}</strong>
                    <p class="mt-1 text-gray-600 dark:text-gray-400">${helpText}</p>
                  </div>
                </div>
              </div>
              <details class="mt-2">
                <summary class="text-xs cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors">
                  🔍 查看详细信息
                </summary>
                <div class="mt-2 space-y-2">
                  <div>
                    <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">错误信息:</div>
                    <pre class="text-xs overflow-auto p-2 bg-red-100 dark:bg-red-900/30 rounded text-red-700 dark:text-red-300">${errorMessage}</pre>
                  </div>
                  <div>
                    <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">原始图表代码:</div>
                    <pre class="text-xs overflow-auto p-2 bg-gray-100 dark:bg-gray-800 rounded mt-1 max-h-40">${chart.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                  </div>
                </div>
              </details>
            `;
          }
        }
      }
    };

    // 使用 try-catch 包装，确保错误不会导致整个应用崩溃
    try {
      renderChart();
    } catch (err) {
      console.error('Fatal error in Mermaid component:', err);
      if (isMounted) {
        setError('图表组件发生严重错误，请刷新页面重试。');
      }
    }

    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleFullscreenClick = () => {
    if (!error && svg) {
      setIsFullscreen(true);
    }
  };

  const handleCopyDiagram = async () => {
    try {
      await navigator.clipboard.writeText(chart);
    } catch (err) {
      console.error('Failed to copy diagram code:', err);
    }
  };

  // Loading state
  if (!svg && !error) {
    return (
      <div className={`flex justify-center items-center p-4 ${className}`}>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-[var(--accent-primary)]/70 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-[var(--accent-primary)]/70 rounded-full animate-pulse delay-75"></div>
          <div className="w-2 h-2 bg-[var(--accent-primary)]/70 rounded-full animate-pulse delay-150"></div>
          <span className="text-[var(--muted)] text-xs ml-2 font-serif">図表を描画中...</span>
        </div>
      </div>
    );
  }

  // Main render with tabs (works for both success and error states)
  return (
    <>
      <div
        ref={containerRef}
        className={`w-full max-w-full bg-[var(--card-bg)] rounded-lg border border-[var(--border-color)] overflow-hidden ${zoomingEnabled ? "h-[600px] p-4" : ""}`}
      >
        {/* Tab navigation - always show if showCodeToggle is enabled */}
        {showCodeToggle && (
          <div className="flex items-center gap-1 px-2 pt-3 pb-2 bg-[var(--background)] border-b border-[var(--border-color)]">
            <button
              onClick={() => setShowCode(false)}
              className={`relative px-4 py-2 text-sm font-medium transition-all duration-200 rounded-t-lg ${
                !showCode
                  ? 'text-[var(--accent-primary)] bg-[var(--card-bg)] shadow-sm'
                  : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background)]/50'
              }`}
            >
              <span className="relative z-10">图表</span>
              {!showCode && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent-primary)] rounded-full"></div>
              )}
            </button>
            <button
              onClick={() => setShowCode(true)}
              className={`relative px-4 py-2 text-sm font-medium transition-all duration-200 rounded-t-lg ${
                showCode
                  ? 'text-[var(--accent-primary)] bg-[var(--card-bg)] shadow-sm'
                  : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background)]/50'
              }`}
            >
              <span className="relative z-10">代码</span>
              {showCode && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent-primary)] rounded-full"></div>
              )}
            </button>
          </div>
        )}

        {/* Content area */}
        <div className="p-4 bg-[var(--card-bg)]">
          {showCode ? (
            /* Code view */
            <div className="relative">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs text-[var(--muted)] font-semibold">Mermaid源代码</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(chart);
                    }}
                    className="text-xs px-3 py-1.5 rounded-md bg-[var(--background)] border border-[var(--border-color)] text-[var(--foreground)] hover:bg-[var(--accent-primary)]/10 hover:border-[var(--accent-primary)]/30 transition-all duration-200"
                    title="复制代码"
                  >
                    复制
                  </button>
                </div>
              </div>
              <div className="bg-[var(--background)] border border-[var(--border-color)] rounded-lg p-4 overflow-auto max-h-[600px]">
                <pre className="text-xs text-[var(--foreground)] whitespace-pre-wrap break-words font-mono leading-relaxed">
                  {chart}
                </pre>
              </div>
            </div>
          ) : (
            /* Diagram view or Error view */
            <div className="relative">
              {error ? (
                /* Error state - show error message */
                <div className="flex flex-col items-center justify-center py-12 px-4 min-h-[200px]">
                  <div className="mb-4">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="text-center w-full">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">渲染失败</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">图表语法错误，无法渲染</p>
                    <div ref={mermaidRef} className="text-xs text-left max-w-2xl mx-auto"></div>
                  </div>
                </div>
              ) : (
                /* Success state - show diagram */
                <div
                  className={`relative group ${zoomingEnabled ? "h-full rounded-lg border-2 border-black" : ""}`}
                >
                  <div
                    className={`flex justify-center overflow-auto text-center my-2 rounded-md ${className} ${zoomingEnabled ? "h-full" : ""}`}
                    dangerouslySetInnerHTML={{ __html: svg }}
                  />

                  {!zoomingEnabled && (
                    <div className="absolute top-2 right-2 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <button
                        onClick={handleCopyDiagram}
                        className="bg-gray-700/90 dark:bg-gray-900/90 hover:bg-gray-600 dark:hover:bg-gray-800 text-white p-2 rounded-md transition-colors duration-200 flex items-center gap-1.5 text-xs shadow-md"
                        title="复制图表代码"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <span>复制</span>
                      </button>
                      <button
                        onClick={handleFullscreenClick}
                        className="bg-gray-700/90 dark:bg-gray-900/90 hover:bg-gray-600 dark:hover:bg-gray-800 text-white p-2 rounded-md transition-colors duration-200 flex items-center gap-1.5 text-xs shadow-md"
                        title="全屏查看"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
                        </svg>
                        <span>全屏</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen modal - only for successful renders */}
      {!zoomingEnabled && !showCode && !error && svg && (
        <FullScreenModal
          isOpen={isFullscreen}
          onClose={() => setIsFullscreen(false)}
          onCopy={handleCopyDiagram}
        >
          <div
            className="flex items-center justify-center"
            style={{
              width: 'auto',
              height: 'auto',
              maxWidth: '100%',
              maxHeight: '100%'
            }}
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </FullScreenModal>
      )}
    </>
  );
};



export default Mermaid;