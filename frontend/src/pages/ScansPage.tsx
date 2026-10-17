import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  Radar,
  Play,
  ShieldCheck,
  ShieldAlert,
  AlertOctagon,
  Clock,
  Layers,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Lock,
} from 'lucide-react';
import { createScan, getScans, verifyBola } from '../services/api';
import { ScanResponse, BolaVerificationResponse } from '../types';
import { LoadingState, ErrorState, EmptyState } from '../components/common/FeedbackStates';

export const ScansPage: React.FC = () => {
  const { currentProject } = useOutletContext<{ currentProject: string }>();
  const navigate = useNavigate();

  const [scans, setScans] = useState<ScanResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Scan Execution State
  const [selectedScanner, setSelectedScanner] = useState<string>('http_headers');
  const [targetUrl, setTargetUrl] = useState<string>('http://127.0.0.1:5001');
  const [scanning, setScanning] = useState<boolean>(false);
  const [scanResult, setScanResult] = useState<ScanResponse | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  // BOLA Verification State
  const [verifying, setVerifying] = useState<boolean>(false);
  const [bolaResult, setBolaResult] = useState<BolaVerificationResponse | null>(null);
  const [bolaError, setBolaError] = useState<string | null>(null);

  const loadScanHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getScans({ project_id: currentProject, limit: 50 });
      setScans(res.items || []);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err.message || 'Failed to load scan history');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    loadScanHistory();
  }, [loadScanHistory]);

  const handleRunScan = async (e: React.FormEvent) => {
    e.preventDefault();
    setScanning(true);
    setScanResult(null);
    setScanError(null);

    try {
      const res = await createScan(currentProject, {
        scanner: selectedScanner,
        target_url: targetUrl.trim(),
      });
      setScanResult(res);
      loadScanHistory();
    } catch (err: any) {
      setScanError(err?.response?.data?.error?.message || err.message || 'Scan execution failed');
    } finally {
      setScanning(false);
    }
  };

  const handleVerifyBola = async () => {
    setVerifying(true);
    setBolaResult(null);
    setBolaError(null);

    try {
      const res = await verifyBola({
        project_id: currentProject,
        target_url: targetUrl.trim(),
      });
      setBolaResult(res);
      loadScanHistory();
    } catch (err: any) {
      setBolaError(err?.response?.data?.error?.message || err.message || 'BOLA verification failed');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Radar size={26} color="var(--color-info)" />
            Scan & Verification Engine
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: '2px' }}>
            Execute authorized baseline audits and verify object-level authorization across project: <strong>{currentProject}</strong>
          </p>
        </div>

        <button
          onClick={loadScanHistory}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
            padding: '8px 14px',
            borderRadius: '6px',
            fontSize: '0.82rem',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} /> Refresh History
        </button>
      </div>

      {/* Two Column Interactive Consoles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '24px' }}>
        {/* Run Authorized Scan */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Play size={18} color="var(--color-info)" />
            <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Authorized Scan Execution</h2>
          </div>

          <form onSubmit={handleRunScan} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                SELECT SCANNER MODULE
              </label>
              <select
                value={selectedScanner}
                onChange={(e) => setSelectedScanner(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: 'rgba(7, 11, 20, 0.7)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: 'var(--text-main)',
                  padding: '8px 12px',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              >
                <option value="http_headers">Security Headers Scanner (Baseline Audit)</option>
                <option value="bola_check">BOLA Authorization Checker (Multi-Tenant Test)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                AUTHORIZED TARGET URL
              </label>
              <input
                type="text"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="http://127.0.0.1:5001"
                style={{
                  width: '100%',
                  backgroundColor: 'rgba(7, 11, 20, 0.7)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: 'var(--text-main)',
                  padding: '8px 12px',
                  fontSize: '0.88rem',
                  fontFamily: 'var(--font-mono)',
                  outline: 'none',
                }}
              />
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Lock size={11} /> Scans are strictly constrained to authorized local hosts (localhost / 127.0.0.1)
              </div>
            </div>

            <button
              type="submit"
              disabled={scanning}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                backgroundColor: 'rgba(6, 182, 212, 0.18)',
                border: '1px solid rgba(6, 182, 212, 0.4)',
                color: 'var(--color-info)',
                padding: '10px 18px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: scanning ? 'not-allowed' : 'pointer',
                marginTop: '6px',
              }}
            >
              {scanning ? <Loader2 size={16} className="pulse-indicator" /> : <Play size={16} />}
              <span>{scanning ? 'Executing Scan & Graph Ingestion...' : 'Execute Authorized Scan'}</span>
            </button>
          </form>

          {/* Scan result display */}
          {scanResult && (
            <div style={{
              marginTop: '16px',
              backgroundColor: 'rgba(7, 11, 20, 0.6)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              padding: '14px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-success)', fontWeight: 600, fontSize: '0.85rem' }}>
                  <CheckCircle2 size={16} /> Scan Completed Successfully
                </div>
                <span className="badge badge-info">{scanResult.id}</span>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Observed <strong>{scanResult.findings_count}</strong> findings. Status: <strong>{scanResult.status}</strong>
              </div>
            </div>
          )}

          {scanError && (
            <div style={{
              marginTop: '16px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '12px 14px',
              color: '#f87171',
              fontSize: '0.82rem',
            }}>
              {scanError}
            </div>
          )}
        </div>

        {/* Targeted BOLA Verification */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <ShieldAlert size={18} color="var(--color-critical)" />
            <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Targeted BOLA Retest & Verification</h2>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5', marginBottom: '16px' }}>
            Performs an active, deterministic cross-tenant authorization audit between authenticated tenants on endpoint:
            <code style={{ marginLeft: '4px', color: 'var(--color-info)' }}>/api/orders/order-101</code>
          </p>

          <button
            onClick={handleVerifyBola}
            disabled={verifying}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              color: '#f87171',
              padding: '10px 18px',
              borderRadius: '8px',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: verifying ? 'not-allowed' : 'pointer',
            }}
          >
            {verifying ? <Loader2 size={16} className="pulse-indicator" /> : <ShieldCheck size={16} />}
            <span>{verifying ? 'Executing BOLA Verification...' : 'Trigger BOLA Verification'}</span>
          </button>

          {/* Verification outcome display */}
          {bolaResult && (
            <div style={{
              marginTop: '16px',
              backgroundColor: 'rgba(7, 11, 20, 0.6)',
              border: `1px solid ${
                bolaResult.outcome === 'CONFIRMED_UNAUTHORIZED_ACCESS'
                  ? 'rgba(239, 68, 68, 0.3)'
                  : 'rgba(16, 185, 129, 0.3)'
              }`,
              borderRadius: '8px',
              padding: '14px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span className={`badge ${
                  bolaResult.outcome === 'CONFIRMED_UNAUTHORIZED_ACCESS' ? 'badge-critical' : 'badge-success'
                }`}>
                  {bolaResult.outcome}
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                  {bolaResult.test_id}
                </span>
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--text-main)', marginTop: '4px' }}>
                {bolaResult.summary}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '6px' }}>
                Tested At: {new Date(bolaResult.tested_at).toLocaleString()}
              </div>
            </div>
          )}

          {bolaError && (
            <div style={{
              marginTop: '16px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '12px 14px',
              color: '#f87171',
              fontSize: '0.82rem',
            }}>
              {bolaError}
            </div>
          )}
        </div>
      </div>

      {/* Scan History Table */}
      <div className="glass-panel" style={{ padding: '22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={18} color="var(--color-info)" />
            <h2 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>Historical Scanner Executions</h2>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            Total Recorded Runs: <strong>{scans.length}</strong>
          </span>
        </div>

        {loading ? (
          <LoadingState message="Loading scan execution logs..." />
        ) : error ? (
          <ErrorState title="History Failed" message={error} onRetry={loadScanHistory} />
        ) : scans.length === 0 ? (
          <EmptyState
            title="No Scans Executed Yet"
            message="No scanner runs have been recorded for this project yet. Use the console above to initiate an authorized baseline scan."
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-dim)',
                  fontSize: '0.72rem',
                  textTransform: 'uppercase',
                }}>
                  <th style={{ padding: '12px 16px' }}>Scan ID</th>
                  <th style={{ padding: '12px 16px' }}>Scanner</th>
                  <th style={{ padding: '12px 16px' }}>Target Scope</th>
                  <th style={{ padding: '12px 16px' }}>Execution Status</th>
                  <th style={{ padding: '12px 16px' }}>Findings Count</th>
                  <th style={{ padding: '12px 16px' }}>Started At</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <tr key={s.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-info)' }}>
                      {s.id}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid var(--border-subtle)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.78rem',
                        fontFamily: 'var(--font-mono)',
                      }}>
                        {s.scanner}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                      {s.target_url || 'Default Demo Target'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className={`badge ${
                        s.status.includes('findings') ? 'badge-critical' : s.status.includes('clean') ? 'badge-success' : 'badge-gray'
                      }`}>
                        {s.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontWeight: 700, color: s.findings_count > 0 ? 'var(--color-critical)' : 'var(--color-success)' }}>
                      {s.findings_count}
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
