import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../services/authService';
import { TbSparkles, TbMail, TbArrowLeft, TbCheck, TbAlertCircle, TbExternalLink } from 'react-icons/tb';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [devInfo, setDevInfo] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const res = await authService.forgotPassword(email);
      setSubmitted(true);
      setMessage(res.message || 'If an account exists with this email, a password reset link has been sent.');
      if (res.dev_info) {
        setDevInfo(res.dev_info);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Unable to process request. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-base-950">
      <div className="w-full max-w-md p-8 rounded-3xl glass">
        {/* Brand */}
        <div className="mb-6">
          <div className="flex items-center space-x-2.5 mb-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-400 to-teal-600 flex items-center justify-center text-base-950 font-bold">
              <TbSparkles className="w-4 h-4" />
            </div>
            <span className="font-heading font-bold text-lg text-white">SkillBridge</span>
          </div>
          <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
            Reset Password
          </h1>
          <p className="text-white/50 text-xs mt-1">
            Enter the email address registered with your student account to receive a secure reset link.
          </p>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center space-x-2">
            <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs space-y-2">
              <div className="flex items-center space-x-2 font-semibold text-teal-200">
                <TbCheck className="w-4 h-4 text-emerald-400" />
                <span>Instructions Dispatched</span>
              </div>
              <p className="text-white/80 leading-relaxed">
                {message}
              </p>
              <p className="text-[11px] text-white/50">
                Please check your inbox and spam folder. The password reset link will expire in 1 hour.
              </p>
            </div>

            {devInfo?.dev_reset_link && (
              <div className="p-3.5 rounded-xl bg-base-900 border border-accent-500/30 text-xs space-y-2">
                <div className="flex items-center justify-between text-accent-300 font-medium text-[11px]">
                  <span>Local Development Reset Link</span>
                  <span className="text-[10px] font-mono bg-accent-500/20 px-1.5 py-0.5 rounded">DEV MODE</span>
                </div>
                <p className="text-[11px] text-white/60">
                  {devInfo.note}
                </p>
                <a
                  href={devInfo.dev_reset_link}
                  className="inline-flex items-center space-x-1.5 text-xs text-accent-400 hover:text-accent-300 font-semibold underline underline-offset-2 break-all"
                >
                  <span>Open Password Reset Screen</span>
                  <TbExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                </a>
              </div>
            )}

            <div className="pt-2">
              <Link
                to="/login"
                className="w-full py-2.5 rounded-xl border border-base-700 hover:border-base-600 text-white/80 hover:text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
              >
                <TbArrowLeft className="w-4 h-4" />
                <span>Return to Sign In</span>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                Registered Email Address
              </label>
              <div className="relative">
                <input
                  type="email"
                  name="email"
                  placeholder="student@university.edu"
                  className="input-field text-xs py-2.5 pl-9"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <TbMail className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-semibold text-xs btn-primary shadow-glow transition-all flex items-center justify-center space-x-2 disabled:opacity-40"
            >
              <span>{loading ? 'Generating Reset Link...' : 'Send Password Reset Link'}</span>
            </button>

            <div className="pt-2 text-center">
              <Link
                to="/login"
                className="inline-flex items-center space-x-1.5 text-xs text-white/50 hover:text-white transition-colors"
              >
                <TbArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

