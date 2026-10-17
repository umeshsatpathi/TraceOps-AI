import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Share2,
  ExternalLink,
  Bot,
  AlertCircle,
  Database,
  Globe,
  Tag,
  Loader2,
} from 'lucide-react';
import { GraphEdge, GraphNode } from '../../types';
import { SeverityBadge } from '../common/Badge';

interface GraphNodeDetailsProps {
  selectedNode: GraphNode | null;
  selectedEdge: GraphEdge | null;
  onClose: () => void;
  onExpandNeighbors: (nodeId: string) => void;
  isExpanding?: boolean;
}

export const GraphNodeDetails: React.FC<GraphNodeDetailsProps> = ({
  selectedNode,
  selectedEdge,
  onClose,
  onExpandNeighbors,
  isExpanding = false,
}) => {
  const navigate = useNavigate();

  if (!selectedNode && !selectedEdge) return null;

  // Selected Edge View
  if (selectedEdge) {
    return (
      <div style={{
        position: 'absolute',
        top: '64px',
        right: '16px',
        width: '320px',
        maxHeight: 'calc(100% - 96px)',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.5)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 30,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(30, 41, 59, 0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Share2 size={16} color="var(--color-info)" />
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-main)' }}>
              Relationship
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Type</span>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-info)', marginTop: '2px' }}>
              {selectedEdge.type}
            </div>
          </div>
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Source Entity</span>
            <div style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: '2px', wordBreak: 'break-all' }}>
              {selectedEdge.source}
            </div>
          </div>
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Target Entity</span>
            <div style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: '2px', wordBreak: 'break-all' }}>
              {selectedEdge.target}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Selected Node View
  const node = selectedNode!;
  const isFinding = node.label.toLowerCase() === 'finding';
  const findingId = isFinding
    ? (node.properties?.finding_id || node.id.replace(/^finding-/, ''))
    : null;

  return (
    <div style={{
      position: 'absolute',
      top: '64px',
      right: '16px',
      width: '360px',
      maxHeight: 'calc(100% - 96px)',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '10px',
      backdropFilter: 'blur(16px)',
      boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 30,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'rgba(30, 41, 59, 0.5)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Tag size={16} color="var(--color-info)" />
          <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-main)' }}>
            {node.label} Entity
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Node ID */}
        <div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Identifier</span>
          <div style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '2px', wordBreak: 'break-all' }}>
            {node.id}
          </div>
        </div>

        {/* Severity if Finding */}
        {isFinding && node.properties?.severity && (
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Severity</span>
            <div style={{ marginTop: '4px' }}>
              <SeverityBadge severity={node.properties.severity} />
            </div>
          </div>
        )}

        {/* Properties table */}
        <div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Properties</span>
          <div style={{
            marginTop: '6px',
            backgroundColor: 'rgba(7, 11, 20, 0.6)',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
            padding: '8px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}>
            {Object.entries(node.properties || {}).map(([key, value]) => {
              const strVal = typeof value === 'object' ? JSON.stringify(value) : String(value);
              return (
                <div key={key} style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{key}</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', wordBreak: 'break-all' }}>{strVal}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
          <button
            onClick={() => onExpandNeighbors(node.id)}
            disabled={isExpanding}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.35)',
              color: 'var(--color-info)',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: isExpanding ? 'not-allowed' : 'pointer',
              transition: 'background 0.15s ease',
            }}
          >
            {isExpanding ? <Loader2 size={14} className="pulse-indicator" /> : <Share2 size={14} />}
            <span>{isExpanding ? 'Expanding Neighbors...' : 'Expand 1-Hop Neighbors'}</span>
          </button>

          {isFinding && findingId && (
            <button
              onClick={() => navigate(`/findings/${findingId}`)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                padding: '8px 14px',
                borderRadius: '6px',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <AlertCircle size={14} />
              <span>Inspect Finding {findingId}</span>
            </button>
          )}

          <button
            onClick={() => navigate('/investigations')}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: 'rgba(99, 102, 241, 0.12)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              color: '#818cf8',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Bot size={14} />
            <span>AI Root-Cause Investigation</span>
          </button>
        </div>
      </div>
    </div>
  );
};
