import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  ShieldAlert,
  LayoutDashboard,
  SearchCode,
  Network,
  Bot,
  Radar,
  Activity,
  ExternalLink,
} from 'lucide-react';
import { getHealth } from '../../services/api';

export const Sidebar: React.FC = () => {
  const [dbHealthy, setDbHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    const checkDb = async () => {
      try {
        const res = await getHealth();
        if (isMounted) {
          setDbHealthy(res.dependencies?.graph_db === 'ok');
        }
      } catch {
        if (isMounted) setDbHealthy(false);
      }
    };
    checkDb();
    const interval = setInterval(checkDb, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/findings', label: 'Findings', icon: SearchCode },
    { to: '/graph', label: 'Graph Explorer', icon: Network },
    { to: '/investigations', label: 'AI Investigations', icon: Bot },
    { to: '/scans', label: 'Scan Engine', icon: Radar },
  ];

  return (
    <aside style={{
      width: '260px',
      height: '100vh',
      backgroundColor: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
        }}>
          <ShieldAlert size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{
            fontSize: '1.05rem',
            fontWeight: 800,
            fontFamily: 'var(--font-heading)',
            letterSpacing: '-0.02em',
            background: 'linear-gradient(90deg, #f1f5f9 0%, #94a3b8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            TraceShield AI
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-info)', fontWeight: 600 }}>
            Security Knowledge Graph
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: '16px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-dim)', padding: '0 8px 8px 8px', letterSpacing: '0.08em' }}>
          CORE CAPABILITIES
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#ffffff' : 'var(--text-muted)',
                backgroundColor: isActive ? 'rgba(6, 182, 212, 0.12)' : 'transparent',
                border: isActive ? '1px solid rgba(6, 182, 212, 0.3)' : '1px solid transparent',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid var(--border-subtle)',
        backgroundColor: 'rgba(7, 11, 20, 0.5)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={14} color="var(--text-dim)" />
            FalkorDB Graph
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: dbHealthy ? 'var(--color-success)' : dbHealthy === false ? 'var(--color-critical)' : 'var(--text-dim)',
            fontWeight: 600,
          }}>
            <span
              className="pulse-indicator"
              style={{
                backgroundColor: dbHealthy ? 'var(--color-success)' : dbHealthy === false ? 'var(--color-critical)' : '#94a3b8',
              }}
            />
            {dbHealthy ? 'ONLINE' : dbHealthy === false ? 'OFFLINE' : 'CHECKING...'}
          </span>
        </div>
      </div>
    </aside>
  );
};
