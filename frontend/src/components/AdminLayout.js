import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TbBuildingCommunity,
  TbDashboard,
  TbUsers,
  TbChartBar,
  TbTrendingUp,
  TbTargetArrow,
  TbNetwork,
  TbRotateClockwise,
  TbFileSpreadsheet,
  TbAdjustments,
  TbLogout,
  TbServer2
} from 'react-icons/tb';
import authService from '../services/authService';

export default function AdminLayout({ activeTab, onTabChange, adminUser, children }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {
      // ignore
    }
    navigate('/login');
  };

  const navItems = [
    { id: 'overview', label: 'Overview', icon: TbDashboard },
    { id: 'students', label: 'Students', icon: TbUsers },
    { id: 'skills', label: 'Skill Analytics', icon: TbChartBar },
    { id: 'careers', label: 'Career Trends', icon: TbTrendingUp },
    { id: 'gaps', label: 'Common Skill Gaps', icon: TbTargetArrow },
    { id: 'federated', label: 'Federated Learning', icon: TbNetwork, badge: 'Core FL' },
    { id: 'rounds', label: 'FL Rounds', icon: TbRotateClockwise },
    { id: 'reports', label: 'Reports', icon: TbFileSpreadsheet },
    { id: 'settings', label: 'Settings', icon: TbAdjustments },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Institutional Topbar */}
      <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#090e1c]/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Consortium Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-700 flex items-center justify-center text-white font-bold shadow-md shadow-cyan-950">
              <TbBuildingCommunity className="w-5 h-5 text-cyan-200" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-heading font-bold text-lg tracking-tight text-white">
                  SkillBridge
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-semibold uppercase tracking-wider">
                  Institution Portal
                </span>
              </div>
              <p className="text-[10px] text-slate-400 -mt-0.5 hidden sm:block">
                Consortium Intelligence & Federated Learning Control Center
              </p>
            </div>
          </div>

          {/* Node Heartbeat & Admin Session */}
          <div className="flex items-center space-x-4">
            <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Consortium Mesh: 4 Nodes Active</span>
            </div>

            {adminUser && (
              <div className="hidden sm:flex items-center space-x-2.5 pl-2 border-l border-slate-800">
                <div className="text-right">
                  <p className="text-xs font-semibold text-white">{adminUser.name || 'Consortium Admin'}</p>
                  <p className="text-[10px] text-cyan-400 font-mono">
                    {adminUser.email}
                  </p>
                </div>
                <div className="w-8 h-8 rounded-full bg-cyan-950 border border-cyan-500/40 flex items-center justify-center text-cyan-300 font-bold text-xs">
                  A
                </div>
              </div>
            )}

            <button
              onClick={handleLogout}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors text-sm flex items-center space-x-1"
              title="Log out from Administrative Session"
            >
              <TbLogout className="w-4 h-4" />
              <span className="text-xs hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        {/* Institutional Admin Sidebar */}
        <aside className="w-64 bg-[#0a1020]/70 border-r border-slate-800/80 p-4 hidden lg:flex flex-col justify-between min-h-[calc(100vh-4rem)]">
          <div className="space-y-1">
            <div className="flex items-center justify-between px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-slate-400">
              <span>Administration</span>
              <span className="text-cyan-400">RBAC Active</span>
            </div>

            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-semibold shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/40">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Infrastructure Health Card */}
          <div className="p-3.5 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-2">
            <div className="flex items-center space-x-2 text-cyan-400">
              <TbServer2 className="w-4 h-4" />
              <span className="text-xs font-semibold">Federated Privacy Layer</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Decentralized SGD model training across college partitions with mathematical Differential Privacy.
            </p>
            <div className="pt-1.5 border-t border-slate-800 text-[10px] font-mono text-slate-400 flex justify-between">
              <span>Aggregation: FedAvg</span>
              <span className="text-emerald-400">Zero Raw Exfiltration</span>
            </div>
          </div>
        </aside>

        {/* Content Area */}
        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-5xl">
          {children}
        </main>
      </div>
    </div>
  );
}
