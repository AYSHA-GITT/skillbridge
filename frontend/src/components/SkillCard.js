import React from 'react';
import { TbCheck, TbAlertTriangle, TbArrowRight } from 'react-icons/tb';

export default function SkillCard({ skill, onVerify, compact = false }) {
  const isVerified = skill.is_verified || !!skill.verification;
  const confidence = skill.extraction_confidence ?? 0.5;
  const confidencePercent = Math.round(confidence * 100);

  const getBadgeColor = () => {
    if (confidence >= 0.7) return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
    if (confidence >= 0.4) return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
  };

  return (
    <div className={`surface p-4 rounded-xl flex flex-col justify-between transition-all duration-200 hover:border-accent-400/30 ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-white capitalize text-base tracking-wide">
            {skill.skill_name}
          </h3>
          <div className="flex items-center space-x-2 mt-1">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono border ${getBadgeColor()}`}>
              {confidencePercent}% confidence
            </span>
          </div>
        </div>

        {isVerified ? (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <TbCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
            Verified
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-white/5 text-white/50 border border-white/10">
            <TbAlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-400" />
            Unverified
          </span>
        )}
      </div>

      {skill.verification && (
        <div className="mt-2 text-xs text-white/50 bg-base-900/60 px-2.5 py-1.5 rounded-lg border border-base-700/50 flex justify-between">
          <span>Quiz Score:</span>
          <span className="text-accent-300 font-semibold">{skill.verification.quiz_score_percent}%</span>
        </div>
      )}

      {!isVerified && onVerify && (
        <button
          onClick={() => onVerify(skill)}
          className="mt-3 w-full py-2 px-3 rounded-lg bg-accent-500/10 hover:bg-accent-500/20 text-accent-300 border border-accent-400/30 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
        >
          <span>Take Quiz Test</span>
          <TbArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
