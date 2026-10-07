import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import api from '../services/api';
import { TbSparkles, TbBuildingCommunity, TbArrowRight } from 'react-icons/tb';

export default function Login() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPortal = searchParams.get('portal') === 'admin' ? 'admin' : 'student';

  const [portal, setPortal] = useState(initialPortal);
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const p = searchParams.get('portal');
    if (p === 'admin' || p === 'student') {
      setPortal(p);
    }
  }, [searchParams]);

  const handlePortalSwitch = (newPortal) => {
    setPortal(newPortal);
    setSearchParams({ portal: newPortal });
    setError('');
  };

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.post('/auth/login', {
        email: form.email,
        password: form.password,
        portal: portal
      });

      const user = res.data.student;
      const userRole = (user?.role || 'student').toLowerCase();

      if (portal === 'admin') {
        if (userRole === 'admin') {
          navigate('/admin');
        } else {
          setError('Access denied: Student accounts cannot access the Institutional Admin Portal.');
        }
      } else {
        // Student Portal login
        if (userRole === 'admin') {
          navigate('/admin');
        } else {
          navigate('/dashboard');
        }
      }
    } catch (err) {
      setError(
        err.response?.data?.error || 'Authentication failed. Please verify your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  const isAdminPortal = portal === 'admin';

  return (
    <div className={`min-h-screen flex items-center justify-center px-4 transition-colors duration-300 ${isAdminPortal ? 'bg-[#070b14]' : 'bg-base-950'}`}>
      <div className={`w-full max-w-md p-8 rounded-3xl transition-all duration-300 ${
        isAdminPortal
          ? 'bg-slate-900/80 border border-cyan-500/30 shadow-2xl shadow-cyan-950/50'
          : 'glass'
      }`}>
        {/* Portal Switcher Tabs */}
        <div className="flex rounded-2xl bg-slate-950/70 p-1 mb-6 border border-slate-800">
          <button
            type="button"
            onClick={() => handlePortalSwitch('student')}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all ${
              !isAdminPortal
                ? 'bg-accent-500/20 text-accent-300 border border-accent-400/40 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🎓 Student Portal</span>
          </button>
          <button
            type="button"
            onClick={() => handlePortalSwitch('admin')}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all ${
              isAdminPortal
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🏛 Institution Portal</span>
          </button>
        </div>

        {/* Portal Header */}
        <div className="mb-6">
          <div className="flex items-center space-x-2.5 mb-2">
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold ${
              isAdminPortal
                ? 'bg-gradient-to-tr from-cyan-600 to-blue-700 text-white'
                : 'bg-gradient-to-br from-accent-400 to-teal-600 text-base-950'
            }`}>
              {isAdminPortal ? <TbBuildingCommunity className="w-4 h-4" /> : <TbSparkles className="w-4 h-4" />}
            </div>
            <span className="font-heading font-bold text-lg text-white">
              SkillBridge
            </span>
          </div>

          <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
            {isAdminPortal ? 'Institutional Sign In' : 'Student Sign In'}
          </h1>
          <p className="text-white/50 text-xs mt-1">
            {isAdminPortal
              ? 'Access consortium analytics & federated learning orchestration'
              : 'Continue to your skills, verification, and career roadmaps'}
          </p>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start space-x-2 animate-slide-up">
            <span className="font-bold">•</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              name="email"
              placeholder={isAdminPortal ? "admin@skillbridge.edu" : "student@university.edu"}
              className="input-field text-xs py-2.5"
              value={form.email}
              onChange={handleChange}
              required
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
              Password
            </label>
            <input
              type="password"
              name="password"
              placeholder="••••••••"
              className="input-field text-xs py-2.5"
              value={form.password}
              onChange={handleChange}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-3 rounded-xl font-semibold text-xs transition-all flex items-center justify-center space-x-2 ${
              isAdminPortal
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-950'
                : 'btn-primary shadow-glow'
            } disabled:opacity-40`}
          >
            <span>{loading ? 'Authenticating...' : isAdminPortal ? 'Sign In to Institution Portal' : 'Sign In to Student Portal'}</span>
            <TbArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-slate-800 text-center text-xs">
          {!isAdminPortal ? (
            <p className="text-white/40">
              Don't have a student account?{' '}
              <Link to="/register" className="text-accent-400 hover:text-accent-300 font-medium">
                Create one free
              </Link>
            </p>
          ) : (
            <p className="text-slate-400 text-[11px]">
              Institutional accounts are managed by consortium administrators.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}