import React from 'react';
import { Loader2, AlertCircle, Inbox, RefreshCw } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Querying security graph...' }) => (
  <div style={{
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    color: 'var(--text-muted)',
    gap: '14px',
  }}>
    <Loader2 size={36} color="var(--color-info)" style={{ animation: 'spin 1.5s linear infinite' }} />
    <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>{message}</div>
    <style>{`
      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
    `}</style>
  </div>
);

interface ErrorStateProps {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Operation Failed',
  message,
  requestId,
  onRetry,
}) => (
  <div style={{
    padding: '24px',
    borderRadius: '10px',
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    border: '1px solid rgba(239, 68, 68, 0.25)',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    margin: '16px 0',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--color-critical)' }}>
      <AlertCircle size={22} />
      <span style={{ fontWeight: 700, fontSize: '1rem' }}>{title}</span>
    </div>
    <div style={{ color: 'var(--text-main)', fontSize: '0.88rem', lineHeight: '1.5' }}>
      {message}
    </div>
    {requestId && (
      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
        Request ID: {requestId}
      </div>
    )}
    {onRetry && (
      <div>
        <button
          onClick={onRetry}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'rgba(239, 68, 68, 0.2)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#ffffff',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '0.82rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    )}
  </div>
);

interface EmptyStateProps {
  title: string;
  description?: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  message,
  actionText,
  onAction,
}) => {
  const desc = description || message || '';
  return (
    <div style={{
      padding: '48px 24px',
      textAlign: 'center',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '12px',
      backgroundColor: 'rgba(15, 23, 42, 0.3)',
      border: '1px dashed var(--border-subtle)',
      borderRadius: '12px',
      margin: '16px 0',
    }}>
      <Inbox size={42} color="var(--text-dim)" />
      <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>{title}</div>
      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '420px', lineHeight: '1.5' }}>
        {desc}
      </div>
    {actionText && onAction && (
      <button
        onClick={onAction}
        style={{
          marginTop: '8px',
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          border: '1px solid rgba(6, 182, 212, 0.35)',
          color: 'var(--color-info)',
          padding: '8px 18px',
          borderRadius: '8px',
          fontSize: '0.85rem',
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        {actionText}
      </button>
    )}
  </div>
  );
};
