import React, { useEffect, useState, useCallback } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  SearchCode,
  Network,
  Bot,
  Radar,
  ArrowRight,
  TrendingUp,
  Clock,
  Layers,
  CheckCircle2,
  AlertOctagon,
} from 'lucide-react';
import { getFindings, getScans, getGraphView } from '../services/api';
import { FindingSummary, ScanResponse, GraphMeta } from '../types';
import { SeverityBadge, StatusBadge } from '../components/common/Badge';
import { LoadingState, ErrorState } from '../components/common/FeedbackStates';

export const OverviewPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [findings, setFindings] = useState<FindingSummary[]>([]);
  const [scans, setScans] = useState<ScanResponse[]>([]);
  const [graphMeta, setGraphMeta] = useState<GraphMeta>({ node_count: 0, edge_count: 0, truncated: false });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [findingsRes, scansRes, graphRes] = await Promise.all([
        getFindings({ project_id: currentProject, limit: 100 }),
        getScans({ project_id: currentProject, limit: 5 }),
        getGraphView({ project_id: currentProject, limit: 1 }),
      ]);

      setFindings(findingsRes.items || []);
      setScans(scansRes.items || []);
      setGraphMeta(graphRes.meta || { node_count: 0, edge_count: 0, truncated: false });
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err.message || 'Failed to load project overview');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return <LoadingState message="Aggregating security posture and graph metrics..." />;
  }

  if (error) {
    return <ErrorState title="Overview Error" message={error} onRetry={loadData} />;
  }

  // Calculate metrics
  const totalFindings = findings.length;
  const criticalCount = findings.filter((f) => f.severity === 'critical').length;
  const highCount = findings.filter((f) => f.severity === 'high').length;
  const mediumCount = findings.filter((f) => f.severity === 'medium').length;
  const lowCount = findings.filter((f) => f.severity === 'low' || f.severity === 'informational').length;

  const openCount = findings.filter((f) => f.status === 'OPEN').length;
  const confirmedCount = findings.filter((f) => f.status === 'CONFIRMED').length;
  const remediatedCount = findings.filter((f) => f.status === 'REMEDIATED').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Banner / Welcome */}
      <div className="glass-panel" style={{
        padding: '24px 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.6) 100%)',
        border: '1px solid var(--border-subtle)',
      }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', color: '#ffffff', marginBottom: '6px' }}>
            Security Posture & Knowledge Graph
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Real-time multi-hop threat analysis and graph-grounded remediation for active project: <strong style={{ color: 'var(--color-info)' }}>{currentProject}</strong>
          </p>
        </div>
        <button
          onClick={() => navigate('/investigations')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'rgba(6, 182, 212, 0.15)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            color: 'var(--color-info)',
            padding: '10px 18px',
            borderRadius: '8px',
            fontSize: '0.88rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <Bot size={18} />
          <span>Launch AI Investigation</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>Total Findings</span>
            <ShieldAlert size={18} color="var(--color-info)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-main)' }}>{totalFindings}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {openCount} Open · {confirmedCount} Confirmed
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid var(--color-critical)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>Critical Severity</span>
            <AlertOctagon size={18} color="var(--color-critical)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-critical)' }}>{criticalCount}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Immediate remediation recommended</div>
        </div>

        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid var(--color-high)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>High Severity</span>
            <TrendingUp size={18} color="var(--color-high)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-high)' }}>{highCount}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Multi-hop exposure detected</div>
        </div>

        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid var(--color-medium)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>Medium / Low</span>
            <CheckCircle2 size={18} color="var(--color-medium)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-medium)' }}>{mediumCount + lowCount}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>{mediumCount} Medium · {lowCount} Low</div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>Graph Topology</span>
            <Network size={18} color="#818cf8" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#818cf8' }}>{graphMeta.node_count}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {graphMeta.edge_count} Relationships tracked
          </div>
        </div>
      </div>

      {/* Two Column Section: Recent Findings & Recent Scans */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '24px' }}>
        {/* Recent Findings Card */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <SearchCode size={20} color="var(--color-info)" />
              <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Recent Findings</h2>
            </div>
            <button
              onClick={() => navigate('/findings')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'none',
                border: 'none',
                color: 'var(--color-info)',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              View All <ArrowRight size={14} />
            </button>
          </div>

          {findings.length === 0 ? (
            <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', padding: '24px 0', textAlign: 'center' }}>
              No findings recorded for this project yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {findings.slice(0, 5).map((f) => (
                <div
                  key={f.id}
                  onClick={() => navigate(`/findings/${f.id}`)}
                  className="glass-card"
                  style={{
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <SeverityBadge severity={f.severity} />
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        {f.title}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        ID: {f.id} · Source: {f.source}
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={f.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Scans Card */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Radar size={20} color="var(--color-info)" />
              <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Recent Scan Executions</h2>
            </div>
            <button
              onClick={() => navigate('/scans')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'none',
                border: 'none',
                color: 'var(--color-info)',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Scan Console <ArrowRight size={14} />
            </button>
          </div>

          {scans.length === 0 ? (
            <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', padding: '24px 0', textAlign: 'center' }}>
              No scanner executions registered yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {scans.slice(0, 5).map((s) => (
                <div
                  key={s.id}
                  className="glass-card"
                  style={{
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      backgroundColor: 'rgba(6, 182, 212, 0.1)',
                      border: '1px solid rgba(6, 182, 212, 0.25)',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--color-info)',
                      fontFamily: 'var(--font-mono)',
                    }}>
                      {s.scanner}
                    </div>
                    <div>
                      <div style={{ fontSize: '0.84rem', color: 'var(--text-main)', fontWeight: 500 }}>
                        {s.findings_count} findings discovered
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} />
                        {new Date(s.started_at).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <span className={`badge ${
                    s.status.includes('findings') ? 'badge-critical' : s.status.includes('clean') ? 'badge-success' : 'badge-gray'
                  }`}>
                    {s.status.replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Feature Navigation Banners */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        <div
          onClick={() => navigate('/graph')}
          className="glass-card"
          style={{
            padding: '20px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Network size={22} color="#818cf8" />
            </div>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)' }}>Threat Graph Explorer</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Visualize endpoints, databases, and sensitive assets</div>
            </div>
          </div>
          <ArrowRight size={18} color="var(--text-dim)" />
        </div>

        <div
          onClick={() => navigate('/investigations')}
          className="glass-card"
          style={{
            padding: '20px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Bot size={22} color="var(--color-info)" />
            </div>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)' }}>AI Security Investigations</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Multi-hop grounding with verified factual evidence</div>
            </div>
          </div>
          <ArrowRight size={18} color="var(--text-dim)" />
        </div>

        <div
          onClick={() => navigate('/scans')}
          className="glass-card"
          style={{
            padding: '20px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Radar size={22} color="var(--color-success)" />
            </div>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)' }}>Scan & Verification Engine</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Run baseline scans and deterministic BOLA verification</div>
            </div>
          </div>
          <ArrowRight size={18} color="var(--text-dim)" />
        </div>
      </div>
    </div>
  );
};
