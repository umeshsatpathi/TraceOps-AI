import React from 'react';

interface SeverityBadgeProps {
  severity: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const s = severity.toLowerCase();
  let badgeClass = 'badge-medium';
  if (s === 'critical') badgeClass = 'badge-critical';
  else if (s === 'high') badgeClass = 'badge-high';
  else if (s === 'medium') badgeClass = 'badge-medium';
  else if (s === 'low') badgeClass = 'badge-low';
  else if (s === 'info' || s === 'informational') badgeClass = 'badge-info';

  return <span className={`badge ${badgeClass}`}>{severity}</span>;
};

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const st = status.toUpperCase();
  let badgeClass = 'badge-gray';
  if (st === 'CONFIRMED' || st === 'OPEN') badgeClass = 'badge-critical';
  else if (st === 'REMEDIATED' || st === 'RESOLVED') badgeClass = 'badge-success';
  else if (st === 'REOPENED') badgeClass = 'badge-high';
  else if (st === 'UNVERIFIED' || st === 'INCONCLUSIVE') badgeClass = 'badge-medium';
  else if (st === 'COMPLETED_CLEAN' || st === 'COMPLETED') badgeClass = 'badge-success';
  else if (st === 'FAILED') badgeClass = 'badge-critical';

  return <span className={`badge ${badgeClass}`}>{status}</span>;
};
