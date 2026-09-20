import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  CartesianGrid
} from 'recharts';
import { ContributorProfile } from '../../types';

interface Props {
  profiles: ContributorProfile[];
  onSelectContributor?: (profile: ContributorProfile) => void;
}

export const ContributorRiskBarChart: React.FC<Props> = ({ profiles, onSelectContributor }) => {
  const data = profiles.map(p => ({
    name: p.contributor_id.replace('contributor_', 'Contrib '),
    id: p.contributor_id,
    risk: Math.round(p.risk_score * 1000) / 1000,
    riskLevel: p.risk_level,
    flagged: p.flagged_samples,
    total: p.total_samples,
    dominantFactor: p.dominant_factor,
    raw: p
  }));

  const getBarColor = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return '#ef4444';
      case 'HIGH':
        return '#f97316';
      case 'MEDIUM':
        return '#f59e0b';
      case 'CLEAN':
      default:
        return '#10b981';
    }
  };

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 30, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 1]}
            tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}
            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
          />
          <YAxis
            dataKey="name"
            type="category"
            tick={{ fill: '#cbd5e1', fontSize: 12 }}
            width={90}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="bg-slate-900 border border-slate-700 p-2.5 rounded shadow-xl text-xs font-sans">
                    <p className="font-semibold text-white mb-1">{item.id}</p>
                    <p className="text-slate-300">
                      Risk Score: <span className="font-mono text-cyan-400">{(item.risk * 100).toFixed(1)}%</span>
                    </p>
                    <p className="text-slate-300">
                      Risk Tier: <span className="font-mono font-semibold" style={{ color: getBarColor(item.riskLevel) }}>{item.riskLevel}</span>
                    </p>
                    <p className="text-slate-300">
                      Flagged: <span className="font-mono text-amber-400">{item.flagged} / {item.total}</span>
                    </p>
                    <p className="text-slate-400 text-[11px] mt-1 italic">
                      Dominant: {item.dominantFactor}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar
            dataKey="risk"
            radius={[0, 4, 4, 0]}
            onClick={(entry: any) => onSelectContributor && onSelectContributor(entry?.payload?.raw || entry?.raw)}
            cursor="pointer"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.riskLevel)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
