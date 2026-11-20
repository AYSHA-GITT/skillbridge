import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  TbBriefcase2,
  TbLayoutDashboard,
  TbBuildingSkyscraper,
  TbBriefcase,
  TbUserSearch,
  TbListCheck,
  TbColumns3,
  TbLogout,
  TbRosetteDiscountCheck,
  TbAlertTriangle,
  TbLock,
  TbMenu2,
  TbX,
  TbClipboardCheck
} from 'react-icons/tb';
import authService from '../services/authService';
import recruiterService from '../services/recruiterService';

const RecruiterContext = createContext(null);
export const useRecruiter = () => useContext(RecruiterContext);

const NAV = [
  { to: '/recruiter', label: 'Dashboard', icon: TbLayoutDashboard, end: true },
  { to: '/recruiter/jobs', label: 'Job Postings', icon: TbBriefcase },
  { to: '/recruiter/candidates', label: 'Find Candidates', icon: TbUserSearch },
  { to: '/recruiter/pipeline', label: 'Hiring Pipeline', icon: TbColumns3 },
  { to: '/recruiter/shortlists', label: 'Shortlists', icon: TbListCheck },
  { to: '/recruiter/verifications', label: 'Verification Requests', icon: TbClipboardCheck },
  { to: '/recruiter/organisation', label: 'Organisation', icon: TbBuildingSkyscraper }
];

export function OrgBadge({ status, className = '' }) {
  if (status === 'verified') {
    return (
      <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border bg-emerald-500/15 text-emerald-300 border-emerald-500/40 ${className}`}>
        <TbRosetteDiscountCheck className="w-3 h-3" /> Verified employer
      </span>
    );
  }
  const map = {
    pending: ['Verification pending', 'bg-amber-500/15 text-amber-300 border-amber-500/40'],
    rejected: ['Not verified', 'bg-rose-500/15 text-rose-300 border-rose-500/40'],
    unverified: ['Unverified', 'bg-white/5 text-white/60 border-white/15']
  };
  const [label, cls] = map[status] || map.unverified;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${cls} ${className}`}>
      <TbAlertTriangle className="w-3 h-3" /> {label}
    </span>
  );
}

/** Shown on features that need a verified organisation. */
export function VerificationGate({ me, children, feature = 'This feature' }) {
  if (me?.organisation?.verification_status === 'verified') return children;
  return (
    <div className="glass p-8 rounded-2xl text-center space-y-3 max-w-xl mx-auto">
      <TbLock className="w-10 h-10 text-white/30 mx-auto" />
      <h2 className="font-heading text-lg font-bold text-white">{feature} needs a verified organisation</h2>
      <p className="text-sm text-white/55">
        To protect students, only organisations an administrator has verified can publish jobs and search
        candidates. Current status: <OrgBadge status={me?.organisation?.verification_status} />
      </p>
      <NavLink to="/recruiter/organisation" className="btn-primary inline-flex w-auto px-4 text-xs">
        Go to organisation verification
      </NavLink>
    </div>
  );
}

export default function RecruiterLayout({ children }) {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [error, setError] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

  const refresh = useCallback(() => recruiterService.me().then(setMe), []);

  useEffect(() => {
    recruiterService.me()
      .then(setMe)
      .catch((e) => {
        if (e?.response?.status === 401) navigate('/login?portal=recruiter');
        else setError(e?.response?.data?.error || 'Could not load your recruiter account.');
      });
  }, [navigate]);

  const logout = async () => {
    try {
      await authService.logout();
    } catch {
      // ignore
    }
    navigate('/login?portal=recruiter');
  };

  if (error) {
    return <div className="min-h-screen flex items-center justify-center text-rose-300 text-sm p-6">{error}</div>;
  }
  if (!me) {
    return (
      <div className="min-h-screen flex items-center justify-center text-white/40 font-mono text-sm">
        <div className="inline-block w-6 h-6 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin mr-3" />
        Loading recruiter portal...
      </div>
    );
  }

  const nav = (
    <nav className="space-y-1">
      {NAV.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={() => setMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-500/15 text-indigo-200 border border-indigo-400/30 font-semibold'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
              }`
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );

  return (
    <RecruiterContext.Provider value={{ me, refresh }}>
      <div className="min-h-screen flex flex-col bg-base-950">
        <header className="sticky top-0 z-40 w-full border-b border-base-700/60 bg-base-950/85 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <button className="lg:hidden p-2 text-white/60" onClick={() => setMenuOpen(!menuOpen)} aria-label="Menu">
                {menuOpen ? <TbX className="w-5 h-5" /> : <TbMenu2 className="w-5 h-5" />}
              </button>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-400 to-violet-600 flex items-center justify-center text-white">
                <TbBriefcase2 className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="font-heading font-bold text-lg tracking-tight text-white">SkillBridge</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-400/30">
                    Recruiter Portal
                  </span>
                </div>
                <p className="text-[10px] text-white/40 -mt-0.5 hidden sm:block">Hire on evidence, not keywords</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden md:block text-right">
                <p className="text-xs font-semibold text-white">{me.user.name}</p>
                <p className="text-[11px] text-white/50 flex items-center gap-1.5 justify-end">
                  {me.organisation.name} <OrgBadge status={me.organisation.verification_status} />
                </p>
              </div>
              <button onClick={logout} className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/5" title="Log out">
                <TbLogout className="w-4 h-4" />
              </button>
            </div>
          </div>
          {menuOpen && <div className="lg:hidden px-4 pb-4 border-t border-base-700/60 pt-3">{nav}</div>}
        </header>
        <div className="flex-1 flex w-full max-w-7xl mx-auto">
          <aside className="w-60 border-r border-base-700/60 p-4 hidden lg:block bg-base-900/40">
            <p className="text-[10px] font-mono uppercase tracking-wider text-white/30 px-3 py-2">Recruiter Portal</p>
            {nav}
            <div className="mt-6 surface p-3 rounded-2xl text-[11px] text-white/55 leading-snug">
              Candidates appear only with their consent and only with the sections they chose to share.
              Every profile view is shown to the student.
            </div>
          </aside>
          <main className="flex-1 p-4 md:p-8 min-w-0">{children}</main>
        </div>
      </div>
    </RecruiterContext.Provider>
  );
}
