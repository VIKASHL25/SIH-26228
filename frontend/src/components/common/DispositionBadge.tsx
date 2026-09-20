import React from 'react';
import { RecommendedDisposition } from '../../types';
import { ShieldCheck, AlertTriangle, ShieldAlert } from 'lucide-react';

interface Props {
  disposition: RecommendedDisposition | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const DispositionBadge: React.FC<Props> = ({ disposition, size = 'md', showIcon = true }) => {
  const disp = (disposition || '').toUpperCase();

  const getStyle = () => {
    switch (disp) {
      case 'ACCEPT':
        return {
          bg: 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40 shadow-emerald-900/20',
          icon: <ShieldCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
        };
      case 'REVIEW':
        return {
          bg: 'bg-amber-950/70 text-amber-300 border-amber-500/40 shadow-amber-900/20',
          icon: <AlertTriangle className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
        };
      case 'QUARANTINE':
      case 'QUARANTINE_CONTRIBUTOR':
        return {
          bg: 'bg-rose-950/70 text-rose-300 border-rose-500/40 shadow-rose-900/20',
          icon: <ShieldAlert className="w-3.5 h-3.5 mr-1.5 text-rose-400" />
        };
      default:
        return {
          bg: 'bg-slate-800 text-slate-300 border-slate-700',
          icon: null
        };
    }
  };

  const style = getStyle();
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3.5 py-1.5 font-semibold tracking-wide'
  }[size];

  return (
    <span className={`inline-flex items-center rounded-md border shadow-sm font-medium tracking-wider ${style.bg} ${sizeClasses}`}>
      {showIcon && style.icon}
      {disp}
    </span>
  );
};
