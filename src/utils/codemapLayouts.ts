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

export type LayoutAlgorithm = 'grid' | 'force' | 'hierarchical' | 'grouped' | 'fruchterman-reingold' | 'hierarchical-orthogonal';

/**
 * Fruchterman-Reingold force-directed layout algorithm
 * Optimized for better node distribution and reduced edge crossings
 * Uses temperature-based cooling for stable convergence
 */
export function fruchtermanReingoldLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: {
    width?: number;
    height?: number;
    iterations?: number;
    k?: number; // Ideal distance between nodes
    temperature?: number; // Initial temperature
    coolingFactor?: number; // Temperature cooling rate
    direction?: 'TB' | 'BT' | 'LR' | 'RL'; // Layout direction
  } = {}
): LayoutPosition[] {
  const {
    width = 5000,
    height = 4000,
    iterations = 300,
    k = Math.sqrt((width * height) / nodes.length), // Optimal k based on area
    temperature = Math.max(width, height) / 10, // Initial temperature
    coolingFactor = 0.95, // Cooling rate per iteration
    direction = 'TB', // Top to Bottom
  } = options;

  // Type hierarchy for directional bias - more levels for better layering
  const typeHierarchy: Record<string, number> = {
    'directory': 0,
    'file': 1,
    'class': 2,
    'interface': 2,
    'function': 3,
    'method': 3,
  };

  // Calculate number of levels needed
  const maxLevel = Math.max(...nodes.map(n => typeHierarchy[n.type] || 2));
  const numLevels = maxLevel + 1;

  // Initialize positions with directional bias
  const positions = new Map<string, { 
    x: number; 
    y: number; 
    fx: number; 
    fy: number;
    level: number;
  }>();

  // Group nodes by level for better initial positioning
  const nodesByLevel = new Map<number, LayoutNode[]>();
  nodes.forEach(node => {
    const level = typeHierarchy[node.type] || 2;
    if (!nodesByLevel.has(level)) {
      nodesByLevel.set(level, []);
    }
    nodesByLevel.get(level)!.push(node);
  });

  // Initialize positions with better layering and spacing
  nodes.forEach(node => {
    const level = typeHierarchy[node.type] || 2;
    const levelNodes = nodesByLevel.get(level) || [];
    const nodeIndex = levelNodes.findIndex(n => n.id === node.id);
    const nodesInLevel = levelNodes.length;
    
    // Initial positioning based on direction with better horizontal distribution
    let x: number, y: number;
    switch (direction) {
      case 'TB': // Top to Bottom - clear horizontal layers
        // Distribute nodes evenly across width within each level
        const levelSpacing = width / (nodesInLevel + 1);
        x = levelSpacing * (nodeIndex + 1);
        // Place nodes in clear horizontal bands
        y = (height / (numLevels + 1)) * (level + 1) + (Math.random() - 0.5) * 50;
        break;
      case 'BT': // Bottom to Top
        const levelSpacingBT = width / (nodesInLevel + 1);
        x = levelSpacingBT * (nodeIndex + 1);
        y = height - (height / (numLevels + 1)) * (level + 1) - (Math.random() - 0.5) * 50;
        break;
      case 'LR': // Left to Right
        const levelSpacingLR = height / (nodesInLevel + 1);
        x = (width / (numLevels + 1)) * (level + 1) + (Math.random() - 0.5) * 50;
        y = levelSpacingLR * (nodeIndex + 1);
        break;
      case 'RL': // Right to Left
        const levelSpacingRL = height / (nodesInLevel + 1);
        x = width - (width / (numLevels + 1)) * (level + 1) - (Math.random() - 0.5) * 50;
        y = levelSpacingRL * (nodeIndex + 1);
        break;
      default:
        x = Math.random() * width;
        y = Math.random() * height;
    }

    positions.set(node.id, {
      x,
      y,
      fx: 0,
      fy: 0,
      level,
    });
  });

  // Build adjacency map
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

  let currentTemp = temperature;

  // Fruchterman-Reingold simulation
  for (let iter = 0; iter < iterations; iter++) {
    // Reset forces
    positions.forEach(pos => {
      pos.fx = 0;
      pos.fy = 0;
    });

    // Calculate repulsion forces (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      const nodeA = nodes[i];
      const posA = positions.get(nodeA.id)!;

      for (let j = i + 1; j < nodes.length; j++) {
        const nodeB = nodes[j];
        const posB = positions.get(nodeB.id)!;

        const dx = posB.x - posA.x;
        const dy = posB.y - posA.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 0.1; // Avoid division by zero

        // Fruchterman-Reingold repulsion: k²/d
        const repulsion = (k * k) / distance;
        const fx = (dx / distance) * repulsion;
        const fy = (dy / distance) * repulsion;

        posA.fx -= fx;
        posA.fy -= fy;
        posB.fx += fx;
        posB.fy += fy;
      }
    }

    // Calculate attraction forces (connected nodes)
    edges.forEach(edge => {
      const posSource = positions.get(edge.source);
      const posTarget = positions.get(edge.target);

      if (!posSource || !posTarget) return;

      const dx = posTarget.x - posSource.x;
      const dy = posTarget.y - posSource.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 0.1;

      // Fruchterman-Reingold attraction: d²/k
      const attraction = (distance * distance) / k;
      const fx = (dx / distance) * attraction;
      const fy = (dy / distance) * attraction;

      posSource.fx += fx;
      posSource.fy += fy;
      posTarget.fx -= fx;
      posTarget.fy -= fy;
    });

    // Apply stronger directional constraints for clear layering
    // Increase force strength to maintain clear horizontal/vertical bands
    const directionalForce = currentTemp * 0.3; // Increased from 0.1 to 0.3 for stronger layering
    positions.forEach((pos, nodeId) => {
      const node = nodes.find(n => n.id === nodeId);
      if (!node) return;

      // Get level nodes for horizontal distribution
      const levelNodes = nodesByLevel.get(pos.level) || [];
      const nodeIndex = levelNodes.findIndex(n => n.id === nodeId);
      const nodesInLevel = levelNodes.length;

      let targetX = pos.x;
      let targetY = pos.y;

      switch (direction) {
        case 'TB':
          // Maintain horizontal distribution within level
          const levelSpacing = nodesInLevel > 0 ? width / (nodesInLevel + 1) : width / 2;
          targetX = nodesInLevel > 0 ? levelSpacing * (nodeIndex + 1) : width / 2;
          // Strong vertical constraint to level band
          targetY = (height / (numLevels + 1)) * (pos.level + 1);
          break;
        case 'BT':
          const levelSpacingBT = nodesInLevel > 0 ? width / (nodesInLevel + 1) : width / 2;
          targetX = nodesInLevel > 0 ? levelSpacingBT * (nodeIndex + 1) : width / 2;
          targetY = height - (height / (numLevels + 1)) * (pos.level + 1);
          break;
        case 'LR':
          const levelSpacingLR = nodesInLevel > 0 ? height / (nodesInLevel + 1) : height / 2;
          targetX = (width / (numLevels + 1)) * (pos.level + 1);
          targetY = nodesInLevel > 0 ? levelSpacingLR * (nodeIndex + 1) : height / 2;
          break;
        case 'RL':
          const levelSpacingRL = nodesInLevel > 0 ? height / (nodesInLevel + 1) : height / 2;
          targetX = width - (width / (numLevels + 1)) * (pos.level + 1);
          targetY = nodesInLevel > 0 ? levelSpacingRL * (nodeIndex + 1) : height / 2;
          break;
      }

      const dx = targetX - pos.x;
      const dy = targetY - pos.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Apply force even for small distances to maintain alignment
      if (dist > 10) {
        pos.fx += (dx / dist) * directionalForce;
        pos.fy += (dy / dist) * directionalForce;
      }
    });

    // Update positions with temperature-based movement
    positions.forEach(pos => {
      // Limit force by temperature
      const forceMagnitude = Math.sqrt(pos.fx * pos.fx + pos.fy * pos.fy);
      if (forceMagnitude > currentTemp) {
        pos.fx = (pos.fx / forceMagnitude) * currentTemp;
        pos.fy = (pos.fy / forceMagnitude) * currentTemp;
      }

      // Update position
      pos.x += pos.fx;
      pos.y += pos.fy;

      // Boundary constraints (soft)
      const margin = 100;
      if (pos.x < margin) pos.x = margin + Math.random() * 50;
      if (pos.x > width - margin) pos.x = width - margin - Math.random() * 50;
      if (pos.y < margin) pos.y = margin + Math.random() * 50;
      if (pos.y > height - margin) pos.y = height - margin - Math.random() * 50;
    });

    // Cool down temperature
    currentTemp *= coolingFactor;
  }

  // Convert to output format
  return Array.from(positions.entries()).map(([id, pos]) => ({
    id,
    x: pos.x,
    y: pos.y,
  }));
}

/**
 * Hierarchical layout with orthogonal edge routing
 * Uses Sugiyama-style layering with orthogonal edge paths
 * Minimizes edge crossings and provides clear directional flow
 */
export function hierarchicalOrthogonalLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: {
    levelHeight?: number;
    nodeSpacing?: number;
    direction?: 'TB' | 'BT' | 'LR' | 'RL';
    minimizeCrossings?: boolean;
    width?: number;
    height?: number;
  } = {}
): LayoutPosition[] {
  const {
    levelHeight = 250,
    nodeSpacing = 300,
    direction = 'TB',
    minimizeCrossings = true,
    width = 5000,
    height = 4000,
  } = options;

  // Build dependency graph
  const inDegree = new Map<string, number>();
  const outEdges = new Map<string, string[]>();
  const inEdges = new Map<string, string[]>();

  nodes.forEach(node => {
    inDegree.set(node.id, 0);
    outEdges.set(node.id, []);
    inEdges.set(node.id, []);
  });

  edges.forEach(edge => {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    outEdges.get(edge.source)?.push(edge.target);
    inEdges.get(edge.target)?.push(edge.source);
  });

  // Find root nodes
  const roots: string[] = [];
  inDegree.forEach((degree, nodeId) => {
    if (degree === 0) {
      roots.push(nodeId);
    }
  });

  if (roots.length === 0) {
    nodes.forEach(node => roots.push(node.id));
  }

  // Assign levels using BFS
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

  // Assign unvisited nodes
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

  // Minimize crossings by sorting nodes within each level
  if (minimizeCrossings) {
    nodesByLevel.forEach((nodeIds, level) => {
      if (level === 0) return; // Root level doesn't need sorting

      // Sort nodes by barycenter (average position of neighbors in previous level)
      nodeIds.sort((a, b) => {
        const neighborsA = inEdges.get(a) || [];
        const neighborsB = inEdges.get(b) || [];

        if (neighborsA.length === 0 && neighborsB.length === 0) return 0;
        if (neighborsA.length === 0) return 1;
        if (neighborsB.length === 0) return -1;

        // Calculate barycenter based on positions in previous level
        const prevLevelNodes = nodesByLevel.get(level - 1) || [];
        const prevLevelMap = new Map(prevLevelNodes.map((id, idx) => [id, idx]));

        const barycenterA = neighborsA.reduce((sum, n) => sum + (prevLevelMap.get(n) || 0), 0) / neighborsA.length;
        const barycenterB = neighborsB.reduce((sum, n) => sum + (prevLevelMap.get(n) || 0), 0) / neighborsB.length;

        return barycenterA - barycenterB;
      });
    });
  }

  // Calculate positions
  const positions: LayoutPosition[] = [];
  const maxLevel = Math.max(...Array.from(nodesByLevel.keys()));

  // Calculate center offset for horizontal centering
  const maxLevelWidth = Math.max(...Array.from(nodesByLevel.values()).map(ids => ids.length * nodeSpacing));
  const centerX = width / 2;

  nodesByLevel.forEach((nodeIds, level) => {
    const levelWidth = nodeIds.length * nodeSpacing;
    const startX = centerX - levelWidth / 2 + nodeSpacing / 2;

    nodeIds.forEach((nodeId, index) => {
      let x = startX + index * nodeSpacing;
      let y = level * levelHeight + 200;

      // Apply direction transformation
      let finalX = x;
      let finalY = y;

      switch (direction) {
        case 'TB': // Top to Bottom
          finalX = x;
          finalY = y;
          break;
        case 'BT': // Bottom to Top
          finalX = x;
          finalY = height - y;
          break;
        case 'LR': // Left to Right
          finalX = y;
          finalY = x;
          break;
        case 'RL': // Right to Left
          finalX = width - y;
          finalY = x;
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
    case 'fruchterman-reingold':
      return fruchtermanReingoldLayout(nodes, edges, options);
    case 'hierarchical':
      return hierarchicalLayout(nodes, edges, options);
    case 'hierarchical-orthogonal':
      return hierarchicalOrthogonalLayout(nodes, edges, options);
    case 'grouped':
      return groupedLayout(nodes, edges, options);
    case 'grid':
    default:
      return gridLayout(nodes, options);
  }
}
