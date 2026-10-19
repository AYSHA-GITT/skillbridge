import React from 'react';

export default function ProgressBar({
  value,
  progress,
  max = 100,
  label = '',
  showPercentage = false,
  height = 'h-2',
  size,
  colorGradient = 'from-accent-400 to-teal-500'
}) {
  const actualValue = value ?? progress ?? 0;
  const percentage = Math.min(100, Math.max(0, Math.round((actualValue / max) * 100)));
  const barHeight = size === 'sm' ? 'h-1.5' : height;

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex justify-between items-center text-sm mb-1.5">
          {label && <span className="text-white/60 font-medium">{label}</span>}
          {showPercentage && (
            <span className="text-accent-300 font-semibold font-mono text-xs">
              {percentage}%
            </span>
          )}
        </div>
      )}
      <div className={`w-full ${barHeight} rounded-full bg-base-800 border border-base-700/60 overflow-hidden`}>
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colorGradient} transition-all duration-700 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

