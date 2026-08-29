import React from 'react';
import {
  TbFileCheck, TbBrain, TbAward, TbTrophy,
  TbFlame, TbRocket, TbShieldCheck, TbLock
} from 'react-icons/tb';

const iconMap = {
  TbFileCheck,
  TbBrain,
  TbAward,
  TbTrophy,
  TbFlame,
  TbRocket,
  TbShieldCheck
};

export default function BadgeCard({ badge }) {
  const IconComponent = iconMap[badge.icon] || TbAward;
  const isUnlocked = badge.unlocked;

  return (
    <div
      className={`relative p-5 rounded-2xl border transition-all duration-300 ${
        isUnlocked
          ? 'bg-gradient-to-b from-base-800 to-base-900 border-accent-400/30 shadow-glow'
          : 'bg-base-900/40 border-base-800 opacity-60'
      }`}
    >
      <div className="flex items-start space-x-4">
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform ${
            isUnlocked
              ? 'bg-accent-500/20 text-accent-300 border border-accent-400/40'
              : 'bg-base-800 text-white/30 border border-base-700'
          }`}
        >
          {isUnlocked ? (
            <IconComponent className="w-6 h-6" />
          ) : (
            <TbLock className="w-5 h-5" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-accent-400 font-medium">
              {badge.category}
            </span>
            {isUnlocked && (
              <span className="text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                Earned
              </span>
            )}
          </div>
          <h4 className="text-base font-semibold text-white mt-0.5 truncate">
            {badge.title}
          </h4>
          <p className="text-xs text-white/50 mt-1 leading-relaxed">
            {badge.description}
          </p>

          {!isUnlocked && (
            <div className="mt-3">
              <div className="flex justify-between text-[10px] text-white/40 mb-1">
                <span>Progress</span>
                <span>{badge.progress}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-base-800 overflow-hidden">
                <div
                  className="h-full bg-accent-500/50 rounded-full"
                  style={{ width: `${badge.progress}%` }}
                />
              </div>
            </div>
          )}

          {isUnlocked && badge.unlocked_at && (
            <p className="text-[11px] text-white/30 mt-3">
              Unlocked: {badge.unlocked_at}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
