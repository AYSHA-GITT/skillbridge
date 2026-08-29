import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  TbLayoutDashboard,
  TbUserCheck,
  TbTargetArrow,
  TbClipboardCheck,
  TbRoute,
  TbChartRadar,
  TbTrendingUp,
  TbCoin,
  TbAward,
  TbNetwork,
  TbBriefcase,
  TbShieldCode
} from 'react-icons/tb';

export default function Sidebar() {
  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: TbLayoutDashboard },
    { to: '/profile', label: 'Skills Profile', icon: TbUserCheck },
    { to: '/skill-gap', label: 'Skill Gap', icon: TbTargetArrow },
    { to: '/assessment', label: 'Assessments', icon: TbClipboardCheck },
    { to: '/roadmap', label: 'Learning Roadmap', icon: TbRoute },
    { to: '/readiness', label: 'Readiness Score', icon: TbChartRadar },
    { to: '/progress', label: 'Progress History', icon: TbTrendingUp },
    { to: '/salary-sim', label: 'Salary Simulator', icon: TbCoin },
    { to: '/badges', label: 'Badges & Awards', icon: TbAward },
    { to: '/careers', label: 'Career Demand', icon: TbBriefcase },
    { to: '/federated', label: 'Federated Viz', icon: TbNetwork },
    { to: '/admin', label: 'Admin Portal', icon: TbShieldCode },
  ];

  return (
    <aside className="w-64 bg-base-900/50 border-r border-base-700/60 p-4 hidden lg:flex flex-col justify-between min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <p className="text-[10px] font-mono uppercase tracking-wider text-white/30 px-3 py-2">
          Navigation
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

      <div className="surface p-3.5 rounded-xl border border-base-700/80">
        <div className="flex items-center space-x-2 text-accent-400 mb-1.5">
          <TbNetwork className="w-4 h-4" />
          <span className="text-xs font-semibold">Federated Privacy</span>
        </div>
        <p className="text-[11px] text-white/50 leading-snug">
          Your skill data never leaves your institution unencrypted.
        </p>
      </div>
    </aside>
  );
}
