import React from 'react';
import { Search, Filter, RotateCcw } from 'lucide-react';
import { GraphNode } from '../../types';

interface GraphFiltersProps {
  nodes: GraphNode[];
  searchQuery: string;
  onSearchChange: (query: string) => void;
  hiddenNodeTypes: Set<string>;
  onToggleNodeType: (type: string) => void;
  onResetFilters: () => void;
}

export const GraphFilters: React.FC<GraphFiltersProps> = ({
  nodes,
  searchQuery,
  onSearchChange,
  hiddenNodeTypes,
  onToggleNodeType,
  onResetFilters,
}) => {
  // Compute counts per node type
  const typeCounts = nodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.label] = (acc[n.label] || 0) + 1;
    return acc;
  }, {});

  const availableTypes = Object.keys(typeCounts).sort();

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '8px 16px',
      backgroundColor: 'rgba(15, 23, 42, 0.8)',
      borderBottom: '1px solid var(--border-subtle)',
      gap: '14px',
      flexWrap: 'wrap',
    }}>
      {/* Search Input */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        backgroundColor: 'rgba(7, 11, 20, 0.6)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '4px 10px',
        minWidth: '240px',
      }}>
        <Search size={14} color="var(--text-dim)" />
        <input
          type="text"
          placeholder="Filter node ID, title, path..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            background: 'none',
            border: 'none',
            outline: 'none',
            color: 'var(--text-main)',
            fontSize: '0.8rem',
            width: '100%',
          }}
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange('')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              fontSize: '0.75rem',
            }}
          >
            ×
          </button>
        )}
      </div>

      {/* Node Type Visibility Toggles */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>
          <Filter size={12} />
          <span>FILTER:</span>
        </div>

        {availableTypes.map((type) => {
          const isHidden = hiddenNodeTypes.has(type);
          const count = typeCounts[type];
          return (
            <button
              key={type}
              onClick={() => onToggleNodeType(type)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '0.72rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: isHidden ? 'rgba(255, 255, 255, 0.03)' : 'rgba(6, 182, 212, 0.12)',
                border: isHidden ? '1px dashed rgba(255, 255, 255, 0.1)' : '1px solid rgba(6, 182, 212, 0.3)',
                color: isHidden ? 'var(--text-dim)' : 'var(--color-info)',
                opacity: isHidden ? 0.6 : 1,
                transition: 'all 0.15s ease',
              }}
              title={isHidden ? `Show ${type} nodes` : `Hide ${type} nodes`}
            >
              <span>{type}</span>
              <span style={{
                backgroundColor: isHidden ? 'rgba(255, 255, 255, 0.05)' : 'rgba(6, 182, 212, 0.25)',
                padding: '1px 5px',
                borderRadius: '999px',
                fontSize: '0.65rem',
              }}>
                {count}
              </span>
            </button>
          );
        })}

        {hiddenNodeTypes.size > 0 && (
          <button
            onClick={onResetFilters}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'none',
              border: 'none',
              color: 'var(--color-medium)',
              fontSize: '0.72rem',
              cursor: 'pointer',
              marginLeft: '4px',
            }}
          >
            <RotateCcw size={11} />
            Reset
          </button>
        )}
      </div>
    </div>
  );
};
