import React, { useState, useEffect } from 'react';
import { useOutletContext, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Bot,
  Send,
  Sparkles,
  CheckCircle2,
  GitBranch,
  AlertTriangle,
  Layers,
  ArrowRight,
  ShieldAlert,
  Loader2,
  FileCheck,
  HelpCircle,
} from 'lucide-react';
import { startInvestigation } from '../services/api';
import { InvestigationResponse } from '../types';
import { ErrorState, EmptyState } from '../components/common/FeedbackStates';

export const InvestigationsPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const prefilledFinding = searchParams.get('finding_id') || '';

  const [question, setQuestion] = useState<string>(
    prefilledFinding
      ? `Analyze the blast radius, multi-hop exposure, and sensitive data access for finding ${prefilledFinding}.`
      : 'What sensitive customer data assets are exposed through unauthenticated endpoints?'
  );
  const [findingIdsInput, setFindingIdsInput] = useState<string>(prefilledFinding);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigationResponse | null>(null);

  useEffect(() => {
    if (prefilledFinding) {
      setFindingIdsInput(prefilledFinding);
      setQuestion(`Analyze the blast radius, multi-hop exposure, and sensitive data access for finding ${prefilledFinding}.`);
    }
  }, [prefilledFinding]);

  const handleInvestigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    const parsedFindingIds = findingIdsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const response = await startInvestigation({
        project_id: currentProject,
        question: question.trim(),
        finding_ids: parsedFindingIds.length > 0 ? parsedFindingIds : undefined,
      });
      setResult(response);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err.message || 'AI Investigation query failed');
    } finally {
      setLoading(false);
    }
  };

  const examplePrompts = [
    'What sensitive customer data assets are exposed through unauthenticated endpoints?',
    'Trace multi-hop access from DemoShop endpoints to user credentials in the database',
    'What defensive verification and remediation should we prioritize?',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '1.6rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Bot size={26} color="var(--color-info)" />
          Graph-Grounded AI Security Analyst
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: '2px' }}>
          Interrogate your security knowledge graph with verified multi-hop grounding and empirical facts for project: <strong>{currentProject}</strong>
        </p>
      </div>

      {/* Query Form */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <form onSubmit={handleInvestigate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '6px', display: 'block' }}>
              Investigation Query / Prompt
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(7, 11, 20, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '10px 14px',
            }}>
              <input
                type="text"
                placeholder="Ask about vulnerabilities, blast radius, exposed sensitive assets..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
                style={{
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-main)',
                  fontSize: '0.92rem',
                  width: '100%',
                }}
              />
              <button
                type="submit"
                disabled={loading || !question.trim()}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: 'rgba(6, 182, 212, 0.2)',
                  border: '1px solid rgba(6, 182, 212, 0.4)',
                  color: 'var(--color-info)',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
                  flexShrink: 0,
                  marginLeft: '12px',
                }}
              >
                {loading ? <Loader2 size={16} className="pulse-indicator" /> : <Send size={16} />}
                <span>{loading ? 'Reasoning...' : 'Investigate'}</span>
              </button>
            </div>
          </div>

          {/* Finding ID scoping & Example Prompts */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '260px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                FOCUS FINDINGS (OPTIONAL):
              </span>
              <input
                type="text"
                placeholder="e.g. F-001, F-002"
                value={findingIdsInput}
                onChange={(e) => setFindingIdsInput(e.target.value)}
                style={{
                  backgroundColor: 'rgba(7, 11, 20, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-main)',
                  width: '180px',
                  outline: 'none',
                }}
              />
            </div>

            {/* Prompt pills */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <Sparkles size={13} color="var(--color-info)" />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>Try:</span>
              {examplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setQuestion(p)}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-info)')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                >
                  {p.slice(0, 36)}...
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="glass-panel" style={{ padding: '36px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px' }}>
          <Loader2 size={32} color="var(--color-info)" className="pulse-indicator" />
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Grounding investigation query against FalkorDB...
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
              Traversing 3-hop topology, verifying empirical evidence, and formulating defensible actions
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <ErrorState
          title="Investigation Analysis Failed"
          message={error}
          onRetry={() => handleInvestigate()}
        />
      )}

      {/* Result Display */}
      {result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Main Answer Card */}
          <div className="glass-panel" style={{ padding: '24px 28px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileCheck size={20} color="var(--color-info)" />
                <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)' }}>Investigation Assessment</h2>
              </div>
              <span className="badge badge-info">
                STATUS: {result.status}
              </span>
            </div>

            <div style={{
              fontSize: '0.92rem',
              color: 'var(--text-main)',
              lineHeight: '1.65',
              backgroundColor: 'rgba(7, 11, 20, 0.5)',
              padding: '16px 20px',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              whiteSpace: 'pre-wrap',
            }}>
              {result.answer}
            </div>
          </div>

          {/* Two Column: Observed Facts vs Inferred Relationships */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '20px' }}>
            {/* Observed Facts */}
            <div className="glass-panel" style={{ padding: '22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <CheckCircle2 size={18} color="var(--color-success)" />
                <h3 style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Observed Facts (Empirical Evidence)</h3>
              </div>

              {result.observed_facts?.length === 0 ? (
                <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>No factual claims recorded.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {result.observed_facts.map((fact, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                        fontSize: '0.84rem',
                        color: 'var(--text-main)',
                      }}
                    >
                      <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>✓</span>
                      <span>{fact}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Inferred Relationships */}
            <div className="glass-panel" style={{ padding: '22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <GitBranch size={18} color="#818cf8" />
                <h3 style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Inferred Graph Relationships</h3>
              </div>

              {result.inferred_relationships?.length === 0 ? (
                <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>No inferred relationships derived.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {result.inferred_relationships.map((inf, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                        fontSize: '0.84rem',
                        color: 'var(--text-main)',
                      }}
                    >
                      <span style={{ color: '#818cf8', fontWeight: 700 }}>➔</span>
                      <span>{inf}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Uncertainties & Caveats Card */}
          {result.uncertainties && result.uncertainties.length > 0 && (
            <div className="glass-panel" style={{
              padding: '20px 24px',
              borderLeft: '4px solid var(--color-medium)',
              backgroundColor: 'rgba(245, 158, 11, 0.05)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <AlertTriangle size={18} color="var(--color-medium)" />
                <h3 style={{ fontSize: '0.98rem', color: 'var(--color-medium)' }}>Uncertainties & Assumptions</h3>
              </div>
              <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                {result.uncertainties.map((u, idx) => (
                  <li key={idx}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Affected Components */}
          {result.affected_components && result.affected_components.length > 0 && (
            <div className="glass-panel" style={{ padding: '22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <Layers size={18} color="var(--color-info)" />
                <h3 style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Affected Components in Blast Radius</h3>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      color: 'var(--text-dim)',
                      fontSize: '0.7rem',
                      textTransform: 'uppercase',
                    }}>
                      <th style={{ padding: '10px 14px' }}>Finding</th>
                      <th style={{ padding: '10px 14px' }}>Endpoint</th>
                      <th style={{ padding: '10px 14px' }}>Service</th>
                      <th style={{ padding: '10px 14px' }}>Database</th>
                      <th style={{ padding: '10px 14px' }}>Data Asset</th>
                      <th style={{ padding: '10px 14px' }}>Classification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.affected_components.map((comp, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', color: 'var(--color-info)' }}>
                          {comp.finding_id ? (
                            <button
                              onClick={() => navigate(`/findings/${comp.finding_id}`)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--color-info)',
                                cursor: 'pointer',
                                textDecoration: 'underline',
                                fontFamily: 'inherit',
                              }}
                            >
                              {comp.finding_id}
                            </button>
                          ) : '—'}
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)' }}>{comp.endpoint || '—'}</td>
                        <td style={{ padding: '10px 14px' }}>{comp.service || '—'}</td>
                        <td style={{ padding: '10px 14px' }}>{comp.database || '—'}</td>
                        <td style={{ padding: '10px 14px', fontWeight: 600 }}>{comp.data_asset || '—'}</td>
                        <td style={{ padding: '10px 14px' }}>
                          {comp.classification && (
                            <span style={{
                              backgroundColor: comp.classification === 'sensitive' ? 'rgba(236, 72, 153, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                              color: comp.classification === 'sensitive' ? '#ec4899' : 'var(--color-success)',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                            }}>
                              {comp.classification}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Recommended Next Actions */}
          {result.next_actions && result.next_actions.length > 0 && (
            <div className="glass-panel" style={{ padding: '22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <ShieldAlert size={18} color="var(--color-critical)" />
                <h3 style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Recommended Remediation & Verification Actions</h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {result.next_actions.map((act, idx) => (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: 'rgba(7, 11, 20, 0.6)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      padding: '14px 18px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.9rem' }}>
                        {act.action}
                      </div>
                      {act.requires_approval ? (
                        <span className="badge badge-critical" style={{ fontSize: '0.68rem' }}>
                          REQUIRES HUMAN APPROVAL
                        </span>
                      ) : (
                        <span className="badge badge-success" style={{ fontSize: '0.68rem' }}>
                          SAFE VERIFICATION
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      <strong>Rationale:</strong> {act.why}
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                      <span><strong>Method:</strong> {act.method}</span>
                      <span><strong>Verification:</strong> {act.verification}</span>
                      {act.target && <span><strong>Target:</strong> {act.target}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
