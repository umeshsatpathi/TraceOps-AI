import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import { GraphCanvas, GraphCanvasHandle } from '../components/graph/GraphCanvas';
import { GraphToolbar } from '../components/graph/GraphToolbar';
import { GraphLegend } from '../components/graph/GraphLegend';
import { GraphNodeDetails } from '../components/graph/GraphNodeDetails';
import { GraphFilters } from '../components/graph/GraphFilters';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';
import { getGraphView, getNodeNeighbors } from '../services/api';
import { GraphNode, GraphEdge, GraphMeta } from '../types';
import { AlertTriangle } from 'lucide-react';

export const GraphPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: string }>();
  const [searchParams] = useSearchParams();
  const focusNodeId = searchParams.get('focus');

  const canvasRef = useRef<GraphCanvasHandle>(null);

  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [meta, setMeta] = useState<GraphMeta>({ node_count: 0, edge_count: 0, truncated: false });

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanding, setIsExpanding] = useState<boolean>(false);

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);

  const [layoutName, setLayoutName] = useState<string>('fcose');
  const [hiddenNodeTypes, setHiddenNodeTypes] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getGraphView({ project_id: currentProject, limit: 150 });
      setNodes(res.nodes || []);
      setEdges(res.edges || []);
      setMeta(res.meta || { node_count: res.nodes?.length || 0, edge_count: res.edges?.length || 0, truncated: false });

      // If a focus node was requested in query param, select it
      if (focusNodeId) {
        const found = res.nodes?.find((n) => n.id === focusNodeId || n.id.includes(focusNodeId));
        if (found) {
          setSelectedNode(found);
          setSearchQuery(found.id);
        }
      }
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err.message || 'Failed to load graph visualization');
    } finally {
      setLoading(false);
    }
  }, [currentProject, focusNodeId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Handle 1-hop neighbor expansion
  const handleExpandNeighbors = async (nodeId: string) => {
    setIsExpanding(true);
    try {
      const res = await getNodeNeighbors(nodeId, { depth: 1, limit: 50 });
      if (res && res.neighbors) {
        setNodes((prevNodes) => {
          const existingIds = new Set(prevNodes.map((n) => n.id));
          const newNeighbors = res.neighbors.filter((n) => !existingIds.has(n.id));
          return [...prevNodes, ...newNeighbors];
        });

        setEdges((prevEdges) => {
          const existingEdgeKeys = new Set(
            prevEdges.map((e) => e.id || `${e.source}-${e.target}-${e.type}`)
          );
          const newEdges = (res.edges || []).filter(
            (e) => !existingEdgeKeys.has(e.id || `${e.source}-${e.target}-${e.type}`)
          );
          return [...prevEdges, ...newEdges];
        });
      }
    } catch (err: any) {
      console.error('Failed to expand neighbors:', err);
    } finally {
      setIsExpanding(false);
    }
  };

  const handleToggleNodeType = (type: string) => {
    setHiddenNodeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const handleResetFilters = () => {
    setHiddenNodeTypes(new Set());
    setSearchQuery('');
  };

  if (loading) {
    return <LoadingState message="Loading threat graph topology from FalkorDB..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Graph Exploration Failed"
        message={error}
        onRetry={loadGraph}
      />
    );
  }

  if (nodes.length === 0) {
    return (
      <EmptyState
        title="No Graph Entities Discovered"
        message="No security nodes or relationship edges were found for this project. Run an initial scan to seed findings and topology."
      />
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 120px)',
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '12px',
      overflow: 'hidden',
      position: 'relative',
    }}>
      {/* Truncation notification */}
      {meta.truncated && (
        <div style={{
          backgroundColor: 'rgba(245, 158, 11, 0.15)',
          borderBottom: '1px solid rgba(245, 158, 11, 0.3)',
          padding: '6px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.78rem',
          color: '#fbbf24',
        }}>
          <AlertTriangle size={14} />
          <span>
            Graph rendering is truncated to {meta.node_count} nodes for interactive performance. Use node expansion or filters to explore deeper dependencies.
          </span>
        </div>
      )}

      {/* Toolbar */}
      <GraphToolbar
        layoutName={layoutName}
        onChangeLayout={setLayoutName}
        onFit={() => canvasRef.current?.fit()}
        onZoomIn={() => canvasRef.current?.zoomIn()}
        onZoomOut={() => canvasRef.current?.zoomOut()}
        onReset={() => canvasRef.current?.reset()}
        onRefresh={loadGraph}
        nodeCount={nodes.length}
        edgeCount={edges.length}
        isTruncated={meta.truncated}
      />

      {/* Filters Bar */}
      <GraphFilters
        nodes={nodes}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        hiddenNodeTypes={hiddenNodeTypes}
        onToggleNodeType={handleToggleNodeType}
        onResetFilters={handleResetFilters}
      />

      {/* Main Canvas Area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <GraphCanvas
          ref={canvasRef}
          nodes={nodes}
          edges={edges}
          layoutName={layoutName}
          onSelectNode={setSelectedNode}
          onSelectEdge={setSelectedEdge}
          hiddenNodeTypes={hiddenNodeTypes}
          searchQuery={searchQuery}
        />

        {/* Legend */}
        <GraphLegend />

        {/* Details Drawer */}
        <GraphNodeDetails
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onClose={() => {
            setSelectedNode(null);
            setSelectedEdge(null);
          }}
          onExpandNeighbors={handleExpandNeighbors}
          isExpanding={isExpanding}
        />
      </div>
    </div>
  );
};
