import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  TbLayoutDashboard,
  TbUserCheck,
  TbFileUpload,
  TbTargetArrow,
  TbClipboardCheck,
  TbRoute,
  TbChartRadar,
  TbTrendingUp,
  TbCoin,
  TbAward,
  TbBriefcase,
  TbShieldCheck,
  TbCheck
} from 'react-icons/tb';

export default function Sidebar({ onOpenPrivacyModal }) {
  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: TbLayoutDashboard },
    { to: '/profile', label: 'Profile & Skills', icon: TbUserCheck },
    { to: '/upload-resume', label: 'Resume Upload', icon: TbFileUpload },
    { to: '/assessment', label: 'Skill Verification', icon: TbClipboardCheck },
    { to: '/careers', label: 'Career Recommendations', icon: TbBriefcase },
    { to: '/skill-gap', label: 'Skill Gap Analysis', icon: TbTargetArrow },
    { to: '/roadmap', label: 'Learning Roadmap', icon: TbRoute },
    { to: '/readiness', label: 'Readiness Score', icon: TbChartRadar },
    { to: '/salary-sim', label: 'Salary Simulator', icon: TbCoin },
    { to: '/progress', label: 'Progress History', icon: TbTrendingUp },
    { to: '/badges', label: 'Badges & Awards', icon: TbAward },
  ];

  return (
    <aside className="w-64 bg-base-900/50 border-r border-base-700/60 p-4 hidden lg:flex flex-col justify-between min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <p className="text-[10px] font-mono uppercase tracking-wider text-white/30 px-3 py-2">
          Student Portal
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-accent-500/15 text-accent-300 border border-accent-400/30 shadow-glow font-semibold'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Informational Privacy Card (No Admin or FL operational controls) */}
      <div className="surface p-3.5 rounded-2xl border border-teal-500/30 bg-teal-950/20 space-y-2">
        <div className="flex items-center space-x-2 text-teal-400">
          <TbShieldCheck className="w-4 h-4 flex-shrink-0" />
          <span className="text-xs font-semibold">Privacy-Preserving Intelligence</span>
        </div>
        <p className="text-[11px] text-white/60 leading-snug">
          Your career data is protected using decentralized privacy-preserving learning.
        </p>
        <div className="space-y-1 pt-1 border-t border-teal-500/20 text-[10px] text-teal-200/90 font-mono">
          <div className="flex items-center space-x-1.5">
            <TbCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span>Raw training data remains local</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <TbCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span>Model updates are shared</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <TbCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span>Federated aggregation (FedAvg)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <TbCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span>Differential Privacy protection</span>
          </div>
        </div>

        {onOpenPrivacyModal && (
          <button
            type="button"
            onClick={onOpenPrivacyModal}
            className="w-full text-center text-[10px] text-teal-300 hover:text-white pt-1 underline underline-offset-2"
          >
            Learn More
          </button>
        )}
      </div>
    </aside>
  );
}
