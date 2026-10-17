import React, { useEffect, useState, useCallback } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { getFindings } from '../services/api';
import { FindingSummary, PaginationMeta } from '../types';
import { SeverityBadge, StatusBadge } from '../components/common/Badge';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';

export const FindingsPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [findings, setFindings] = useState<FindingSummary[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({ limit: 20, offset: 0, total: 0 });

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const loadFindings = useCallback(async (offset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getFindings({
        project_id: currentProject,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        limit: pagination.limit,
        offset,
      });
      setFindings(res.items || []);
      setPagination(res.pagination || { limit: 20, offset, total: res.items?.length || 0 });
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err.message || 'Failed to fetch findings');
    } finally {
      setLoading(false);
    }
  }, [currentProject, severityFilter, statusFilter, pagination.limit]);

  useEffect(() => {
    loadFindings(0);
  }, [loadFindings]);

  // Client-side text search refinement
  const filteredFindings = findings.filter((f) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      f.id.toLowerCase().includes(q) ||
      f.title.toLowerCase().includes(q) ||
      f.category.toLowerCase().includes(q) ||
      f.source.toLowerCase().includes(q)
    );
  });

  const currentPage = Math.floor(pagination.offset / pagination.limit) + 1;
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.limit));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert size={26} color="var(--color-critical)" />
            Security Findings
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: '2px' }}>
            Triage, investigate, and remediate identified vulnerabilities for project <strong>{currentProject}</strong>
          </p>
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Showing <strong>{filteredFindings.length}</strong> of <strong>{pagination.total}</strong> findings
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel" style={{
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap',
      }}>
        {/* Search Input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          backgroundColor: 'rgba(7, 11, 20, 0.6)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '8px',
          padding: '8px 14px',
          minWidth: '280px',
          flex: 1,
        }}>
          <Search size={16} color="var(--text-dim)" />
          <input
            type="text"
            placeholder="Search by ID (e.g. F-001), title, category..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'none',
              border: 'none',
              outline: 'none',
              color: 'var(--text-main)',
              fontSize: '0.88rem',
              width: '100%',
            }}
          />
        </div>

        {/* Filter Dropdowns */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Severity */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600 }}>SEVERITY:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                fontSize: '0.82rem',
                padding: '6px 12px',
                borderRadius: '6px',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600 }}>STATUS:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                fontSize: '0.82rem',
                padding: '6px 12px',
                borderRadius: '6px',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="all">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="REMEDIATED">REMEDIATED</option>
              <option value="INCONCLUSIVE">INCONCLUSIVE</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Content Area */}
      {loading ? (
        <LoadingState message="Retrieving security findings list..." />
      ) : error ? (
        <ErrorState title="Findings Unavailable" message={error} onRetry={() => loadFindings(pagination.offset)} />
      ) : filteredFindings.length === 0 ? (
        <EmptyState
          title="No Findings Match Filter Criteria"
          message="No security vulnerabilities were found matching your current search parameters. Clear your filters or run a scan."
        />
      ) : (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  color: 'var(--text-dim)',
                  fontSize: '0.72rem',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}>
                  <th style={{ padding: '14px 18px', width: '110px' }}>ID</th>
                  <th style={{ padding: '14px 18px' }}>Title & Description</th>
                  <th style={{ padding: '14px 18px', width: '110px' }}>Severity</th>
                  <th style={{ padding: '14px 18px', width: '110px' }}>Status</th>
                  <th style={{ padding: '14px 18px', width: '150px' }}>Category</th>
                  <th style={{ padding: '14px 18px', width: '140px' }}>Scanner</th>
                  <th style={{ padding: '14px 18px', width: '90px', textAlign: 'center' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredFindings.map((finding) => (
                  <tr
                    key={finding.id}
                    onClick={() => navigate(`/findings/${finding.id}`)}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(30, 41, 59, 0.5)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    {/* Canonical ID */}
                    <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-info)' }}>
                      {finding.id}
                    </td>

                    {/* Title */}
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{finding.title}</div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                        Type: {finding.type}
                      </div>
                    </td>

                    {/* Severity */}
                    <td style={{ padding: '14px 18px' }}>
                      <SeverityBadge severity={finding.severity} />
                    </td>

                    {/* Status */}
                    <td style={{ padding: '14px 18px' }}>
                      <StatusBadge status={finding.status} />
                    </td>

                    {/* Category */}
                    <td style={{ padding: '14px 18px', color: 'var(--text-muted)' }}>
                      {finding.category}
                    </td>

                    {/* Scanner */}
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-muted)',
                      }}>
                        {finding.source}
                      </span>
                    </td>

                    {/* Inspect Link */}
                    <td style={{ padding: '14px 18px', textAlign: 'center' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/findings/${finding.id}`);
                        }}
                        style={{
                          backgroundColor: 'rgba(6, 182, 212, 0.1)',
                          border: '1px solid rgba(6, 182, 212, 0.25)',
                          color: 'var(--color-info)',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div style={{
            padding: '14px 20px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
              Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                disabled={pagination.offset === 0}
                onClick={() => loadFindings(Math.max(0, pagination.offset - pagination.limit))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  backgroundColor: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid var(--border-subtle)',
                  color: pagination.offset === 0 ? 'var(--text-dim)' : 'var(--text-main)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  cursor: pagination.offset === 0 ? 'not-allowed' : 'pointer',
                }}
              >
                <ChevronLeft size={14} /> Previous
              </button>

              <button
                disabled={pagination.offset + pagination.limit >= pagination.total}
                onClick={() => loadFindings(pagination.offset + pagination.limit)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  backgroundColor: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid var(--border-subtle)',
                  color: pagination.offset + pagination.limit >= pagination.total ? 'var(--text-dim)' : 'var(--text-main)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  cursor: pagination.offset + pagination.limit >= pagination.total ? 'not-allowed' : 'pointer',
                }}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
