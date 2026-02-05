'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FaSearch, FaFilter, FaExpand, FaCompress, FaFileCode, FaFolder, FaCube, FaProjectDiagram, FaProjectDiagram as FaLayout } from 'react-icons/fa';
import { applyLayout, LayoutAlgorithm, LayoutNode, LayoutEdge } from '@/utils/codemapLayouts';

// 动态导入ReactFlow以避免chunk加载问题
let ReactFlow: any;
let Background: any;
let Controls: any;
let MiniMap: any;
let useNodesState: any;
let useEdgesState: any;
let Panel: any;
let MarkerType: any;
let Position: any;
let Handle: any;

// 延迟加载ReactFlow
const loadReactFlow = async () => {
  if (!ReactFlow) {
    try {
      const reactflowModule = await import('reactflow');
      ReactFlow = reactflowModule.default;
      Background = reactflowModule.Background;
      Controls = reactflowModule.Controls;
      MiniMap = reactflowModule.MiniMap;
      useNodesState = reactflowModule.useNodesState;
      useEdgesState = reactflowModule.useEdgesState;
      Panel = reactflowModule.Panel;
      MarkerType = reactflowModule.MarkerType;
      Position = reactflowModule.Position;
      Handle = reactflowModule.Handle;

      // 动态导入样式（忽略类型检查，因为CSS文件没有类型声明）
      // @ts-ignore
      await import('reactflow/dist/style.css');
    } catch (error) {
      console.error('Failed to load ReactFlow:', error);
      throw error;
    }
  }
  return {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    Panel,
    MarkerType,
    Position,
    Handle,
  };
};

// 节点类型图标映射
const NodeTypeIcons: Record<string, React.ReactNode> = {
  file: <FaFileCode className="w-3 h-3" />,
  directory: <FaFolder className="w-3 h-3" />,
  class: <FaCube className="w-3 h-3" />,
  function: <FaProjectDiagram className="w-3 h-3" />,
  method: <FaProjectDiagram className="w-3 h-3" />,
  module: <FaCube className="w-3 h-3" />,
};

// 节点类型颜色映射
const NodeTypeColors: Record<string, { bg: string; border: string; text: string }> = {
  file: { bg: '#f0f9ff', border: '#0ea5e9', text: '#0c4a6e' },
  directory: { bg: '#fef3c7', border: '#f59e0b', text: '#78350f' },
  class: { bg: '#fce7f3', border: '#ec4899', text: '#831843' },
  function: { bg: '#ddd6fe', border: '#8b5cf6', text: '#4c1d95' },
  method: { bg: '#e0e7ff', border: '#6366f1', text: '#312e81' },
  module: { bg: '#d1fae5', border: '#10b981', text: '#065f46' },
};

// 边类型颜色映射
const EdgeTypeColors: Record<string, string> = {
  import: '#0ea5e9',
  call: '#8b5cf6',
  inherit: '#ec4899',
  implement: '#10b981',
  reference: '#64748b',
  contains: '#94a3b8',
};

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

interface CodeEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  weight?: number;
}

interface CodemapProps {
  data: {
    nodes: CodeNode[];
    edges: CodeEdge[];
    metadata: {
      total_files: number;
      node_count: number;
      edge_count: number;
      total_lines: number;
    };
  };
  onNodeClick?: (node: CodeNode) => void;
  className?: string;
}

interface Node {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: any;
  sourcePosition?: any;
  targetPosition?: any;
}

// CustomNode需要在loadReactFlow之后创建，因为需要Handle组件
let CustomNode: React.FC<{ data: any }> | null = null;

const createCustomNode = (HandleComponent: any, PositionEnum: any) => {
  return ({ data }: { data: any }) => {
    const colors = NodeTypeColors[data.type] || NodeTypeColors.file;
    const icon = NodeTypeIcons[data.type] || NodeTypeIcons.file;

    return (
      <>
        {/* Source handle (right side) - for outgoing edges */}
        <HandleComponent
          type="source"
          position={PositionEnum.Right}
          id="right"
          style={{ background: colors.border }}
        />

        {/* Target handle (left side) - for incoming edges */}
        <HandleComponent
          type="target"
          position={PositionEnum.Left}
          id="left"
          style={{ background: colors.border }}
        />

        <div
          className="px-4 py-2 rounded-md border-2 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
          style={{
            backgroundColor: colors.bg,
            borderColor: colors.border,
            color: colors.text,
            minWidth: '120px',
          }}
        >
          <div className="flex items-center gap-2">
            {icon}
            <div className="text-sm font-medium truncate" title={data.label}>
              {data.label}
            </div>
          </div>
          {data.description && (
            <div className="text-xs mt-1 text-gray-600 truncate" title={data.description}>
              {data.description}
            </div>
          )}
          {data.language && (
            <div className="text-xs mt-1 text-gray-500">
              {data.language}
            </div>
          )}
        </div>
      </>
    );
  };
};

// nodeTypes will be created dynamically in CodemapContent after ReactFlow loads

// 内部组件：实际使用ReactFlow的组件（所有hooks在顶层）
function CodemapContent({
  data,
  onNodeClick,
  className,
  reactFlowComponents
}: CodemapProps & { reactFlowComponents: any }) {
  const { ReactFlow: RF, Background: Bg, Controls: Ctrl, MiniMap: MM, useNodesState: useNodes, useEdgesState: useEdges, Panel: Pnl, MarkerType: MT, Position: Pos, Handle: Hdl } = reactFlowComponents;

  // Create nodeTypes with Handle component
  const nodeTypes = React.useMemo(() => {
    if (!CustomNode) {
      CustomNode = createCustomNode(Hdl, Pos);
    }
    return {
      custom: CustomNode,
    };
  }, [Hdl, Pos]);
  
  // 所有hooks在组件顶层无条件调用
  const [nodes, setNodes, onNodesChange] = useNodes([]);
  const [edges, setEdges, onEdgesChange] = useEdges([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set(['directory']));
  const [selectedLanguages, setSelectedLanguages] = useState<Set<string>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [layoutAlgorithm, setLayoutAlgorithm] = useState<LayoutAlgorithm>('fruchterman-reingold');

  // 获取所有唯一的节点类型
  const availableTypes = useMemo(() => {
    const types = new Set(data.nodes.map(n => n.type));
    return Array.from(types);
  }, [data.nodes]);

  // 获取所有唯一的语言
  const availableLanguages = useMemo(() => {
    const languages = new Set(
      data.nodes
        .map(n => n.language)
        .filter((lang): lang is string => lang !== undefined)
    );
    return Array.from(languages);
  }, [data.nodes]);

  // 布局算法 - 使用高级布局系统
  const layoutNodes = useCallback((codeNodes: CodeNode[], codeEdges: CodeEdge[]) => {
    console.log(`Applying layout algorithm: ${layoutAlgorithm}`);

    // Convert to layout format
    const layoutNodesData: LayoutNode[] = codeNodes.map(node => ({
      id: node.id,
      name: node.name,
      type: node.type,
      path: node.path,
      description: node.description,
      metadata: node.metadata,
    }));

    const layoutEdgesData: LayoutEdge[] = codeEdges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type,
      weight: edge.weight,
    }));

    // Calculate optimal parameters based on node count
    const nodeCount = codeNodes.length;
    const columns = Math.max(5, Math.min(10, Math.ceil(Math.sqrt(nodeCount))));

    // Apply selected layout algorithm with optimized parameters
    let layoutOptions: Record<string, any>;

    switch (layoutAlgorithm) {
      case 'fruchterman-reingold':
        layoutOptions = {
          width: 5000,
          height: 4000,
          iterations: 300,
          k: Math.sqrt((5000 * 4000) / nodeCount), // Optimal k based on area
          temperature: Math.max(5000, 4000) / 10,
          coolingFactor: 0.95,
          direction: 'TB', // Top to Bottom
        };
        break;
      case 'hierarchical-orthogonal':
        layoutOptions = {
          levelHeight: 250,
          nodeSpacing: 300,
          direction: 'TB',
          minimizeCrossings: true,
          width: 5000,
          height: 4000,
        };
        break;
      case 'force':
        layoutOptions = {
          width: 4000,
          height: 4000,
          iterations: 200,
          repulsionStrength: 8000,
          attractionStrength: 0.02,
          damping: 0.85,
        };
        break;
      case 'hierarchical':
        layoutOptions = {
          levelHeight: 200,
          nodeSpacing: 250,
          direction: 'TB',
        };
        break;
      case 'grouped':
        layoutOptions = {
          groupBy: 'type',
          groupSpacing: 400,
          nodeSpacing: 180,
          nodesPerRow: Math.max(4, Math.min(8, Math.ceil(nodeCount / 20))),
        };
        break;
      case 'grid':
      default:
        layoutOptions = {
          columns,
          xSpacing: 250,
          ySpacing: 150,
          groupByType: true,
        };
        break;
    }

    const positions = applyLayout(layoutNodesData, layoutEdgesData, layoutAlgorithm, layoutOptions);

    // Convert positions to ReactFlow nodes
    const positionMap = new Map(positions.map(p => [p.id, p]));

    // IMPORTANT: Only include nodes that have valid positions
    // This prevents dangling edges from appearing
    const layouted: Node[] = codeNodes
      .filter(node => positionMap.has(node.id))  // Only nodes with valid positions
      .map(node => {
        const pos = positionMap.get(node.id)!;

        return {
          id: node.id,
          type: 'custom',
          position: { x: pos.x, y: pos.y },
          data: {
            label: node.name,
            type: node.type,
            language: node.language,
            description: node.description,
            originalNode: node,
          },
          sourcePosition: Pos.Right,
          targetPosition: Pos.Left,
        };
      });

    console.log(`Layout complete: ${layouted.length} nodes positioned`);
    return layouted;
  }, [Pos, layoutAlgorithm]);

  // 转换边数据
  const convertEdges = useCallback((codeEdges: CodeEdge[]) => {
    console.log(`Converting ${codeEdges.length} edges for ReactFlow`);
    
    // Use orthogonal routing for hierarchical-orthogonal layout
    const edgeType = layoutAlgorithm === 'hierarchical-orthogonal' ? 'orthogonal' : 'smoothstep';
    
    const converted = codeEdges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edgeType,
      label: edge.label || '',  // Handle null labels
      animated: edge.type === 'call',
      style: {
        stroke: EdgeTypeColors[edge.type] || EdgeTypeColors.reference,
        strokeWidth: Math.min(edge.weight || 1, 3),
      },
      markerEnd: {
        type: MT.ArrowClosed,
        color: EdgeTypeColors[edge.type] || EdgeTypeColors.reference,
      },
    }));
    console.log(`First 3 converted edges:`, converted.slice(0, 3));
    return converted;
  }, [MT, layoutAlgorithm]);

  // 初始化节点和边
  useEffect(() => {
    console.log('Initializing Codemap with data:', {
      nodeCount: data.nodes.length,
      edgeCount: data.edges.length,
      layoutAlgorithm: layoutAlgorithm,
      sampleEdge: data.edges[0]
    });

    // 重要：先清空旧的节点和边，防止切换布局时遗留
    console.log('Clearing previous layout...');
    setNodes([]);
    setEdges([]);

    // 使用setTimeout确保状态清空后再重新布局
    // 这样可以避免ReactFlow中的边遗留问题
    const timeoutId = setTimeout(() => {
      const layoutedNodes = layoutNodes(data.nodes, data.edges);
      const convertedEdges = convertEdges(data.edges);

      console.log('After conversion:', {
        layoutedNodesCount: layoutedNodes.length,
        convertedEdgesCount: convertedEdges.length
      });

      setNodes(layoutedNodes);
      setEdges(convertedEdges);
    }, 10);

    return () => clearTimeout(timeoutId);
  }, [data.nodes, data.edges, layoutNodes, convertEdges, setNodes, setEdges, layoutAlgorithm]);

  // 过滤节点和边
  const filteredNodes = useMemo(() => {
    return nodes.filter((node: any) => {
      const matchesSearch = !searchTerm || node.data.label.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = selectedTypes.size === 0 || selectedTypes.has(node.data.type);
      const matchesLanguage = selectedLanguages.size === 0 || !node.data.language || selectedLanguages.has(node.data.language);
      return matchesSearch && matchesType && matchesLanguage;
    });
  }, [nodes, searchTerm, selectedTypes, selectedLanguages]);

  const filteredEdges = useMemo(() => {
    // Get IDs of currently visible nodes
    const filteredNodeIds = new Set(filteredNodes.map((n: any) => n.id));

    // Filter edges: both source and target must be in visible nodes
    const filtered = edges.filter((edge: any) => {
      const hasSource = filteredNodeIds.has(edge.source);
      const hasTarget = filteredNodeIds.has(edge.target);

      // Debug: log edges with missing nodes
      if (!hasSource || !hasTarget) {
        if (!hasSource && !hasTarget) {
          console.debug(`Edge ${edge.id}: both nodes missing`);
        } else if (!hasSource) {
          console.debug(`Edge ${edge.id}: source node ${edge.source} missing`);
        } else {
          console.debug(`Edge ${edge.id}: target node ${edge.target} missing`);
        }
      }

      return hasSource && hasTarget;
    });

    console.log('Filtering edges:', {
      totalEdges: edges.length,
      filteredNodesCount: filteredNodes.length,
      filteredEdgesCount: filtered.length,
      edgesDropped: edges.length - filtered.length,
      dropReasons: {
        bothMissing: edges.filter((e: any) => !filteredNodeIds.has(e.source) && !filteredNodeIds.has(e.target)).length,
        sourceMissing: edges.filter((e: any) => !filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)).length,
        targetMissing: edges.filter((e: any) => filteredNodeIds.has(e.source) && !filteredNodeIds.has(e.target)).length,
      }
    });

    return filtered;
  }, [edges, filteredNodes]);

  // 更新过滤后的节点和边
  // useEffect(() => {
  //   setNodes(filteredNodes);
  //   setEdges(filteredEdges);
  // }, [filteredNodes, filteredEdges, setNodes, setEdges]);

  // 切换类型过滤
  const toggleType = useCallback((type: string) => {
    setSelectedTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  // 切换语言过滤
  const toggleLanguage = useCallback((language: string) => {
    setSelectedLanguages(prev => {
      const next = new Set(prev);
      if (next.has(language)) {
        next.delete(language);
      } else {
        next.add(language);
      }
      return next;
    });
  }, []);

  // 清除所有过滤
  const clearFilters = useCallback(() => {
    setSearchTerm('');
    setSelectedTypes(new Set());
    setSelectedLanguages(new Set());
  }, []);

  // 处理节点点击
  const handleNodeClick = useCallback((event: React.MouseEvent, node: any) => {
    if (onNodeClick && node.data.originalNode) {
      onNodeClick(node.data.originalNode);
    }
  }, [onNodeClick]);

  return (
    <div className={`flex h-full w-full ${className}`}>
      <div className="flex flex-row h-full w-full">
        {/* 侧边栏 */}
        <div className="w-64 flex-shrink-0 border-r border-[var(--border-color)] bg-[var(--card-bg)] p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4 text-[var(--foreground)]">代码地图</h3>

          {/* 搜索框 */}
          <div className="mb-4">
            <div className="relative">
              <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[var(--muted)]" />
              <input
                type="text"
                placeholder="搜索节点..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border border-[var(--border-color)] rounded-md bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
              />
            </div>
          </div>

          {/* 布局算法选择器 */}
          <div className="mb-4">
            <h4 className="text-sm font-medium mb-2 text-[var(--foreground)] flex items-center gap-2">
              <FaProjectDiagram className="w-3 h-3" />
              布局算法
            </h4>
            <select
              value={layoutAlgorithm}
              onChange={e => setLayoutAlgorithm(e.target.value as LayoutAlgorithm)}
              className="w-full px-3 py-2 border border-[var(--border-color)] rounded-md bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
            >
              <option value="fruchterman-reingold">Fruchterman-Reingold (推荐)</option>
              <option value="hierarchical-orthogonal">层次正交布局</option>
              <option value="force">力导向布局</option>
              <option value="hierarchical">层次布局</option>
              <option value="grouped">分组布局</option>
              <option value="grid">网格布局</option>
            </select>
          </div>

          {/* 类型过滤 */}
          <div className="mb-4">
            <h4 className="text-sm font-medium mb-2 text-[var(--foreground)] flex items-center gap-2">
              <FaFilter className="w-3 h-3" />
              节点类型
            </h4>
            <div className="space-y-1">
              {availableTypes.map(type => (
                <label key={type} className="flex items-center gap-2 cursor-pointer hover:bg-[var(--background)]/50 p-1 rounded">
                  <input
                    type="checkbox"
                    checked={selectedTypes.has(type)}
                    onChange={() => toggleType(type)}
                    className="rounded border-[var(--border-color)]"
                  />
                  <span className="text-sm text-[var(--foreground)]">{type}</span>
                </label>
              ))}
            </div>
          </div>

          {/* 语言过滤 */}
          {availableLanguages.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium mb-2 text-[var(--foreground)]">语言</h4>
              <div className="space-y-1">
                {availableLanguages.map(lang => (
                  <label key={lang} className="flex items-center gap-2 cursor-pointer hover:bg-[var(--background)]/50 p-1 rounded">
                    <input
                      type="checkbox"
                      checked={selectedLanguages.has(lang)}
                      onChange={() => toggleLanguage(lang)}
                      className="rounded border-[var(--border-color)]"
                    />
                    <span className="text-sm text-[var(--foreground)]">{lang}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* 统计信息 */}
          <div className="mb-4">
            <h4 className="text-xs font-medium mb-2 text-[var(--muted)]">统计</h4>
            <div className="space-y-1 text-xs text-[var(--foreground)]">
              <div>文件: {data.metadata.total_files}</div>
              <div>节点: {filteredNodes.length} / {data.metadata.node_count}</div>
              <div>关系: {filteredEdges.length} / {data.metadata.edge_count}</div>
              <div>代码行: {data.metadata.total_lines.toLocaleString()}</div>
            </div>
          </div>

          {/* 清除按钮 */}
          {(searchTerm || selectedTypes.size > 0 || selectedLanguages.size > 0) && (
            <button
              onClick={clearFilters}
              className="mt-4 w-full py-2 px-3 bg-[var(--accent-primary)] text-white rounded-md hover:opacity-90 transition-opacity text-sm"
            >
              清除过滤
            </button>
          )}
        </div>

        {/* 主可视化区域 */}
        <div className="flex-1 relative min-w-0 min-h-0">
          <RF
            nodes={filteredNodes}
            edges={filteredEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{
              padding: 0.2,
              includeHiddenNodes: false,
              minZoom: 0.1,
              maxZoom: 1.5,
            }}
            minZoom={0.05}
            maxZoom={3}
            defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
            connectionLineType={layoutAlgorithm === 'hierarchical-orthogonal' ? 'orthogonal' : 'smoothstep'}
            defaultEdgeOptions={{
              type: layoutAlgorithm === 'hierarchical-orthogonal' ? 'orthogonal' : 'smoothstep',
              animated: false,
              style: { strokeWidth: 2 }
            }}
            proOptions={{ hideAttribution: true }}
            deleteKeyCode={null}
            selectNodesOnDrag={false}
          >
            <Bg />
            <Ctrl />
            <MM
              nodeColor={(node: any) => {
                const type = node.data.type;
                return NodeTypeColors[type]?.border || '#64748b';
              }}
              maskColor="rgba(0, 0, 0, 0.1)"
            />
            <Pnl position="top-right">
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-2 bg-white dark:bg-gray-800 rounded-md shadow-md hover:shadow-lg transition-shadow"
                title={isFullscreen ? '退出全屏' : '全屏显示'}
              >
                {isFullscreen ? <FaCompress /> : <FaExpand />}
              </button>
            </Pnl>
          </RF>
        </div>
      </div>
    </div>
  );
}

// 主组件：负责加载ReactFlow
export default function Codemap({ data, onNodeClick, className = '' }: CodemapProps) {
  const [reactFlowLoaded, setReactFlowLoaded] = useState(false);
  const [reactFlowError, setReactFlowError] = useState<string | null>(null);
  const [reactFlowComponents, setReactFlowComponents] = useState<any>(null);
  
  // 动态加载ReactFlow
  useEffect(() => {
    let mounted = true;
    
    loadReactFlow()
      .then((components) => {
        if (!mounted) return;
        setReactFlowComponents(components);
        setReactFlowLoaded(true);
      })
      .catch((error) => {
        if (!mounted) return;
        console.error('Failed to load ReactFlow:', error);
        setReactFlowError('Failed to load ReactFlow library. Please refresh the page.');
      });
    
    return () => {
      mounted = false;
    };
  }, []);

  // 如果ReactFlow未加载，显示加载状态
  if (!reactFlowLoaded || !reactFlowComponents) {
    if (reactFlowError) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center p-6">
            <div className="text-red-500 mb-4">{reactFlowError}</div>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">加载代码地图组件...</p>
        </div>
      </div>
    );
  }

  // ReactFlow加载完成后，渲染内容组件
  return (
    <CodemapContent 
      data={data} 
      onNodeClick={onNodeClick} 
      className={className}
      reactFlowComponents={reactFlowComponents}
    />
  );
}
