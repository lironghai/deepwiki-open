'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FaSearch, FaFilter, FaExpand, FaCompress, FaFileCode, FaFolder, FaCube, FaProjectDiagram } from 'react-icons/fa';

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

const CustomNode: React.FC<{ data: any }> = ({ data }) => {
  const colors = NodeTypeColors[data.type] || NodeTypeColors.file;
  const icon = NodeTypeIcons[data.type] || NodeTypeIcons.file;

  return (
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
  );
};

const nodeTypes = {
  custom: CustomNode,
};

// 内部组件：实际使用ReactFlow的组件（所有hooks在顶层）
function CodemapContent({ 
  data, 
  onNodeClick, 
  className,
  reactFlowComponents 
}: CodemapProps & { reactFlowComponents: any }) {
  const { ReactFlow: RF, Background: Bg, Controls: Ctrl, MiniMap: MM, useNodesState: useNodes, useEdgesState: useEdges, Panel: Pnl, MarkerType: MT, Position: Pos } = reactFlowComponents;
  
  // 所有hooks在组件顶层无条件调用
  const [nodes, setNodes, onNodesChange] = useNodes([]);
  const [edges, setEdges, onEdgesChange] = useEdges([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedLanguages, setSelectedLanguages] = useState<Set<string>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  // 布局算法 - 简单的分层布局
  const layoutNodes = useCallback((codeNodes: CodeNode[]) => {
    const nodeMap = new Map<string, CodeNode>();
    codeNodes.forEach(n => nodeMap.set(n.id, n));

    // 按类型分组
    const typeGroups: Record<string, CodeNode[]> = {};
    codeNodes.forEach(node => {
      if (!typeGroups[node.type]) {
        typeGroups[node.type] = [];
      }
      typeGroups[node.type].push(node);
    });

    const layouted: Node[] = [];
    let yOffset = 0;
    const xSpacing = 200;
    const ySpacing = 100;

    Object.entries(typeGroups).forEach(([type, groupNodes], typeIndex) => {
      groupNodes.forEach((node, index) => {
        const x = (index % 5) * xSpacing;
        const y = yOffset + Math.floor(index / 5) * ySpacing;

        layouted.push({
          id: node.id,
          type: 'custom',
          position: { x, y },
          data: {
            label: node.name,
            type: node.type,
            language: node.language,
            description: node.description,
            originalNode: node,
          },
          sourcePosition: Pos.Right,
          targetPosition: Pos.Left,
        });
      });

      yOffset += Math.ceil(groupNodes.length / 5) * ySpacing + 50;
    });

    return layouted;
  }, [Pos]);

  // 转换边数据
  const convertEdges = useCallback((codeEdges: CodeEdge[]) => {
    return codeEdges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      label: edge.label,
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
  }, [MT]);

  // 初始化节点和边
  useEffect(() => {
    const layoutedNodes = layoutNodes(data.nodes);
    const convertedEdges = convertEdges(data.edges);
    setNodes(layoutedNodes);
    setEdges(convertedEdges);
  }, [data.nodes, data.edges, layoutNodes, convertEdges, setNodes, setEdges]);

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
    const filteredNodeIds = new Set(filteredNodes.map((n: any) => n.id));
    return edges.filter((edge: any) => filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target));
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
    <div className={`flex h-full ${className}`}>
      <div className="flex flex-col h-full w-full">
        {/* 侧边栏 */}
        <div className="w-64 border-r border-[var(--border-color)] bg-[var(--card-bg)] p-4 overflow-y-auto">
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
        <div className="flex-1 relative">
          <RF
            // nodes={nodes}
            // edges={edges}
            nodes={filteredNodes}
            edges={filteredNodes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.1}
            maxZoom={2}
            defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
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
