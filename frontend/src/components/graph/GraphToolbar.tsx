import React from 'react';
import {
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  RefreshCw,
  Sliders,
  Layers,
} from 'lucide-react';

interface GraphToolbarProps {
  layoutName: string;
  onChangeLayout: (layout: string) => void;
  onFit: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onRefresh: () => void;
  nodeCount: number;
  edgeCount: number;
  isTruncated?: boolean;
}

export const GraphToolbar: React.FC<GraphToolbarProps> = ({
  layoutName,
  onChangeLayout,
  onFit,
  onZoomIn,
  onZoomOut,
  onReset,
  onRefresh,
  nodeCount,
  edgeCount,
  isTruncated = false,
}) => {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 16px',
      backgroundColor: 'rgba(12, 18, 34, 0.95)',
      borderBottom: '1px solid var(--border-subtle)',
      backdropFilter: 'blur(12px)',
      gap: '12px',
      flexWrap: 'wrap',
    }}>
      {/* Left: View Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={onFit}
          title="Fit graph to view"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-main)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'background 0.15s ease',
          }}
        >
          <Maximize2 size={14} color="var(--color-info)" />
          Fit View
        </button>

        <button
          onClick={onZoomIn}
          title="Zoom in"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-main)',
            padding: '6px 10px',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          <ZoomIn size={14} />
        </button>

        <button
          onClick={onZoomOut}
          title="Zoom out"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-main)',
            padding: '6px 10px',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          <ZoomOut size={14} />
        </button>

        <button
          onClick={onReset}
          title="Reset position"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-main)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            cursor: 'pointer',
          }}
        >
          <RotateCcw size={14} />
          Reset
        </button>

        {/* Layout dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
          <Sliders size={14} color="var(--text-dim)" />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Layout:</span>
          <select
            value={layoutName}
            onChange={(e) => onChangeLayout(e.target.value)}
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-main)',
              fontSize: '0.8rem',
              padding: '6px 10px',
              borderRadius: '6px',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="fcose">Force-Directed (fCoSE)</option>
            <option value="breadthfirst">Hierarchical Tree</option>
            <option value="circle">Circular</option>
            <option value="concentric">Concentric Rings</option>
            <option value="grid">Orthogonal Grid</option>
          </select>
        </div>
      </div>

      {/* Right: Refresh & Graph Statistics */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          onClick={onRefresh}
          title="Reload graph data from backend"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(6, 182, 212, 0.12)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
            color: 'var(--color-info)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={13} />
          Refresh
        </button>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
          padding: '4px 10px',
          borderRadius: '6px',
          border: '1px solid var(--border-subtle)',
        }}>
          <Layers size={14} color="var(--color-info)" />
          <span><strong>{nodeCount}</strong> Nodes</span>
          <span style={{ color: 'var(--border-subtle)' }}>|</span>
          <span><strong>{edgeCount}</strong> Edges</span>
          {isTruncated && (
            <span style={{
              marginLeft: '4px',
              color: 'var(--color-medium)',
              fontSize: '0.72rem',
              fontWeight: 600,
            }}>
              (Truncated)
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
