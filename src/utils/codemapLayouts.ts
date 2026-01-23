/**
 * Advanced layout algorithms for Codemap visualization
 * Includes force-directed, hierarchical, and grouped layouts
 */

export interface LayoutNode {
  id: string;
  name: string;
  type: string;
  path: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface LayoutEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight?: number;
}

export interface LayoutPosition {
  id: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
}

export type LayoutAlgorithm = 'grid' | 'force' | 'hierarchical' | 'grouped';

/**
 * Force-directed layout using physics simulation
 * Nodes repel each other, edges attract connected nodes
 * Enhanced version with type-based layering and better clustering
 */
export function forceDirectedLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: {
    width?: number;
    height?: number;
    iterations?: number;
    repulsionStrength?: number;
    attractionStrength?: number;
    damping?: number;
  } = {}
): LayoutPosition[] {
  const {
    width = 5000,
    height = 4000,
    iterations = 300,
    repulsionStrength = 15000,
    attractionStrength = 0.05,
    damping = 0.88,
  } = options;

  // Define type hierarchy for vertical positioning bias
  const typeHierarchy: Record<string, number> = {
    'directory': 0,      // Top level
    'file': 1,           // Second level
    'class': 2,          // Third level
    'interface': 2,      // Third level
    'function': 3,       // Bottom level
    'method': 3,         // Bottom level
  };

  // Define node sizes for better spacing
  const nodeSizes: Record<string, number> = {
    'directory': 1.5,
    'file': 1.2,
    'class': 1.0,
    'interface': 1.0,
    'function': 0.8,
    'method': 0.8,
  };

  // Initialize positions with vertical bias based on type
  const positions = new Map<string, { x: number; y: number; vx: number; vy: number; level: number; size: number }>();
  nodes.forEach(node => {
    const level = typeHierarchy[node.type] || 2;
    const size = nodeSizes[node.type] || 1.0;

    // Position nodes in rough layers initially
    const layerY = (height / 5) * level + (Math.random() - 0.5) * (height / 10);
    const randomX = Math.random() * width;

    positions.set(node.id, {
      x: randomX,
      y: layerY,
      vx: 0,
      vy: 0,
      level: level,
      size: size,
    });
  });

  // Build adjacency map for faster edge lookup
  const adjacency = new Map<string, Set<string>>();
  edges.forEach(edge => {
    if (!adjacency.has(edge.source)) {
      adjacency.set(edge.source, new Set());
    }
    if (!adjacency.has(edge.target)) {
      adjacency.set(edge.target, new Set());
    }
    adjacency.get(edge.source)!.add(edge.target);
    adjacency.get(edge.target)!.add(edge.source);
  });

  // Create node type map for type-based forces
  const nodeTypeMap = new Map<string, string>();
  nodes.forEach(node => {
    nodeTypeMap.set(node.id, node.type);
  });

  // Physics simulation
  for (let iter = 0; iter < iterations; iter++) {
    const progress = iter / iterations;

    // Calculate repulsion forces (all pairs)
    nodes.forEach((nodeA, i) => {
      const posA = positions.get(nodeA.id)!;

      nodes.forEach((nodeB, j) => {
        if (i >= j) return;

        const posB = positions.get(nodeB.id)!;
        const dx = posB.x - posA.x;
        const dy = posB.y - posA.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        // Enhanced Coulomb's law with node size consideration
        const sizeMultiplier = (posA.size + posB.size) / 2;
        const force = (repulsionStrength * sizeMultiplier) / (distance * distance);
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        posA.vx -= fx;
        posA.vy -= fy;
        posB.vx += fx;
        posB.vy += fy;

        // Type similarity attraction (weak force)
        // Same type nodes attract slightly
        if (nodeA.type === nodeB.type && nodeA.type !== 'directory') {
          const typeForce = 50 * (1 - progress);  // Decreases over time
          const tfx = (dx / distance) * typeForce;
          const tfy = (dy / distance) * typeForce;
          posA.vx += tfx;
          posA.vy += tfy;
          posB.vx -= tfx;
          posB.vy -= tfy;
        }
      });
    });

    // Calculate attraction forces (connected nodes)
    edges.forEach(edge => {
      const posSource = positions.get(edge.source);
      const posTarget = positions.get(edge.target);

      if (!posSource || !posTarget) return;

      const dx = posTarget.x - posSource.x;
      const dy = posTarget.y - posSource.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;

      // Enhanced Hooke's law with edge type consideration
      // CONTAINS edges get stronger attraction to show hierarchy
      const edgeTypeMultiplier = edge.type === 'contains' ? 1.5 : 1.0;
      const force = attractionStrength * distance * edgeTypeMultiplier;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;

      posSource.vx += fx;
      posSource.vy += fy;
      posTarget.vx -= fx;
      posTarget.vy -= fy;
    });

    // Add vertical layering constraint (gentle force pushing nodes toward their level)
    const layerForce = 200 * (1 - progress * 0.5);  // Decreases over time but doesn't disappear
    nodes.forEach(node => {
      const pos = positions.get(node.id)!;
      const targetY = (height / 5) * pos.level;
      const dy = targetY - pos.y;

      // Gentle force toward target layer
      if (Math.abs(dy) > 100) {  // Only apply if far from target
        pos.vy += (dy / Math.abs(dy)) * layerForce * 0.001;
      }
    });

    // Apply velocities with damping and boundary constraints
    positions.forEach((pos, id) => {
      pos.x += pos.vx;
      pos.y += pos.vy;
      pos.vx *= damping;
      pos.vy *= damping;

      // Keep nodes within bounds with soft boundaries
      if (pos.x < 50) pos.x = 50 + Math.random() * 50;
      if (pos.x > width - 50) pos.x = width - 50 - Math.random() * 50;
      if (pos.y < 50) pos.y = 50 + Math.random() * 50;
      if (pos.y > height - 50) pos.y = height - 50 - Math.random() * 50;
    });
  }

  // Convert to output format
  return Array.from(positions.entries()).map(([id, pos]) => ({
    id,
    x: pos.x,
    y: pos.y,
  }));
}

/**
 * Hierarchical layout creating tree-like structure based on dependencies
 * Root nodes at top, dependencies flow downward
 * Optimized with better spacing and visual hierarchy
 */
export function hierarchicalLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: {
    levelHeight?: number;
    nodeSpacing?: number;
    direction?: 'TB' | 'BT' | 'LR' | 'RL';
  } = {}
): LayoutPosition[] {
  const {
    levelHeight = 200,
    nodeSpacing = 250,
    direction = 'TB', // Top to Bottom
  } = options;

  // Build dependency graph
  const inDegree = new Map<string, number>();
  const outEdges = new Map<string, string[]>();

  nodes.forEach(node => {
    inDegree.set(node.id, 0);
    outEdges.set(node.id, []);
  });

  edges.forEach(edge => {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    outEdges.get(edge.source)?.push(edge.target);
  });

  // Find root nodes (nodes with no incoming edges)
  const roots: string[] = [];
  inDegree.forEach((degree, nodeId) => {
    if (degree === 0) {
      roots.push(nodeId);
    }
  });

  // If no roots (cycle or isolated nodes), use all nodes as potential roots
  if (roots.length === 0) {
    nodes.forEach(node => roots.push(node.id));
  }

  // Topological sort with level assignment (BFS)
  const levels = new Map<string, number>();
  const queue: Array<{ id: string; level: number }> = roots.map(id => ({ id, level: 0 }));
  const visited = new Set<string>();

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;

    if (visited.has(id)) continue;
    visited.add(id);

    levels.set(id, level);

    const children = outEdges.get(id) || [];
    children.forEach(childId => {
      if (!visited.has(childId)) {
        queue.push({ id: childId, level: level + 1 });
      }
    });
  }

  // Assign unvisited nodes to level 0
  nodes.forEach(node => {
    if (!levels.has(node.id)) {
      levels.set(node.id, 0);
    }
  });

  // Group nodes by level
  const nodesByLevel = new Map<number, string[]>();
  levels.forEach((level, nodeId) => {
    if (!nodesByLevel.has(level)) {
      nodesByLevel.set(level, []);
    }
    nodesByLevel.get(level)!.push(nodeId);
  });

  // Calculate positions
  const positions: LayoutPosition[] = [];

  nodesByLevel.forEach((nodeIds, level) => {
    const levelWidth = nodeIds.length * nodeSpacing;
    const startX = -levelWidth / 2;

    nodeIds.forEach((nodeId, index) => {
      const x = startX + index * nodeSpacing + nodeSpacing / 2;
      const y = level * levelHeight;

      // Apply direction transformation
      let finalX = x;
      let finalY = y;

      switch (direction) {
        case 'TB': // Top to Bottom (default)
          finalX = x + 1000; // Center horizontally
          finalY = y + 100;
          break;
        case 'BT': // Bottom to Top
          finalX = x + 1000;
          finalY = -y + (nodesByLevel.size * levelHeight);
          break;
        case 'LR': // Left to Right
          finalX = y + 100;
          finalY = x + 1000;
          break;
        case 'RL': // Right to Left
          finalX = -y + (nodesByLevel.size * levelHeight);
          finalY = x + 1000;
          break;
      }

      positions.push({
        id: nodeId,
        x: finalX,
        y: finalY,
      });
    });
  });

  return positions;
}

/**
 * Grouped layout clustering related components together
 * Groups by type, module, or custom criteria
 * Optimized with better group organization and spacing
 */
export function groupedLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: {
    groupBy?: 'type' | 'path' | 'module';
    groupSpacing?: number;
    nodeSpacing?: number;
    nodesPerRow?: number;
  } = {}
): LayoutPosition[] {
  const {
    groupBy = 'type',
    groupSpacing = 400,
    nodeSpacing = 180,
    nodesPerRow = 6,
  } = options;

  // Group nodes based on criteria
  const groups = new Map<string, LayoutNode[]>();

  nodes.forEach(node => {
    let groupKey: string;

    switch (groupBy) {
      case 'type':
        groupKey = node.type;
        break;
      case 'path':
        // Group by first directory in path
        groupKey = node.path.split('/')[0] || 'root';
        break;
      case 'module':
        // Group by file extension or metadata
        groupKey = node.metadata?.module || node.path.split('.').pop() || 'unknown';
        break;
      default:
        groupKey = 'default';
    }

    if (!groups.has(groupKey)) {
      groups.set(groupKey, []);
    }
    groups.get(groupKey)!.push(node);
  });

  const positions: LayoutPosition[] = [];
  let currentY = 100;

  // Layout each group
  Array.from(groups.entries()).forEach(([groupName, groupNodes], groupIndex) => {
    const rows = Math.ceil(groupNodes.length / nodesPerRow);
    const groupHeight = rows * nodeSpacing;

    groupNodes.forEach((node, index) => {
      const row = Math.floor(index / nodesPerRow);
      const col = index % nodesPerRow;

      const x = 100 + col * nodeSpacing;
      const y = currentY + row * nodeSpacing;

      positions.push({
        id: node.id,
        x,
        y,
      });
    });

    currentY += groupHeight + groupSpacing;
  });

  return positions;
}

/**
 * Grid layout (existing simple layout)
 * Arranges nodes in a regular grid
 * Optimized with dynamic column calculation and better spacing
 */
export function gridLayout(
  nodes: LayoutNode[],
  options: {
    columns?: number;
    xSpacing?: number;
    ySpacing?: number;
    groupByType?: boolean;
  } = {}
): LayoutPosition[] {
  // Calculate optimal column count based on node count
  const optimalColumns = Math.max(5, Math.min(10, Math.ceil(Math.sqrt(nodes.length))));

  const {
    columns = optimalColumns,
    xSpacing = 250,
    ySpacing = 150,
    groupByType = true,
  } = options;

  const positions: LayoutPosition[] = [];

  if (groupByType) {
    // Group by type first with better organization
    const typeGroups = new Map<string, LayoutNode[]>();
    nodes.forEach(node => {
      if (!typeGroups.has(node.type)) {
        typeGroups.set(node.type, []);
      }
      typeGroups.get(node.type)!.push(node);
    });

    // Define type ordering for better visual hierarchy
    const typeOrder = ['directory', 'file', 'class', 'interface', 'function', 'method'];
    const sortedTypes = Array.from(typeGroups.keys()).sort((a, b) => {
      const aIndex = typeOrder.indexOf(a);
      const bIndex = typeOrder.indexOf(b);
      if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;
      return aIndex - bIndex;
    });

    let yOffset = 100;

    sortedTypes.forEach((type) => {
      const groupNodes = typeGroups.get(type)!;

      groupNodes.forEach((node, index) => {
        const x = (index % columns) * xSpacing + 150;
        const y = yOffset + Math.floor(index / columns) * ySpacing;

        positions.push({ id: node.id, x, y });
      });

      // Add larger spacing between groups
      yOffset += Math.ceil(groupNodes.length / columns) * ySpacing + 100;
    });
  } else {
    // Simple grid without grouping
    nodes.forEach((node, index) => {
      const x = (index % columns) * xSpacing + 100;
      const y = Math.floor(index / columns) * ySpacing + 50;

      positions.push({ id: node.id, x, y });
    });
  }

  return positions;
}

/**
 * Apply layout algorithm to nodes
 */
export function applyLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  algorithm: LayoutAlgorithm,
  options: Record<string, any> = {}
): LayoutPosition[] {
  switch (algorithm) {
    case 'force':
      return forceDirectedLayout(nodes, edges, options);
    case 'hierarchical':
      return hierarchicalLayout(nodes, edges, options);
    case 'grouped':
      return groupedLayout(nodes, edges, options);
    case 'grid':
    default:
      return gridLayout(nodes, options);
  }
}
