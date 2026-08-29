import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { TbShieldLock, TbLogout, TbSparkles } from 'react-icons/tb';
import authService from '../services/authService';

export default function Navbar({ student }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {
      // ignore
    }
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-base-700/60 bg-base-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/dashboard" className="flex items-center space-x-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-400 to-teal-600 flex items-center justify-center text-base-950 font-bold shadow-glow group-hover:scale-105 transition-transform">
            <TbSparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-heading font-bold text-lg tracking-tight text-white">
                SkillBridge
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-500/15 text-accent-300 border border-accent-400/30">
                FL-Powered
              </span>
            </div>
            <p className="text-[10px] text-white/40 -mt-1 hidden sm:block">Privacy-Preserving Career Intelligence</p>
          </div>
        </Link>

        {/* User Info & Actions */}
        <div className="flex items-center space-x-4">
          {student && (
            <div className="hidden md:flex items-center space-x-3 pr-2 border-r border-base-700/60">
              <div className="text-right">
                <p className="text-xs font-semibold text-white">{student.name}</p>
                <p className="text-[11px] text-accent-400 capitalize">
                  {student.target_career || 'Target not set'}
                </p>
              </div>
              <div className="w-8 h-8 rounded-full bg-accent-500/20 border border-accent-400/40 flex items-center justify-center text-accent-300 font-semibold text-xs">
                {student.name ? student.name[0].toUpperCase() : 'S'}
              </div>
            </div>
          )}

          <Link
            to="/federated"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-accent-400/30 text-xs font-medium text-accent-300 bg-accent-500/10 hover:bg-accent-500/20 transition-colors"
          >
            <TbShieldLock className="w-4 h-4" />
            <span className="hidden sm:inline">Privacy Hub</span>
          </Link>

          <button
            onClick={handleLogout}
            className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/5 transition-colors text-sm"
            title="Log out"
          >
            <TbLogout className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
