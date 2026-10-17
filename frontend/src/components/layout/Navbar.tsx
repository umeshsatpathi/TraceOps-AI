import React, { useEffect, useState } from 'react';
import { Layers, Server, ShieldCheck, Terminal, AlertTriangle } from 'lucide-react';
import { getHealth, getProjects } from '../../services/api';
import { ProjectSummary } from '../../types';

interface NavbarProps {
  currentProject: string;
  onSelectProject: (projectId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentProject, onSelectProject }) => {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const [healthRes, projRes] = await Promise.all([getHealth(), getProjects()]);
        if (isMounted) {
          setApiOk(healthRes.status === 'ok');
          setProjects(projRes.items || []);
        }
      } catch {
        if (isMounted) setApiOk(false);
      }
    };
    loadData();
    const interval = setInterval(loadData, 20000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header style={{
      height: '64px',
      borderBottom: '1px solid var(--border-subtle)',
      backgroundColor: 'rgba(12, 18, 34, 0.85)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 28px',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      {/* Left: Project Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: 'var(--text-muted)',
          fontSize: '0.85rem',
          fontWeight: 500,
        }}>
          <Layers size={16} color="var(--color-info)" />
          <span>Active Project:</span>
        </div>

        <select
          value={currentProject}
          onChange={(e) => onSelectProject(e.target.value)}
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-main)',
            fontSize: '0.88rem',
            fontWeight: 600,
            padding: '6px 12px',
            borderRadius: '6px',
            outline: 'none',
            cursor: 'pointer',
          }}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.id})
            </option>
          ))}
          {projects.length === 0 && (
            <option value="project-demoshop">DemoShop (project-demoshop)</option>
          )}
        </select>

        <span style={{
          fontSize: '0.75rem',
          color: 'var(--text-dim)',
          background: 'rgba(255, 255, 255, 0.04)',
          padding: '3px 8px',
          borderRadius: '4px',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        }}>
          Target: http://127.0.0.1:5001
        </span>
      </div>

      {/* Right: API Health Badge & Demo Target link */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '5px 12px',
          borderRadius: '9999px',
          backgroundColor: apiOk ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${apiOk ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
          fontSize: '0.75rem',
          fontWeight: 600,
          color: apiOk ? 'var(--color-success)' : 'var(--color-critical)',
        }}>
          <span
            className="pulse-indicator"
            style={{ backgroundColor: apiOk ? 'var(--color-success)' : 'var(--color-critical)' }}
          />
          {apiOk ? 'FastAPI 1.0 Online' : apiOk === false ? 'API Offline' : 'Connecting API...'}
        </div>
      </div>
    </header>
  );
};
