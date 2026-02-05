import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
// We'll use dynamic import for svg-pan-zoom

// Initialize mermaid with light purple theme - matching the screenshot style
mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  securityLevel: 'loose',
  suppressErrorRendering: true,
  logLevel: 'error',
  maxTextSize: 100000,
  htmlLabels: true,
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
    nodeSpacing: 60,
    rankSpacing: 60,
    padding: 20,
  },
  sequence: {
    actorMargin: 80,
    boxMargin: 10,
    boxTextMargin: 5,
    noteMargin: 10,
    messageMargin: 35,
    mirrorActors: true,
    bottomMarginAdj: 1,
    useMaxWidth: true,
    rightAngles: false,
    showSequenceNumbers: false,
  },
  themeVariables: {
    // Light purple theme colors
    primaryColor: '#f3e8ff',
    primaryBorderColor: '#a855f7',
    primaryTextColor: '#581c87',
    secondaryColor: '#fef3c7',
    secondaryBorderColor: '#f59e0b',
    secondaryTextColor: '#92400e',
    tertiaryColor: '#ecfdf5',
    tertiaryBorderColor: '#10b981',
    tertiaryTextColor: '#065f46',
    // Sequence diagram colors
    actorBkg: '#f3e8ff',
    actorBorder: '#a855f7',
    actorTextColor: '#581c87',
    actorLineColor: '#a855f7',
    signalColor: '#a855f7',
    signalTextColor: '#374151',
    labelBoxBkgColor: '#fef9c3',
    labelBoxBorderColor: '#facc15',
    labelTextColor: '#713f12',
    loopTextColor: '#374151',
    noteBkgColor: '#fef9c3',
    noteBorderColor: '#facc15',
    noteTextColor: '#713f12',
    // General
    lineColor: '#a855f7',
    textColor: '#374151',
    mainBkg: '#ffffff',
    background: '#ffffff',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  themeCSS: `
    /* Light purple theme for diagrams */
    .node rect, .node circle, .node ellipse, .node polygon, .node path {
      fill: #f3e8ff !important;
      stroke: #a855f7 !important;
      stroke-width: 2px !important;
    }

    .edgePath .path {
      stroke: #a855f7 !important;
      stroke-width: 1.5px !important;
    }

    .edgeLabel {
      background-color: #ffffff !important;
      color: #374151 !important;
    }

    .label {
      color: #374151 !important;
      font-weight: 500 !important;
    }

    .cluster rect {
      fill: #faf5ff !important;
      stroke: #c084fc !important;
      stroke-width: 1.5px !important;
    }

    /* Sequence diagram styles */
    .actor {
      fill: #f3e8ff !important;
      stroke: #a855f7 !important;
      stroke-width: 2px !important;
    }

    .actor-line {
      stroke: #a855f7 !important;
      stroke-width: 1px !important;
      stroke-dasharray: 3, 3 !important;
    }

    text.actor > tspan {
      fill: #581c87 !important;
      font-weight: 600 !important;
    }

    .messageText {
      fill: #374151 !important;
      font-weight: 500 !important;
    }

    .messageLine0, .messageLine1 {
      stroke: #a855f7 !important;
      stroke-width: 1.5px !important;
    }

    .noteText {
      fill: #713f12 !important;
    }

    .note {
      fill: #fef9c3 !important;
      stroke: #facc15 !important;
    }

    /* Loop and alt boxes */
    .loopText, .loopText > tspan {
      fill: #374151 !important;
    }

    .labelBox {
      fill: #fef9c3 !important;
      stroke: #facc15 !important;
    }

    .labelText, .labelText > tspan {
      fill: #713f12 !important;
    }

    /* Arrow markers */
    marker {
      fill: #a855f7 !important;
    }

    #arrowhead path {
      fill: #a855f7 !important;
      stroke: #a855f7 !important;
    }

    /* Text styling */
    .nodeLabel, .edgeLabel, text {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Flowchart specific */
    .flowchart-link {
      stroke: #a855f7 !important;
    }

    /* Class diagram */
    .classGroup .title {
      fill: #581c87 !important;
    }

    /* State diagram */
    .statediagram-state rect {
      fill: #f3e8ff !important;
      stroke: #a855f7 !important;
    }

    /* ER diagram */
    .er.entityBox {
      fill: #f3e8ff !important;
      stroke: #a855f7 !important;
    }

    /* Gantt chart */
    .section0, .section2 {
      fill: #f3e8ff !important;
    }

    .section1, .section3 {
      fill: #fef3c7 !important;
    }

    .task0, .task2 {
      fill: #c084fc !important;
    }

    .task1, .task3 {
      fill: #fbbf24 !important;
    }
  `,
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  fontSize: 14,
});

interface MermaidProps {
  chart: string;
  className?: string;
  zoomingEnabled?: boolean;
}

// Download SVG as file
const downloadSvg = (svgContent: string, filename: string = 'diagram.svg') => {
  const blob = new Blob([svgContent], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

// Download SVG as PNG
const downloadPng = async (svgElement: SVGSVGElement, filename: string = 'diagram.png') => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const svgData = new XMLSerializer().serializeToString(svgElement);
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);

  const img = new Image();
  img.onload = () => {
    canvas.width = img.width * 2;
    canvas.height = img.height * 2;
    ctx.scale(2, 2);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    canvas.toBlob((blob) => {
      if (blob) {
        const pngUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(pngUrl);
      }
    }, 'image/png');

    URL.revokeObjectURL(url);
  };
  img.src = url;
};

// Full screen modal component for the diagram with auto-fit
const FullScreenModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}> = ({ isOpen, onClose, children }) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [fitZoom, setFitZoom] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Calculate initial fit-to-screen zoom
  useEffect(() => {
    if (!isOpen || !contentRef.current) return;

    const calculateFitZoom = () => {
      const svgElement = contentRef.current?.querySelector('svg');
      if (!svgElement) return;

      const containerWidth = contentRef.current?.clientWidth || 0;
      const containerHeight = contentRef.current?.clientHeight || 0;
      const svgWidth = svgElement.viewBox?.baseVal?.width || svgElement.clientWidth || 800;
      const svgHeight = svgElement.viewBox?.baseVal?.height || svgElement.clientHeight || 600;

      // Calculate zoom to fit with 20% padding
      const widthRatio = (containerWidth * 0.9) / svgWidth;
      const heightRatio = (containerHeight * 0.9) / svgHeight;
      const initialZoom = Math.min(widthRatio, heightRatio, 3); // Max 3x zoom

      setFitZoom(initialZoom);
      setZoom(initialZoom);
    };

    // Wait for content to render
    setTimeout(calculateFitZoom, 100);

    // Recalculate on window resize
    window.addEventListener('resize', calculateFitZoom);
    return () => window.removeEventListener('resize', calculateFitZoom);
  }, [isOpen]);

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

  // Handle click outside to close
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen, onClose]);

  // Reset zoom and pan when modal opens
  useEffect(() => {
    if (isOpen) {
      setPanPosition({ x: 0, y: 0 });
    }
  }, [isOpen]);

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom > 1) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - panPosition.x, y: e.clientY - panPosition.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPanPosition({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div
        ref={modalRef}
        className="bg-white rounded-xl shadow-2xl max-w-[95vw] max-h-[95vh] w-full overflow-hidden flex flex-col border border-gray-200"
      >
        {/* Modal header with controls - light style */}
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-b from-gray-50 to-gray-100 border-b border-gray-200">
          <div className="font-medium text-gray-700 flex items-center gap-2">
            <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
            <span>图表查看器</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-white rounded-lg px-2 py-1 border border-gray-200">
              <button
                onClick={() => {
                  setZoom(Math.max(0.5, zoom - 0.2));
                  setPanPosition({ x: 0, y: 0 });
                }}
                className="text-gray-500 hover:text-gray-700 hover:bg-gray-100 p-1.5 rounded transition-all"
                aria-label="缩小"
                title="缩小"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
              </button>
              <span className="text-sm text-gray-600 font-medium min-w-[50px] text-center">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={() => {
                  setZoom(Math.min(5, zoom + 0.2));
                  setPanPosition({ x: 0, y: 0 });
                }}
                className="text-gray-500 hover:text-gray-700 hover:bg-gray-100 p-1.5 rounded transition-all"
                aria-label="放大"
                title="放大"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  <line x1="11" y1="8" x2="11" y2="14"></line>
                  <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
              </button>
              <div className="w-px h-4 bg-gray-300 mx-1"></div>
              <button
                onClick={() => {
                  setZoom(fitZoom);
                  setPanPosition({ x: 0, y: 0 });
                }}
                className="text-gray-500 hover:text-gray-700 hover:bg-gray-100 p-1.5 rounded transition-all"
                aria-label="适应屏幕"
                title="适应屏幕"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
                </svg>
              </button>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 hover:bg-gray-100 p-2 rounded-lg border border-gray-200 transition-all"
              aria-label="关闭"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        {/* Modal content with adaptive zoom and pan */}
        <div
          ref={contentRef}
          className="overflow-hidden flex-1 flex items-center justify-center bg-white relative"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{
            cursor: isPanning ? 'grabbing' : zoom > 1 ? 'grab' : 'default',
          }}
        >
          {/* Subtle grid background */}
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage: `
                linear-gradient(rgba(168, 85, 247, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(168, 85, 247, 0.05) 1px, transparent 1px)
              `,
              backgroundSize: '40px 40px',
            }}
          ></div>

          <div
            className="relative z-10"
            style={{
              transform: `scale(${zoom}) translate(${panPosition.x / zoom}px, ${panPosition.y / zoom}px)`,
              transformOrigin: 'center center',
              transition: isPanning ? 'none' : 'transform 0.3s ease-out',
            }}
          >
            {children}
          </div>

          {/* Zoom hint */}
          {zoom > 1 && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800/80 text-white text-xs px-3 py-1.5 rounded-full backdrop-blur-sm">
              拖拽平移
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const Mermaid: React.FC<MermaidProps> = ({ chart, className = '', zoomingEnabled = false }) => {
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState<'diagram' | 'code'>('diagram');
  const [zoom, setZoom] = useState(1);
  const mermaidRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const diagramContainerRef = useRef<HTMLDivElement>(null);
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

        // Render the chart directly without preprocessing
        const { svg: renderedSvg } = await mermaid.render(idRef.current, chart);

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

        if (isMounted) {
          setError(`Failed to render diagram: ${errorMessage}`);

          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = `
              <div class="text-red-500 dark:text-red-400 text-xs mb-1">Syntax error in diagram</div>
              <pre class="text-xs overflow-auto p-2 bg-gray-100 dark:bg-gray-800 rounded">${chart}</pre>
            `;
          }
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleDiagramClick = () => {
    if (!error && svg) {
      setIsFullscreen(true);
    }
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleDownload = () => {
    const svgElement = diagramContainerRef.current?.querySelector('svg');
    if (svgElement) {
      downloadPng(svgElement, 'diagram.png');
    }
  };

  const copyCode = () => {
    navigator.clipboard.writeText(chart);
  };

  if (error) {
    return (
      <div className={`border border-gray-200 rounded-lg overflow-hidden bg-white ${className}`}>
        {/* Error toolbar */}
        <div className="flex items-center justify-between px-3 py-2 bg-gradient-to-b from-gray-50 to-gray-100 border-b border-gray-200">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setViewMode('diagram')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-all ${
                viewMode === 'diagram'
                  ? 'text-gray-700 bg-white border border-gray-200 shadow-sm'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              图表
            </button>
            <button
              onClick={() => setViewMode('code')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-all ${
                viewMode === 'code'
                  ? 'text-gray-700 bg-white border border-gray-200 shadow-sm'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              代码
            </button>
          </div>
          {viewMode === 'code' && (
            <div className="flex items-center gap-1">
              <button
                onClick={copyCode}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="复制代码"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
          )}
        </div>
        <div className="p-5">
          {viewMode === 'diagram' ? (
            <>
              <div className="flex items-center mb-3">
                <div className="text-red-500 text-sm font-medium flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  图表渲染错误
                </div>
              </div>
              <div ref={mermaidRef} className="text-xs overflow-auto font-mono"></div>
              <div className="mt-3 text-sm text-gray-500">
                图表语法存在错误，无法渲染。
              </div>
            </>
          ) : (
            <div className="overflow-auto bg-gray-50" style={{ maxHeight: '500px' }}>
              <pre className="p-4 text-sm font-mono text-gray-700 whitespace-pre-wrap break-words">
                {chart}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className={`border border-gray-200 rounded-lg overflow-hidden bg-white ${className}`}>
        {/* Loading toolbar */}
        <div className="flex items-center justify-between px-3 py-2 bg-gradient-to-b from-gray-50 to-gray-100 border-b border-gray-200">
          <div className="flex items-center gap-1">
            <button className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white rounded border border-gray-200 shadow-sm">
              图表
            </button>
            <button className="px-3 py-1.5 text-sm font-medium text-gray-400">
              代码
            </button>
          </div>
        </div>
        <div className="flex justify-center items-center p-8">
          <div className="flex flex-col items-center space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span className="text-gray-500 text-sm">正在渲染图表...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div
        ref={containerRef}
        className={`w-full max-w-full ${zoomingEnabled ? "h-[600px]" : ""}`}
      >
        {/* Main container with light theme */}
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
          {/* Toolbar - light gray gradient */}
          <div className="flex items-center justify-between px-3 py-2 bg-gradient-to-b from-gray-50 to-gray-100/80 border-b border-gray-200">
            {/* Left side - View toggle */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setViewMode('diagram')}
                className={`px-3 py-1.5 text-sm font-medium rounded transition-all ${
                  viewMode === 'diagram'
                    ? 'text-gray-700 bg-white border border-gray-200 shadow-sm'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                图表
              </button>
              <button
                onClick={() => setViewMode('code')}
                className={`px-3 py-1.5 text-sm font-medium rounded transition-all ${
                  viewMode === 'code'
                    ? 'text-gray-700 bg-white border border-gray-200 shadow-sm'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                代码
              </button>
            </div>

            {/* Right side - Action buttons */}
            <div className="flex items-center gap-1">
              {viewMode === 'diagram' && (
                <>
                  {/* Zoom out */}
                  <button
                    onClick={handleZoomOut}
                    className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                    title="缩小"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8"></circle>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                      <line x1="8" y1="11" x2="14" y2="11"></line>
                    </svg>
                  </button>
                  {/* Zoom in */}
                  <button
                    onClick={handleZoomIn}
                    className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                    title="放大"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8"></circle>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                      <line x1="11" y1="8" x2="11" y2="14"></line>
                      <line x1="8" y1="11" x2="14" y2="11"></line>
                    </svg>
                  </button>
                  <div className="w-px h-4 bg-gray-300 mx-1"></div>
                </>
              )}
              {viewMode === 'code' && (
                <>
                  {/* Copy code */}
                  <button
                    onClick={copyCode}
                    className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                    title="复制代码"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                  </button>
                  <div className="w-px h-4 bg-gray-300 mx-1"></div>
                </>
              )}
              {/* Download */}
              <button
                onClick={handleDownload}
                className="flex items-center gap-1 px-2 py-1.5 text-sm text-purple-600 hover:text-purple-700 hover:bg-purple-50 rounded transition-colors"
                title="下载"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                <span>下载</span>
              </button>
              {/* Fullscreen */}
              <button
                onClick={handleDiagramClick}
                className="flex items-center gap-1 px-2 py-1.5 text-sm text-purple-600 hover:text-purple-700 hover:bg-purple-50 rounded transition-colors"
                title="全屏"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 3h6v6"></path>
                  <path d="M9 21H3v-6"></path>
                  <path d="M21 3l-7 7"></path>
                  <path d="M3 21l7-7"></path>
                </svg>
                <span>全屏</span>
              </button>
            </div>
          </div>

          {/* Content area */}
          <div className={`${zoomingEnabled ? "h-[calc(100%-48px)]" : ""}`}>
            {viewMode === 'diagram' ? (
              <div
                ref={diagramContainerRef}
                className="overflow-auto bg-white"
                style={{
                  minHeight: '200px',
                  maxHeight: zoomingEnabled ? '100%' : '500px',
                }}
              >
                <div
                  className="flex justify-center p-6"
                  style={{
                    transform: `scale(${zoom})`,
                    transformOrigin: 'center top',
                    transition: 'transform 0.2s ease-out',
                  }}
                  dangerouslySetInnerHTML={{ __html: svg }}
                />
              </div>
            ) : (
              <div className="overflow-auto bg-gray-50" style={{ maxHeight: zoomingEnabled ? '100%' : '500px' }}>
                <pre className="p-4 text-sm font-mono text-gray-700 whitespace-pre-wrap break-words">
                  {chart}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>

      {!zoomingEnabled && (
        <FullScreenModal
          isOpen={isFullscreen}
          onClose={() => setIsFullscreen(false)}
        >
          <div
            dangerouslySetInnerHTML={{ __html: svg }}
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          />
        </FullScreenModal>
      )}
    </>
  );
};



export default Mermaid;