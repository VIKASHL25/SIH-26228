import React from 'react';
import { SeverityLevel } from '../../types';

interface Props {
  severity: SeverityLevel | string;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<Props> = ({ severity, size = 'sm' }) => {
  const sev = (severity || '').toUpperCase();

  const getStyle = () => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-red-500/15 text-red-400 border-red-500/40';
      case 'HIGH':
        return 'bg-orange-500/15 text-orange-400 border-orange-500/40';
      case 'MEDIUM':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/40';
      case 'LOW':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40';
      case 'INFO':
      default:
        return 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30';
    }
  };

  const sizeClass = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span className={`inline-flex items-center font-mono font-semibold rounded border uppercase tracking-wider ${getStyle()} ${sizeClass}`}>
      {sev}
    </span>
  );
};
