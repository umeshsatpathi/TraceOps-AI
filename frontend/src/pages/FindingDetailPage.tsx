import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  Network,
  Bot,
  Layers,
  Clock,
  Fingerprint,
  CheckCircle2,
  AlertTriangle,
  Server,
  Database,
  Lock,
  Unlock,
  FileText,
  Activity,
  ArrowRight,
} from 'lucide-react';
import { getFindingById } from '../services/api';
import { FindingDetail } from '../types';
import { SeverityBadge, StatusBadge } from '../components/common/Badge';
import { LoadingState, ErrorState } from '../components/common/FeedbackStates';

export const FindingDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [finding, setFinding] = useState<FindingDetail | null>(null);

  const loadFinding = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getFindingById(id);
      setFinding(data);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err.message || `Failed to fetch finding ${id}`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadFinding();
  }, [loadFinding]);

  if (loading) {
    return <LoadingState message={`Retrieving graph groundings for finding ${id}...`} />;
  }

  if (error || !finding) {
    return (
      <ErrorState
        title="Finding Not Found"
        message={error || `Could not find security finding with identifier ${id}`}
        onRetry={loadFinding}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Back button and navigation breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button
          onClick={() => navigate('/findings')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'rgba(30, 41, 59, 0.6)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '0.82rem',
            cursor: 'pointer',
          }}
        >
          <ArrowLeft size={14} /> Back to Findings
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => navigate(`/graph?focus=${finding.id}`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.35)',
              color: '#818cf8',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Network size={15} />
            <span>Threat Graph</span>
          </button>

          <button
            onClick={() => navigate(`/investigations?finding_id=${finding.id}`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.35)',
              color: 'var(--color-info)',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Bot size={15} />
            <span>AI Investigation</span>
          </button>
        </div>
      </div>

      {/* Main Finding Overview Card */}
      <div className="glass-panel" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '1rem',
                fontWeight: 800,
                color: 'var(--color-info)',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                padding: '3px 10px',
                borderRadius: '6px',
                border: '1px solid rgba(6, 182, 212, 0.25)',
              }}>
                {finding.id}
              </span>
              <SeverityBadge severity={finding.severity} />
              <StatusBadge status={finding.status} />
              <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {finding.category} · {finding.type}
              </span>
            </div>

            <h1 style={{ fontSize: '1.5rem', color: '#ffffff', marginTop: '6px', marginBottom: '8px' }}>
              {finding.title}
            </h1>

            <div style={{ display: 'flex', alignItems: 'center', gap: '18px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Clock size={13} /> Discovered: {finding.first_seen_at ? new Date(finding.first_seen_at).toLocaleString() : 'Initial scan'}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Activity size={13} /> Source Scanner: <strong style={{ color: 'var(--text-main)' }}>{finding.source}</strong>
              </span>
              {finding.fingerprint && (
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontFamily: 'var(--font-mono)' }}>
                  <Fingerprint size={13} /> FP: {finding.fingerprint.slice(0, 12)}...
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Hop Impact Paths (Graph Grounded) */}
      <div className="glass-panel" style={{ padding: '22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Network size={20} color="var(--color-info)" />
          <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Multi-Hop Blast Radius & Data Impact</h2>
        </div>

        {(!finding.impact_paths || finding.impact_paths.length === 0) ? (
          <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            No downstream graph impact path mapped for this finding.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {finding.impact_paths.map((p, idx) => (
              <div
                key={idx}
                style={{
                  backgroundColor: 'rgba(7, 11, 20, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
              >
                {/* Endpoint */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Endpoint:</span>
                  <span style={{
                    backgroundColor: 'rgba(6, 182, 212, 0.1)',
                    border: '1px solid rgba(6, 182, 212, 0.25)',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    color: 'var(--color-info)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {p.endpoint || 'Unknown'}
                  </span>
                </div>

                <ArrowRight size={14} color="var(--text-dim)" />

                {/* Service */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Server size={14} color="#818cf8" />
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-main)', fontWeight: 600 }}>
                    {p.service || 'Service'}
                  </span>
                </div>

                <ArrowRight size={14} color="var(--text-dim)" />

                {/* Database */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Database size={14} color="var(--color-medium)" />
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-main)', fontWeight: 600 }}>
                    {p.database || 'Database'}
                  </span>
                </div>

                <ArrowRight size={14} color="var(--text-dim)" />

                {/* Data Asset with classification */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f43f5e' }}>
                    {p.asset || 'Sensitive Asset'}
                  </span>
                  {p.classification && (
                    <span style={{
                      backgroundColor: p.classification === 'sensitive' ? 'rgba(236, 72, 153, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                      border: `1px solid ${p.classification === 'sensitive' ? 'rgba(236, 72, 153, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                      color: p.classification === 'sensitive' ? '#ec4899' : 'var(--color-success)',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                    }}>
                      {p.classification}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Two Column: Endpoint Details & Priority Factors */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {/* Endpoint Metadata */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Layers size={18} color="var(--color-info)" />
            <h3 style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Affected Target Specification</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>URI Path</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', color: 'var(--text-main)', marginTop: '2px' }}>
                {finding.endpoint?.path || 'N/A'}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '24px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>HTTP Method</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--color-info)', fontWeight: 700, marginTop: '2px' }}>
                  {finding.endpoint?.method || 'N/A'}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Authentication</span>
                <div style={{ marginTop: '2px', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem' }}>
                  {finding.endpoint?.auth_required ? (
                    <span style={{ color: 'var(--color-success)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Lock size={12} /> Required
                    </span>
                  ) : (
                    <span style={{ color: 'var(--color-critical)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Unlock size={12} /> Unauthenticated (Public)
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Priority & Risk Breakdown */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={18} color="var(--color-high)" />
              <h3 style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Priority & Risk Breakdown</h3>
            </div>
            {finding.priority?.priority_score !== undefined && (
              <div style={{
                fontSize: '1.1rem',
                fontWeight: 800,
                color: 'var(--color-high)',
                backgroundColor: 'rgba(249, 115, 22, 0.1)',
                padding: '2px 10px',
                borderRadius: '6px',
                border: '1px solid rgba(249, 115, 22, 0.25)',
              }}>
                {finding.priority.priority_score} / 100
              </div>
            )}
          </div>

          {finding.priority?.factors ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {Object.entries(finding.priority.factors).map(([factorName, factorVal]) => (
                <div key={factorName}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '3px' }}>
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-muted)' }}>{factorName}</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{factorVal}</span>
                  </div>
                  <div style={{
                    height: '6px',
                    borderRadius: '3px',
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, (Number(factorVal) / 10) * 100)}%`,
                      backgroundColor: 'var(--color-high)',
                    }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
              Automated priority scoring pending evidence verification.
            </div>
          )}
        </div>
      </div>

      {/* Supporting Evidence (Distinguishing Fact from Interpretation) */}
      <div className="glass-panel" style={{ padding: '22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <FileText size={18} color="var(--color-info)" />
          <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Grounding Evidence (Empirically Observed)</h2>
        </div>

        {(!finding.evidence || finding.evidence.length === 0) ? (
          <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            No explicit evidence records associated with this finding node.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {finding.evidence.map((ev) => (
              <div
                key={ev.id}
                style={{
                  backgroundColor: 'rgba(7, 11, 20, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <CheckCircle2 size={16} color="var(--color-success)" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-main)', fontWeight: 500 }}>
                      {ev.summary || 'Empirical evidence recorded'}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      Evidence ID: {ev.id}
                    </div>
                  </div>
                </div>

                {ev.confirmed && (
                  <span className="badge badge-success" style={{ flexShrink: 0 }}>
                    CONFIRMED
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Defensive Remediation Guidance */}
      {finding.guidance && (
        <div className="glass-panel" style={{
          padding: '22px',
          borderLeft: '4px solid var(--color-info)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <AlertTriangle size={18} color="var(--color-info)" />
            <h2 style={{ fontSize: '1.05rem', color: 'var(--color-info)' }}>Defensive Remediation Guidance</h2>
          </div>
          <div style={{ fontSize: '0.88rem', color: 'var(--text-main)', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
            {finding.guidance}
          </div>
        </div>
      )}
    </div>
  );
};
