import React, { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { GraphEdge, GraphNode } from '../../types';

// Register fcose layout extension once safely
try {
  cytoscape.use(fcose);
} catch {
  // Already registered
}

export interface GraphCanvasHandle {
  fit: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  reset: () => void;
  centerSelected: () => void;
}

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layoutName: string;
  onSelectNode: (node: GraphNode | null) => void;
  onSelectEdge: (edge: GraphEdge | null) => void;
  hiddenNodeTypes: Set<string>;
  searchQuery?: string;
}

export const GraphCanvas = forwardRef<GraphCanvasHandle, GraphCanvasProps>(({
  nodes,
  edges,
  layoutName,
  onSelectNode,
  onSelectEdge,
  hiddenNodeTypes,
  searchQuery = '',
}, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Expose imperative toolbar controls
  useImperativeHandle(ref, () => ({
    fit: () => {
      cyRef.current?.fit(undefined, 50);
    },
    zoomIn: () => {
      if (cyRef.current) {
        const currentZoom = cyRef.current.zoom();
        cyRef.current.zoom({
          level: currentZoom * 1.3,
          renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 },
        });
      }
    },
    zoomOut: () => {
      if (cyRef.current) {
        const currentZoom = cyRef.current.zoom();
        cyRef.current.zoom({
          level: currentZoom / 1.3,
          renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 },
        });
      }
    },
    reset: () => {
      if (cyRef.current) {
        cyRef.current.reset();
        cyRef.current.fit(undefined, 50);
      }
    },
    centerSelected: () => {
      if (cyRef.current) {
        const selected = cyRef.current.$(':selected');
        if (selected.length > 0) {
          cyRef.current.center(selected);
        }
      }
    },
  }));

  const getNodeColor = (node: GraphNode): string => {
    const label = (node.label || '').toLowerCase();
    if (label === 'finding') {
      const sev = (node.properties?.severity || '').toLowerCase();
      const sevLvl = Number(node.properties?.severity_level || 0);
      if (sev === 'critical' || sevLvl >= 5) return '#ef4444';
      if (sev === 'high' || sevLvl === 4) return '#f97316';
      if (sev === 'medium' || sevLvl === 3) return '#f59e0b';
      if (sev === 'low' || sevLvl === 2) return '#3b82f6';
      return '#06b6d4';
    }
    if (label === 'endpoint') return '#06b6d4';
    if (label === 'service') return '#818cf8';
    if (label === 'database') return '#f59e0b';
    if (label === 'dataasset') {
      return node.properties?.classification === 'sensitive' ? '#ec4899' : '#10b981';
    }
    if (label === 'website') return '#3b82f6';
    if (label === 'evidence') return '#eab308';
    if (label === 'scanrun' || label === 'scan') return '#64748b';
    return '#94a3b8';
  };

  const getNodeShape = (label: string): string => {
    const l = label.toLowerCase();
    if (l === 'finding') return 'diamond';
    if (l === 'endpoint') return 'round-rectangle';
    if (l === 'service') return 'hexagon';
    if (l === 'database') return 'barrel';
    if (l === 'dataasset') return 'ellipse';
    if (l === 'website') return 'rectangle';
    if (l === 'evidence') return 'round-tag';
    return 'round-rectangle';
  };

  // 1. Mount effect: initialize Cytoscape instance once
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            color: '#ffffff',
            'font-size': '11px',
            'font-weight': 600,
            'font-family': 'Inter, sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            shape: 'data(shape)' as any,
            width: 38,
            height: 38,
            'border-width': 2,
            'border-color': 'rgba(255, 255, 255, 0.4)',
            'text-background-opacity': 0.75,
            'text-background-color': '#070b14',
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#38bdf8',
            'underlay-color': '#38bdf8',
            'underlay-padding': 4,
            'underlay-opacity': 0.6,
          } as any,
        },
        {
          selector: 'node.highlighted',
          style: {
            'border-width': 4,
            'border-color': '#22d3ee',
            'underlay-color': '#22d3ee',
            'underlay-padding': 4,
            'underlay-opacity': 0.6,
          } as any,
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': 'rgba(148, 163, 184, 0.45)',
            'target-arrow-color': 'rgba(148, 163, 184, 0.75)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9px',
            color: '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
            'text-background-opacity': 0.65,
            'text-background-color': '#070b14',
            'text-background-padding': '2px',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            width: 3.5,
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
          },
        },
      ],
      wheelSensitivity: 0.25,
    });

    cy.on('tap', 'node', (evt: EventObject) => {
      const raw = evt.target.data('rawNode');
      onSelectNode(raw || null);
      onSelectEdge(null);
    });

    cy.on('tap', 'edge', (evt: EventObject) => {
      const raw = evt.target.data('rawEdge');
      onSelectEdge(raw || null);
      onSelectNode(null);
    });

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        onSelectNode(null);
        onSelectEdge(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  // 2. Data update effect: sync elements and run layout when nodes/edges/filters change
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const visibleNodes = nodes.filter((n) => !hiddenNodeTypes.has(n.label));
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
    const visibleEdges = edges.filter(
      (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
    );

    const elements = [
      ...visibleNodes.map((n) => ({
        data: {
          id: n.id,
          label: n.properties?.name || n.properties?.title || n.properties?.path || n.id,
          type: n.label,
          color: getNodeColor(n),
          shape: getNodeShape(n.label),
          rawNode: n,
        },
      })),
      ...visibleEdges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.type,
          rawEdge: e,
        },
      })),
    ];

    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });

    // Execute requested layout
    const layoutConfig: any = {
      name: layoutName,
      animate: true,
      animationDuration: 400,
      fit: true,
      padding: 50,
    };

    if (layoutName === 'fcose') {
      layoutConfig.quality = 'proof';
      layoutConfig.randomize = false;
      layoutConfig.animate = true;
      layoutConfig.nodeRepulsion = 4500;
      layoutConfig.idealEdgeLength = 90;
    }

    try {
      cy.layout(layoutConfig).run();
    } catch {
      // Fallback to breadthfirst if chosen layout fails
      cy.layout({ name: 'breadthfirst', animate: true, fit: true, padding: 50 }).run();
    }
  }, [nodes, edges, layoutName, hiddenNodeTypes]);

  // 3. Search highlighting effect
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass('highlighted');
    if (searchQuery.trim().length > 0) {
      const q = searchQuery.toLowerCase().trim();
      cy.nodes().forEach((n) => {
        const id = n.id().toLowerCase();
        const lbl = (n.data('label') || '').toLowerCase();
        if (id.includes(q) || lbl.includes(q)) {
          n.addClass('highlighted');
        }
      });
    }
  }, [searchQuery]);

  return <div id="cytoscape-container" ref={containerRef} />;
});

GraphCanvas.displayName = 'GraphCanvas';
