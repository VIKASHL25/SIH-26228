import React from 'react';

interface Props {
  score: number; // 0.0 to 100.0
  size?: number;
}

export const AssuranceHealthGauge: React.FC<Props> = ({ score, size = 180 }) => {
  const normalizedScore = Math.max(0, Math.min(100, score || 0));
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  // Use a 270 degree arc for gauge look
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 80) return '#10b981'; // emerald
    if (s >= 50) return '#f59e0b'; // amber
    return '#ef4444'; // rose
  };

  const color = getColor(normalizedScore);

  return (
    <div className="relative flex flex-col items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#1e293b"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Filled arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          style={{ transition: 'stroke-dashoffset 1s ease-in-out, stroke 0.5s ease' }}
        />
      </svg>

      {/* Central Text Display */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none">
        <span className="text-3xl font-bold font-mono tracking-tight text-white drop-shadow-sm">
          {normalizedScore.toFixed(1)}
        </span>
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 mt-0.5">
          / 100 HEALTH
        </span>
      </div>
    </div>
  );
};
