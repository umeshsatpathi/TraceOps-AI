import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';

export const GraphLegend: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  const nodeTypes = [
    { label: 'Finding (Critical)', color: '#ef4444', shape: 'diamond' },
    { label: 'Finding (High)', color: '#f97316', shape: 'diamond' },
    { label: 'Finding (Medium)', color: '#f59e0b', shape: 'diamond' },
    { label: 'Finding (Low)', color: '#3b82f6', shape: 'diamond' },
    { label: 'Endpoint', color: '#06b6d4', shape: 'rounded-rect' },
    { label: 'Service', color: '#818cf8', shape: 'hexagon' },
    { label: 'Database', color: '#f59e0b', shape: 'barrel' },
    { label: 'Data Asset (Sensitive)', color: '#ec4899', shape: 'ellipse' },
    { label: 'Data Asset (Public)', color: '#10b981', shape: 'ellipse' },
    { label: 'Evidence', color: '#eab308', shape: 'tag' },
    { label: 'ScanRun', color: '#64748b', shape: 'rectangle' },
  ];

  const edgeTypes = [
    { label: 'AFFECTS', desc: 'Finding ➔ Target' },
    { label: 'EXPOSES', desc: 'Endpoint ➔ Asset' },
    { label: 'CONNECTS_TO', desc: 'Service ➔ Database' },
    { label: 'LOCATED_AT', desc: 'Endpoint ➔ Host' },
    { label: 'EVIDENCE_FOR', desc: 'Evidence ➔ Finding' },
  ];

  return (
    <div style={{
      position: 'absolute',
      bottom: '16px',
      left: '16px',
      backgroundColor: 'rgba(12, 18, 34, 0.92)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '8px',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
      zIndex: 20,
      maxWidth: '360px',
      overflow: 'hidden',
      transition: 'all 0.2s ease',
    }}>
      {/* Header */}
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          backgroundColor: 'rgba(15, 23, 42, 0.7)',
          borderBottom: collapsed ? 'none' : '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-main)' }}>
          <Info size={14} color="var(--color-info)" />
          <span>Graph Legend & Taxonomy</span>
        </div>
        <button
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {collapsed ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Body */}
      {!collapsed && (
        <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-dim)', marginBottom: '6px', letterSpacing: '0.04em' }}>
              NODE TYPES
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px' }}>
              {nodeTypes.map((item) => (
                <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: item.shape === 'ellipse' ? '50%' : item.shape === 'diamond' ? '1px' : '2px',
                      transform: item.shape === 'diamond' ? 'rotate(45deg)' : 'none',
                      backgroundColor: item.color,
                      display: 'inline-block',
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '8px' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-dim)', marginBottom: '6px', letterSpacing: '0.04em' }}>
              RELATIONSHIP TYPES
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {edgeTypes.map((edge) => (
                <div
                  key={edge.label}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '0.68rem',
                    color: 'var(--text-muted)',
                  }}
                  title={edge.desc}
                >
                  <span style={{ color: 'var(--color-info)', fontWeight: 600 }}>{edge.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
